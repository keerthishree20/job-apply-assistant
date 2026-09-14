"""Shared form handling for both apply bots.

One rule runs through this module: fill only what the candidate actually gave us,
never guess, and leave every legal or personal-status question for the candidate.

The work is split so the decisions can be tested without a browser:

- `scan_fields` reads every visible field on the page into plain dicts.
- `plan_field` decides, in pure Python, what to do with one field.
- `fill_page` applies those decisions and reports what happened, so the preview
  the candidate approves lists exactly what was filled and what was left for them.
- `verify_submission` looks for a confirmation or an error after the submit click,
  so "submitted" is something the page said, not something we assumed.
"""

import asyncio
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import Page

from services.llm_client import ELIGIBILITY_PATTERN, NEEDS_INPUT


def headless() -> bool:
    """Visible browser by default: the candidate may need to answer questions in it.

    Set APPLY_HEADLESS=true for servers and tests.
    """
    return os.getenv("APPLY_HEADLESS", "false").strip().lower() in {"1", "true", "yes"}


# --------------------------------------------------------------------------- #
# Resume file
# --------------------------------------------------------------------------- #

class ResumeFile:
    """A per-session temp copy of the resume PDF, removed when the session closes.

    The old code wrote every upload to one shared path, so two sessions could
    upload each other's resume.
    """

    def __init__(self, pdf_bytes: bytes, candidate_name: str = ""):
        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError("Resume upload is not a PDF.")
        self._dir = Path(tempfile.mkdtemp(prefix="jaa-resume-"))
        safe = re.sub(r"[^A-Za-z0-9 _-]", "", candidate_name).strip() or "Resume"
        self.path = self._dir / f"{safe} - Resume.pdf"
        self.path.write_bytes(pdf_bytes)

    def remove(self) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Scanning
# --------------------------------------------------------------------------- #

_SCAN_JS = """
(root) => {
  const scope = root || document;
  const visible = (el) => {
    if (el.type === 'file') return true;  // file inputs are often hidden behind a styled button
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const text = (el) => (el ? el.textContent.replace(/\\s+/g, ' ').trim() : '');
  const labelOf = (el) => {
    if (el.labels && el.labels.length) return text(el.labels[0]);
    const by = el.getAttribute('aria-labelledby');
    if (by) return by.split(/\\s+/).map((id) => text(document.getElementById(id))).join(' ').trim();
    return el.getAttribute('aria-label') || el.placeholder || el.name || '';
  };
  const out = [];
  let n = 0;
  const seenGroups = new Set();
  for (const el of scope.querySelectorAll('input, textarea, select')) {
    const type = (el.getAttribute('type') || el.tagName).toLowerCase();
    if (['hidden', 'submit', 'button', 'reset', 'image'].includes(type)) continue;
    if (el.disabled || el.readOnly || !visible(el)) continue;
    if (type === 'radio') {
      const key = el.name || el.id;
      if (seenGroups.has(key)) continue;
      seenGroups.add(key);
      const group = [...scope.querySelectorAll('input[type=radio]')].filter((r) => (r.name || r.id) === key);
      const fs = el.closest('fieldset');
      const legend = fs ? text(fs.querySelector('legend')) : '';
      const id = String(n++);
      group.forEach((r) => r.setAttribute('data-jaa-id', id));
      out.push({
        id, kind: 'radio', label: legend || labelOf(el),
        required: group.some((r) => r.required || r.getAttribute('aria-required') === 'true'),
        value: group.some((r) => r.checked) ? 'checked' : '',
        options: group.map((r) => labelOf(r)),
      });
      continue;
    }
    const id = String(n++);
    el.setAttribute('data-jaa-id', id);
    out.push({
      id,
      kind: el.tagName === 'SELECT' ? 'select' : el.tagName === 'TEXTAREA' ? 'textarea' : type,
      label: labelOf(el),
      required: el.required || el.getAttribute('aria-required') === 'true',
      value: type === 'checkbox' ? (el.checked ? 'checked' : '') :
             type === 'file' ? (el.files && el.files.length ? 'file' : '') :
             el.tagName === 'SELECT' ? (el.selectedIndex > 0 ? el.value : '') : el.value,
      options: el.tagName === 'SELECT' ? [...el.options].slice(1).map((o) => text(o)) : [],
    });
  }
  return out;
}
"""


async def scan_fields(page: Page, root_selector: str | None = None) -> list[dict]:
    if root_selector:
        root = page.locator(root_selector).first
        if await root.count():
            return await root.evaluate(_SCAN_JS)
    return await page.evaluate(_SCAN_JS, None)


# --------------------------------------------------------------------------- #
# Deciding
# --------------------------------------------------------------------------- #

_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "for", "with", "is",
    "are", "do", "does", "you", "your", "we", "our", "us", "what", "why", "how", "this",
    "that", "be", "have", "has", "please", "if", "any", "as", "by", "from", "it", "me",
    "my", "i", "will", "would", "can", "could",
}

_TEXT_KINDS = {"text", "email", "tel", "url", "number", "search", "input"}

# Profile fields matched by label. Each value is a list of patterns tried against
# the normalised label; the first profile key whose pattern matches wins.
_PROFILE_LABELS: list[tuple[str, re.Pattern]] = [
    ("first_name", re.compile(r"\b(first|given|fore)\s*name\b")),
    ("last_name", re.compile(r"\b(last|family|sur)\s*name\b|\bsurname\b")),
    ("name", re.compile(r"^(full |legal |your )?name$")),
    ("email", re.compile(r"\be-?mail\b")),
    ("phone", re.compile(r"\b(phone|mobile|telephone|contact number)\b")),
    ("linkedin_url", re.compile(r"\blinked\s*in\b")),
    ("github_url", re.compile(r"\bgit\s*hub\b")),
    ("portfolio_url", re.compile(r"\b(portfolio|personal website|website)\b")),
    ("graduation_year", re.compile(r"\bgraduat\w*\b.*\byear\b|\byear\b.*\bgraduat\w*\b")),
    ("college", re.compile(r"\b(college|university|school)\b")),
]

_COVER_LETTER = re.compile(r"\bcover\s*letter\b")
_RESUME = re.compile(r"\b(resume|résumé|cv|curriculum)\b")


@dataclass
class Action:
    """What to do with one scanned field."""

    kind: str  # "fill", "choose", "upload", "needs_input", "skip"
    value: str = ""
    reason: str = ""


def _normalise(label: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", label.lower().replace("*", " ")).strip()


def _stems(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    # A five-letter prefix is a crude stem, but it is enough to pair "expected
    # salary" with "salary expectations" without pulling in a stemming library.
    return {w[:5] for w in words if w not in _STOPWORDS and len(w) > 1}


def match_answer(label: str, answers: list[dict]) -> dict | None:
    """The screening answer whose question this label is asking, or None.

    Requires two shared content words and a 60% overlap with the shorter side.
    A near miss returns None, and the field is left blank rather than filled with
    the answer to a different question.
    """
    label_stems = _stems(label)
    best, best_score = None, 0.0
    for item in answers:
        q = _stems(item.get("question", ""))
        shared = len(label_stems & q)
        if shared < 2:
            continue
        score = shared / min(len(label_stems), len(q))
        if score >= 0.6 and score > best_score:
            best, best_score = item, score
    return best


def _profile_values(profile: dict) -> dict:
    values = {k: (v or "").strip() for k, v in profile.items() if isinstance(v, str)}
    parts = values.get("name", "").split(" ", 1)
    values["first_name"] = parts[0] if parts[0] else ""
    values["last_name"] = parts[1].strip() if len(parts) > 1 else ""
    return values


def _choose_option(options: list[str], answer: str) -> str | None:
    wanted = _normalise(answer)
    for opt in options:
        if _normalise(opt) == wanted:
            return opt
    return None


def plan_field(field: dict, profile: dict, answers: list[dict], cover_letter: str) -> Action:
    label = field.get("label", "")
    norm = _normalise(label)
    kind = field["kind"]
    required = field.get("required", False)
    missing = Action("needs_input", reason="required, and nothing provided") if required else Action("skip")

    if kind == "file":
        if _COVER_LETTER.search(norm):
            return missing
        if _RESUME.search(norm) or not norm or "attach" in norm or "upload" in norm or "file" in norm:
            return Action("upload", reason="resume")
        return missing

    # Checked before anything else, including fields that already hold a value:
    # the form can ask an eligibility question our answer set never saw, and a
    # site's own pre-filled guess still needs the candidate's eyes.
    if ELIGIBILITY_PATTERN.search(label):
        return Action("needs_input", reason="legal or personal-status question")

    if field.get("value"):
        return Action("skip", reason="already filled")

    if kind == "checkbox":
        # Consent boxes (terms, privacy, "I certify...") are the candidate's to tick.
        return missing

    if kind in _TEXT_KINDS:
        values = _profile_values(profile)
        for key, pattern in _PROFILE_LABELS:
            if pattern.search(norm):
                value = values.get(key, "")
                if not value:
                    return missing
                if kind == "number" and not value.isdigit():
                    return missing
                return Action("fill", value=value, reason=key)

    if kind == "textarea" and _COVER_LETTER.search(norm):
        if cover_letter.strip():
            return Action("fill", value=cover_letter.strip(), reason="cover letter")
        return missing

    item = match_answer(label, answers)
    if item is None:
        return missing
    answer = (item.get("answer") or "").strip()
    if item.get("needs_review") or NEEDS_INPUT in answer or not answer:
        return Action("needs_input", reason="flagged for the candidate to answer")

    if kind in ("select", "radio"):
        option = _choose_option(field.get("options", []), answer)
        if option is None:
            return Action("needs_input", reason="no option matches the prepared answer")
        return Action("choose", value=option, reason="screening answer")
    if kind == "number" and not re.fullmatch(r"\d+(\.\d+)?", answer):
        return Action("needs_input", reason="expects a number")
    if kind in _TEXT_KINDS or kind == "textarea":
        return Action("fill", value=answer, reason="screening answer")
    return missing


# --------------------------------------------------------------------------- #
# Filling
# --------------------------------------------------------------------------- #

@dataclass
class FillReport:
    filled: list[str] = field(default_factory=list)
    needs_input: list[str] = field(default_factory=list)

    def add_filled(self, label: str) -> None:
        if label not in self.filled:
            self.filled.append(label)

    def add_needs_input(self, label: str) -> None:
        if label not in self.needs_input:
            self.needs_input.append(label)


def _display(label: str, fallback: str) -> str:
    label = re.sub(r"\s+", " ", label.replace("*", "")).strip()
    return label[:80] or fallback


async def fill_page(
    page: Page,
    profile: dict,
    answers: list[dict],
    cover_letter: str,
    resume: ResumeFile | None,
    report: FillReport,
    root_selector: str | None = None,
) -> list[str]:
    """Fill the visible fields on the current step. Returns this step's needs-input labels."""
    step_needs: list[str] = []
    for fld in await scan_fields(page, root_selector):
        action = plan_field(fld, profile, answers, cover_letter)
        label = _display(fld["label"], fld["kind"])
        target = page.locator(f"[data-jaa-id='{fld['id']}']")
        try:
            if action.kind == "upload":
                if resume is None or fld.get("value"):
                    continue
                await target.first.set_input_files(str(resume.path))
                report.add_filled("Resume (PDF)")
            elif action.kind == "fill":
                await target.first.fill(action.value)
                report.add_filled(label)
            elif action.kind == "choose":
                if fld["kind"] == "select":
                    await target.first.select_option(label=action.value)
                else:
                    await page.get_by_label(action.value, exact=True).and_(target).first.check()
                report.add_filled(label)
            elif action.kind == "needs_input":
                report.add_needs_input(label)
                step_needs.append(label)
        except Exception:
            # A field that refuses input is reported, never silently counted as filled.
            if action.kind != "skip":
                report.add_needs_input(label)
                step_needs.append(label)
    return step_needs


# --------------------------------------------------------------------------- #
# Submission checks
# --------------------------------------------------------------------------- #

# A button with this text finishes the application. Paging stops in front of it:
# some ATSs reuse one selector for "Next" and "Submit", so a click-through loop
# that trusts the selector alone would submit before the candidate confirmed.
FINAL_BUTTON = re.compile(r"\b(submit|send application|apply now|finish|complete application)\b", re.I)

_SUCCESS = re.compile(
    r"application (was |has been )?(submitted|received|sent)"
    r"|thank(s| you) for (applying|your application)"
    r"|we('ve| have) received your application",
    re.I,
)
_SUCCESS_URL = re.compile(r"thank|confirm|success|submitted", re.I)

_ERRORS_JS = """
() => {
  const vis = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const texts = [];
  for (const el of document.querySelectorAll(
      "[role=alert], .error, .errors, .field-error, .invalid-feedback, [aria-invalid=true]")) {
    if (!vis(el)) continue;
    const t = el.getAttribute('aria-invalid') === 'true'
      ? 'invalid: ' + (el.labels && el.labels[0] ? el.labels[0].textContent.trim() : el.name)
      : el.textContent.replace(/\\s+/g, ' ').trim();
    if (t) texts.push(t);
  }
  return texts;
}
"""


_NATIVE_INVALID_JS = """
(btn) => {
  const form = btn.form || btn.closest('form');
  if (!form || form.noValidate || btn.formNoValidate) return [];
  const name = (el) => (el.labels && el.labels[0] ? el.labels[0].textContent : '')
    .replace(/[*\\s]+/g, ' ').trim() || el.name || el.id;
  return [...form.elements].filter((el) => el.willValidate && !el.checkValidity()).map(name)
    .filter((v, i, a) => a.indexOf(v) === i);
}
"""


async def native_invalid_fields(button) -> list[str]:
    """Fields the browser's own validation would block on.

    With `required` inputs and no `novalidate`, Chromium swallows the submit and
    shows a tooltip, and the page never changes. Checking first turns that into
    a clear "failed" with names instead of a timeout that reads as "unconfirmed".
    """
    try:
        return await button.evaluate(_NATIVE_INVALID_JS)
    except Exception:
        return []


async def click_submit(page: Page, button) -> dict:
    invalid = await native_invalid_fields(button)
    if invalid:
        return {"status": "failed", "detail": "required fields are not complete: " + ", ".join(invalid)}
    before = await page_state(page)
    await button.click()
    return await verify_submission(page, before)


async def page_state(page: Page) -> dict:
    return {
        "text": await page.evaluate("() => document.body ? document.body.innerText : ''"),
        "errors": await page.evaluate(_ERRORS_JS),
        "url": page.url,
    }


async def verify_submission(page: Page, before: dict, timeout: float | None = None) -> dict:
    """Wait for the page to confirm or reject the submission.

    Only signals that appeared after the click count, so a "* required" legend or
    a job description mentioning applications cannot be misread as the outcome.
    Returns {"status": "submitted" | "failed" | "unconfirmed", "detail": str}.
    """
    timeout = timeout if timeout is not None else float(os.getenv("APPLY_CONFIRM_TIMEOUT", "15"))
    before_errors = set(before["errors"])
    before_success = bool(_SUCCESS.search(before["text"]))
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        try:
            now = await page_state(page)
        except Exception:
            now = None  # mid-navigation; try again
        if now is not None:
            new_errors = [e for e in now["errors"] if e not in before_errors]
            if new_errors:
                return {"status": "failed", "detail": "; ".join(new_errors[:5])}
            if not before_success and _SUCCESS.search(now["text"]):
                return {"status": "submitted", "detail": _SUCCESS.search(now["text"]).group(0)}
            if now["url"] != before["url"] and _SUCCESS_URL.search(now["url"]):
                return {"status": "submitted", "detail": f"redirected to {now['url']}"}
        if asyncio.get_running_loop().time() >= deadline:
            return {
                "status": "unconfirmed",
                "detail": "No confirmation or error appeared after clicking submit.",
            }
        await asyncio.sleep(0.25)

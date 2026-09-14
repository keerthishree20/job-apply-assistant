import json
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from services.form_filler import (
    FINAL_BUTTON, FillReport, ResumeFile, click_submit, fill_page, headless,
)

SESSION_DIR = Path("sessions")
SESSION_DIR.mkdir(exist_ok=True)

# Only navigation lives here. Fields are found by their labels in form_filler, so
# the same logic covers every ATS and a renamed input id cannot mis-fill a field.
ATS_APPLY_CONFIGS = {
    "myworkdayjobs.com": {
        "apply_btn": "a[data-automation-id='applyButton']",
        # Workday uses this one button for both "Next" and "Submit".
        "next_btn": "button[data-automation-id='bottom-navigation-next-btn']",
        "submit_btn": "button[data-automation-id='bottom-navigation-next-btn']",
    },
    "boards.greenhouse.io": {
        "apply_btn": "a#apply_button",
        "next_btn": None,
        "submit_btn": "input[type='submit'], button[type='submit']",
    },
    "greenhouse.io": {
        "apply_btn": "a#apply_button",
        "next_btn": None,
        "submit_btn": "input[type='submit'], button[type='submit']",
    },
    "jobs.lever.co": {
        "apply_btn": "a.template-btn-submit",
        "next_btn": None,
        "submit_btn": "button[type='submit']",
    },
    "smartrecruiters.com": {
        "apply_btn": "a.apply-button",
        "next_btn": "button.navigation-btn-next",
        "submit_btn": "button[data-test='submit-button']",
    },
}

DEFAULT_CONFIG = {"apply_btn": None, "next_btn": None, "submit_btn": "button[type='submit'], input[type='submit']"}


async def _button_text(page: Page, selector: str) -> str | None:
    btn = page.locator(selector).first
    if not await btn.count() or not await btn.is_visible():
        return None
    return (await btn.evaluate("el => el.innerText || el.value || el.getAttribute('aria-label') || ''")).strip()


class ATSBot:
    def __init__(self, ats_type: str):
        self._ats_type = ats_type
        self._config = ATS_APPLY_CONFIGS.get(ats_type, DEFAULT_CONFIG)
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._resume: ResumeFile | None = None
        self._meta: dict = {}

    async def _launch(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless())
        session_file = SESSION_DIR / f"{self._ats_type.replace('.', '_')}.json"
        storage = json.loads(session_file.read_text()) if session_file.exists() else None
        self._context = await self._browser.new_context(storage_state=storage)
        self._page = await self._context.new_page()

    async def fill_form(
        self,
        job_url: str,
        resume_pdf: bytes,
        profile: dict,
        screening_answers: list[dict],
        cover_letter: str = "",
    ) -> dict:
        self._resume = ResumeFile(resume_pdf, profile.get("name", ""))
        await self._launch()
        self._meta = {"url": job_url, "cover_letter": False}
        cfg = self._config
        page = self._page

        await page.goto(job_url, wait_until="domcontentloaded")

        if cfg.get("apply_btn"):
            btn = page.locator(cfg["apply_btn"]).first
            if await btn.count():
                await btn.click()
                await page.wait_for_load_state("domcontentloaded")

        report = FillReport()
        for _ in range(8):
            step_needs = await fill_page(page, profile, screening_answers, cover_letter, self._resume, report)
            next_sel = cfg.get("next_btn")
            if not next_sel or step_needs:
                break  # single-page form, or the candidate has to act before this step can advance
            label = await _button_text(page, next_sel)
            if label is None or FINAL_BUTTON.search(label):
                break  # the next click would submit; that belongs to /confirm
            await page.locator(next_sel).first.click()
            await page.wait_for_load_state("domcontentloaded")

        self._meta["cover_letter"] = any("cover letter" in f.lower() for f in report.filled)
        screenshot = await page.screenshot(full_page=False)
        return {"screenshot": screenshot, "fields_filled": report.filled, "needs_input": report.needs_input}

    async def submit(self) -> dict:
        submit_sel = self._config.get("submit_btn") or DEFAULT_CONFIG["submit_btn"]
        btn = self._page.locator(submit_sel).last
        if not await btn.count():
            return {"status": "failed", "detail": f"Submit button not found for ATS: {self._ats_type}"}
        if self._config.get("next_btn") == submit_sel:
            label = await _button_text(self._page, submit_sel) or ""
            if not FINAL_BUTTON.search(label):
                # Shared Next/Submit button still reads "Next": clicking it would
                # only change step, and the result would read as unconfirmed.
                return {"status": "failed", "detail": "the form has more steps; finish them in the browser window"}
        return await click_submit(self._page, btn)

    @property
    def meta(self) -> dict:
        return self._meta

    async def close(self):
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        finally:
            if self._resume:
                self._resume.remove()

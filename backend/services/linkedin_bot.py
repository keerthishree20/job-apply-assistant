"""LinkedIn Easy Apply.

Not verified against the live site: it needs a logged-in account, and automating
LinkedIn is against its terms. The form handling it shares with ATSBot is tested
against local mock forms; the LinkedIn-specific selectors below are not.
"""

import asyncio
import json
import random
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from services.form_filler import FillReport, ResumeFile, click_submit, fill_page, headless

SESSION_PATH = Path("sessions/linkedin.json")
SESSION_PATH.parent.mkdir(exist_ok=True)

MODAL = "div.jobs-easy-apply-modal, div[role='dialog']"
NEXT_BTN = "button[aria-label='Continue to next step']"
REVIEW_BTN = "button[aria-label='Review your application']"
SUBMIT_BTN = "button[aria-label='Submit application']"


async def _delay(lo=0.8, hi=1.8):
    await asyncio.sleep(random.uniform(lo, hi))


async def _safe_click(page: Page, selector: str, timeout=4000) -> bool:
    try:
        el = page.locator(selector).first
        await el.wait_for(state="visible", timeout=timeout)
        await el.click()
        await _delay(0.5, 1.0)
        return True
    except Exception:
        return False


class LinkedInBot:
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._resume: ResumeFile | None = None
        self._meta: dict = {}

    async def _launch(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=headless(),
            args=["--start-maximized"],
        )
        storage = json.loads(SESSION_PATH.read_text()) if SESSION_PATH.exists() else None
        self._context = await self._browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 900},
        )
        self._page = await self._context.new_page()

    async def _ensure_logged_in(self):
        await self._page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
        await _delay(1, 2)
        if any(k in self._page.url for k in ("login", "authwall", "checkpoint")):
            if headless():
                raise RuntimeError(
                    "LinkedIn needs a saved login. Run once with APPLY_HEADLESS=false and sign in "
                    "in the browser window that opens."
                )
            await self._page.goto("https://www.linkedin.com/login")
            print("[Bot] Waiting for manual LinkedIn login (90s)...")
            await self._page.wait_for_url("**/feed/**", timeout=90_000)
        await self._context.storage_state(path=str(SESSION_PATH))

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
        await self._ensure_logged_in()
        self._meta = {"url": job_url, "cover_letter": False}
        page = self._page

        await page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
        await _delay(2, 3)

        # /api/scrape is usually blocked by LinkedIn, so read the title and company
        # here for the tracker.
        for key, sel in (
            ("role", "h1.top-card-layout__title, h1.job-details-jobs-unified-top-card__job-title"),
            ("company", "a.topcard__org-name-link, .job-details-jobs-unified-top-card__company-name"),
        ):
            try:
                self._meta[key] = (await page.locator(sel).first.text_content(timeout=3000) or "").strip()
            except Exception:
                pass

        for sel in ("button.jobs-apply-button", "button:has-text('Easy Apply')"):
            if await _safe_click(page, sel, timeout=5000):
                break
        else:
            raise RuntimeError("Easy Apply button not found. This job may require applying on the company website.")
        await _delay(2, 3)

        report = FillReport()
        for _ in range(10):
            await _delay(1.0, 1.8)
            # LinkedIn hides its file input behind an "Upload resume" button.
            upload = page.locator("button:has-text('Upload resume'), label:has-text('Upload resume')").first
            if "Resume (PDF)" not in report.filled and await upload.count():
                await page.locator("input[type='file']").first.set_input_files(str(self._resume.path))
                report.add_filled("Resume (PDF)")

            step_needs = await fill_page(page, profile, screening_answers, cover_letter, self._resume, report, MODAL)

            if await page.locator(SUBMIT_BTN).count() or step_needs:
                break  # at the review step, or the candidate must answer something first
            if await page.locator(REVIEW_BTN).count():
                await _safe_click(page, REVIEW_BTN)
                await _delay(1.5, 2)
                break
            if not await _safe_click(page, NEXT_BTN):
                # No known navigation button. Stop here rather than clicking whatever
                # button is last in the footer, which may be the submit.
                break

        self._meta["cover_letter"] = any("cover letter" in f.lower() for f in report.filled)
        screenshot = await page.screenshot(full_page=True)
        return {"screenshot": screenshot, "fields_filled": report.filled, "needs_input": report.needs_input}

    async def submit(self) -> dict:
        btn = self._page.locator(SUBMIT_BTN).first
        if not await btn.count() or not await btn.is_visible():
            return {"status": "failed", "detail": "Submit button not found. Finish the remaining steps in the browser window."}
        return await click_submit(self._page, btn)

    @property
    def meta(self) -> dict:
        return self._meta

    async def close(self):
        try:
            if self._context:
                await self._context.storage_state(path=str(SESSION_PATH))
        except Exception:
            pass
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        finally:
            if self._resume:
                self._resume.remove()

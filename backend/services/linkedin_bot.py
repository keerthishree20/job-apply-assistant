import asyncio
import base64
import json
import random
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

SESSION_PATH = Path("sessions/linkedin.json")
SESSION_PATH.parent.mkdir(exist_ok=True)


async def _human_delay():
    await asyncio.sleep(random.uniform(0.6, 1.4))


class LinkedInBot:
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._meta: dict = {}

    async def _launch(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=False)
        storage = json.loads(SESSION_PATH.read_text()) if SESSION_PATH.exists() else None
        self._context = await self._browser.new_context(storage_state=storage)
        self._page = await self._context.new_page()

    async def _ensure_logged_in(self):
        await self._page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        if "login" in self._page.url or "authwall" in self._page.url:
            await self._page.goto("https://www.linkedin.com/login")
            # Wait up to 60 seconds for the user to log in manually
            await self._page.wait_for_url("**/feed/**", timeout=60_000)
        await self._context.storage_state(path=str(SESSION_PATH))

    async def _upload_resume(self, pdf_base64: str):
        tmp = Path("sessions/resume_upload.pdf")
        tmp.write_bytes(base64.b64decode(pdf_base64))
        file_input = self._page.locator("input[type='file']").first
        if await file_input.count():
            await file_input.set_input_files(str(tmp))
            await _human_delay()

    async def _fill_text(self, selector: str, value: str):
        el = self._page.locator(selector).first
        if await el.count():
            await el.click()
            await el.fill("")
            await el.type(value, delay=40)
            await _human_delay()

    async def _answer_screening_on_page(self, answers: list[dict]):
        for qa in answers:
            question_lower = qa["question"].lower()
            inputs = await self._page.locator("input[type='text'], textarea").all()
            for inp in inputs:
                label_text = ""
                label = await inp.evaluate(
                    "el => el.labels?.[0]?.textContent || el.placeholder || ''"
                )
                if label_text := label.lower():
                    if any(word in label_text for word in question_lower.split()[:3]):
                        await inp.fill(qa["answer"])
                        await _human_delay()
                        break

    async def fill_form(
        self,
        job_url: str,
        resume_pdf_base64: str,
        profile: dict,
        screening_answers: list[dict],
    ) -> dict:
        await self._launch()
        await self._ensure_logged_in()

        self._meta = {"url": job_url, "cover_letter": bool(screening_answers)}

        await self._page.goto(job_url, wait_until="domcontentloaded")
        await _human_delay()

        # Extract job title and company for tracker
        try:
            title_el = await self._page.locator("h1.top-card-layout__title").first.text_content()
            self._meta["role"] = (title_el or "").strip()
        except Exception:
            self._meta["role"] = ""
        try:
            company_el = await self._page.locator("a.topcard__org-name-link").first.text_content()
            self._meta["company"] = (company_el or "").strip()
        except Exception:
            self._meta["company"] = ""

        easy_apply = self._page.locator("button.jobs-apply-button").first
        if not await easy_apply.count():
            raise RuntimeError("Easy Apply button not found for this job.")
        await easy_apply.click()
        await _human_delay()

        fields_filled: list[str] = []

        # Loop through form pages
        for _ in range(8):
            await _human_delay()

            # Fill basic fields
            for selector, key, label in [
                ("input[id*='phoneNumber']", "phone", "phone"),
                ("input[id*='city']", "college", "city"),
            ]:
                if profile.get(key):
                    el = self._page.locator(selector).first
                    if await el.count():
                        await el.fill(profile[key])
                        fields_filled.append(label)
                        await _human_delay()

            await self._upload_resume(resume_pdf_base64)
            if "resume" not in fields_filled:
                fields_filled.append("resume")

            await self._answer_screening_on_page(screening_answers)

            next_btn = self._page.locator("button[aria-label='Continue to next step']").first
            review_btn = self._page.locator("button[aria-label='Review your application']").first

            if await review_btn.count():
                await review_btn.click()
                await _human_delay()
                break
            elif await next_btn.count():
                await next_btn.click()
            else:
                break

        screenshot_bytes = await self._page.screenshot(full_page=False)
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

        return {
            "screenshot_base64": screenshot_b64,
            "fields_filled": fields_filled,
        }

    async def submit(self) -> dict:
        submit_btn = self._page.locator("button[aria-label='Submit application']").first
        if not await submit_btn.count():
            raise RuntimeError("Submit button not found.")
        await submit_btn.click()
        await _human_delay()
        self._meta["resume_snippet"] = ""
        return self._meta

    async def close(self):
        if self._context:
            await self._context.storage_state(path=str(SESSION_PATH))
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

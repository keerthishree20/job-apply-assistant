import asyncio
import base64
import json
import random
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

SESSION_DIR = Path("sessions")
SESSION_DIR.mkdir(exist_ok=True)

ATS_APPLY_CONFIGS = {
    "myworkdayjobs.com": {
        "apply_btn": "a[data-automation-id='applyButton']",
        "first_name": "input[data-automation-id='legalNameSection_firstName']",
        "last_name": "input[data-automation-id='legalNameSection_lastName']",
        "email": "input[data-automation-id='email']",
        "phone": "input[data-automation-id='phone']",
        "resume_upload": "input[type='file']",
        "next_btn": "button[data-automation-id='bottom-navigation-next-btn']",
        "submit_btn": "button[data-automation-id='bottom-navigation-next-btn']",
    },
    "boards.greenhouse.io": {
        "apply_btn": "a#apply_button",
        "first_name": "input#first_name",
        "last_name": "input#last_name",
        "email": "input#email",
        "phone": "input#phone",
        "resume_upload": "input[type='file']",
        "next_btn": None,
        "submit_btn": "input[type='submit']",
    },
    "greenhouse.io": {
        "apply_btn": "a#apply_button",
        "first_name": "input#first_name",
        "last_name": "input#last_name",
        "email": "input#email",
        "phone": "input#phone",
        "resume_upload": "input[type='file']",
        "next_btn": None,
        "submit_btn": "input[type='submit']",
    },
    "jobs.lever.co": {
        "apply_btn": "a.template-btn-submit",
        "first_name": "input[name='name']",
        "last_name": None,
        "email": "input[name='email']",
        "phone": "input[name='phone']",
        "resume_upload": "input[type='file']",
        "next_btn": None,
        "submit_btn": "button[type='submit']",
    },
    "smartrecruiters.com": {
        "apply_btn": "a.apply-button",
        "first_name": "input[id='firstName']",
        "last_name": "input[id='lastName']",
        "email": "input[id='email']",
        "phone": "input[id='phoneNumber']",
        "resume_upload": "input[type='file']",
        "next_btn": "button.navigation-btn-next",
        "submit_btn": "button[data-test='submit-button']",
    },
}


async def _human_delay():
    await asyncio.sleep(random.uniform(0.6, 1.4))


async def _fill(page: Page, selector: str | None, value: str):
    if not selector or not value:
        return
    el = page.locator(selector).first
    if await el.count():
        await el.fill(value)
        await _human_delay()


class ATSBot:
    def __init__(self, ats_type: str):
        self._ats_type = ats_type
        self._config = ATS_APPLY_CONFIGS.get(ats_type, {})
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._meta: dict = {}

    async def _launch(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=False)
        session_file = SESSION_DIR / f"{self._ats_type.replace('.', '_')}.json"
        storage = json.loads(session_file.read_text()) if session_file.exists() else None
        self._context = await self._browser.new_context(storage_state=storage)
        self._page = await self._context.new_page()

    async def fill_form(
        self,
        job_url: str,
        resume_pdf_base64: str,
        profile: dict,
        screening_answers: list[dict],
    ) -> dict:
        await self._launch()
        self._meta = {"url": job_url, "company": "", "role": "", "cover_letter": False}
        cfg = self._config

        await self._page.goto(job_url, wait_until="domcontentloaded")
        await _human_delay()

        if cfg.get("apply_btn"):
            btn = self._page.locator(cfg["apply_btn"]).first
            if await btn.count():
                await btn.click()
                await _human_delay()

        # Split name into first/last
        name_parts = profile.get("name", "").split(" ", 1)
        first = name_parts[0]
        last = name_parts[1] if len(name_parts) > 1 else ""

        await _fill(self._page, cfg.get("first_name"), first)
        await _fill(self._page, cfg.get("last_name"), last)
        await _fill(self._page, cfg.get("email"), profile.get("email", ""))
        await _fill(self._page, cfg.get("phone"), profile.get("phone", ""))

        # Upload resume
        tmp = Path("sessions/resume_upload.pdf")
        tmp.write_bytes(base64.b64decode(resume_pdf_base64))
        upload = self._page.locator(cfg.get("resume_upload", "input[type='file']")).first
        if await upload.count():
            await upload.set_input_files(str(tmp))
            await _human_delay()

        # Click through any next buttons
        if cfg.get("next_btn"):
            for _ in range(5):
                next_btn = self._page.locator(cfg["next_btn"]).first
                if await next_btn.count() and await next_btn.is_visible():
                    await next_btn.click()
                    await _human_delay()
                else:
                    break

        screenshot_bytes = await self._page.screenshot(full_page=False)
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

        return {
            "screenshot_base64": screenshot_b64,
            "fields_filled": ["name", "email", "phone", "resume"],
        }

    async def submit(self) -> dict:
        cfg = self._config
        submit_sel = cfg.get("submit_btn", "button[type='submit']")
        btn = self._page.locator(submit_sel).last
        if not await btn.count():
            raise RuntimeError(f"Submit button not found for ATS: {self._ats_type}")
        await btn.click()
        await _human_delay()
        return self._meta

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

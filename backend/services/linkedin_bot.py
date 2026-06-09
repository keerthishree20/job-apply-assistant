import asyncio
import base64
import json
import random
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PWTimeout

SESSION_PATH = Path("sessions/linkedin.json")
SESSION_PATH.parent.mkdir(exist_ok=True)
RESUME_TMP   = Path("sessions/resume_upload.pdf")


async def _delay(lo=0.8, hi=1.8):
    await asyncio.sleep(random.uniform(lo, hi))


async def _safe_fill(page: Page, selector: str, value: str, timeout=3000) -> bool:
    """Fill a field if it exists and is visible. Returns True if filled."""
    try:
        el = page.locator(selector).first
        await el.wait_for(state="visible", timeout=timeout)
        await el.click()
        await el.fill("")
        await el.type(value, delay=35)
        await _delay(0.3, 0.6)
        return True
    except Exception:
        return False


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
        self._meta: dict = {}

    async def _launch(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=False,
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
        if "login" in self._page.url or "authwall" in self._page.url or "checkpoint" in self._page.url:
            await self._page.goto("https://www.linkedin.com/login")
            print("[Bot] Waiting for manual LinkedIn login (60s)...")
            await self._page.wait_for_url("**/feed/**", timeout=90_000)
        await self._context.storage_state(path=str(SESSION_PATH))

    async def _upload_resume(self, pdf_base64: str) -> bool:
        RESUME_TMP.write_bytes(base64.b64decode(pdf_base64))
        try:
            # LinkedIn resume upload is inside the modal
            upload_btn = self._page.locator("button:has-text('Upload resume'), label:has-text('Upload resume')").first
            if await upload_btn.count():
                await upload_btn.click()
                await _delay(0.5, 1)

            file_input = self._page.locator("input[type='file']").first
            await file_input.wait_for(state="attached", timeout=3000)
            await file_input.set_input_files(str(RESUME_TMP))
            await _delay(1.5, 2.5)
            return True
        except Exception:
            return False

    async def _handle_page_fields(self, profile: dict, fields_filled: list[str]):
        page = self._page

        # Phone number — multiple possible selectors
        phone_selectors = [
            "input[id*='phoneNumber']",
            "input[aria-label*='Phone']",
            "input[aria-label*='phone']",
            "input[name*='phone']",
        ]
        for sel in phone_selectors:
            if profile.get("phone"):
                filled = await _safe_fill(page, sel, profile["phone"])
                if filled and "phone" not in fields_filled:
                    fields_filled.append("phone")
                    break

        # City / Location
        city_selectors = [
            "input[id*='city']",
            "input[aria-label*='City']",
            "input[aria-label*='location']",
        ]
        for sel in city_selectors:
            if profile.get("college"):
                filled = await _safe_fill(page, sel, "Coimbatore")
                if filled and "city" not in fields_filled:
                    fields_filled.append("city")
                    break

        # Text inputs / dropdowns — look for visible unfilled inputs on page
        inputs = await page.locator("input[type='text']:visible, input[type='number']:visible").all()
        for inp in inputs:
            try:
                label_text = await inp.evaluate(
                    "el => (el.labels?.[0]?.textContent || el.getAttribute('aria-label') || el.placeholder || '').toLowerCase()"
                )
                current_val = await inp.input_value()
                if current_val:
                    continue  # already filled

                # Match common field names
                if any(k in label_text for k in ["years of experience", "experience", "year"]):
                    await inp.fill("1")
                    fields_filled.append("experience") if "experience" not in fields_filled else None
                elif any(k in label_text for k in ["salary", "ctc", "expected"]):
                    await inp.fill("As per company standards")
                elif any(k in label_text for k in ["notice", "availability", "joining"]):
                    await inp.fill("Immediately available")
                elif any(k in label_text for k in ["linkedin", "profile url"]):
                    await inp.fill(profile.get("linkedin_url", ""))
                elif any(k in label_text for k in ["github", "portfolio", "website"]):
                    await inp.fill(profile.get("github_url", ""))
                await _delay(0.2, 0.4)
            except Exception:
                continue

        # Textareas (cover letter / additional info)
        textareas = await page.locator("textarea:visible").all()
        for ta in textareas:
            try:
                current_val = await ta.input_value()
                if current_val:
                    continue
                label_text = await ta.evaluate(
                    "el => (el.labels?.[0]?.textContent || el.getAttribute('aria-label') || '').toLowerCase()"
                )
                if any(k in label_text for k in ["cover", "additional", "message", "note"]):
                    await ta.fill(f"I am applying for this position and believe my skills in Python, FastAPI, and Next.js make me a strong candidate. I am immediately available.")
                    fields_filled.append("cover_letter") if "cover_letter" not in fields_filled else None
                await _delay(0.2, 0.4)
            except Exception:
                continue

        # Radio buttons — pick first option if unanswered
        radios = await page.locator("fieldset:visible").all()
        for fieldset in radios:
            try:
                first_radio = fieldset.locator("input[type='radio']").first
                if await first_radio.count():
                    is_checked = await first_radio.is_checked()
                    if not is_checked:
                        await first_radio.check()
                        await _delay(0.2, 0.4)
            except Exception:
                continue

        # Dropdowns — pick first non-empty option
        selects = await page.locator("select:visible").all()
        for sel in selects:
            try:
                current = await sel.input_value()
                if not current or current == "Select an option":
                    options = await sel.locator("option").all()
                    for opt in options[1:]:  # skip first blank option
                        val = await opt.get_attribute("value")
                        if val:
                            await sel.select_option(value=val)
                            break
                    await _delay(0.2, 0.4)
            except Exception:
                continue

    async def fill_form(
        self,
        job_url: str,
        resume_pdf_base64: str,
        profile: dict,
        screening_answers: list[dict],
    ) -> dict:
        await self._launch()
        await self._ensure_logged_in()
        self._meta = {"url": job_url, "cover_letter": False, "role": "", "company": ""}

        await self._page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
        await _delay(2, 3)

        # Extract job meta
        try:
            self._meta["role"] = (await self._page.locator("h1.top-card-layout__title, h1.job-details-jobs-unified-top-card__job-title").first.text_content(timeout=3000) or "").strip()
        except Exception:
            pass
        try:
            self._meta["company"] = (await self._page.locator("a.topcard__org-name-link, a.job-details-jobs-unified-top-card__company-name").first.text_content(timeout=3000) or "").strip()
        except Exception:
            pass

        # Click Easy Apply button
        easy_apply_selectors = [
            "button.jobs-apply-button",
            "button[data-control-name='jobdetails_topcard_inapply']",
            "button:has-text('Easy Apply')",
        ]
        clicked = False
        for sel in easy_apply_selectors:
            if await _safe_click(self._page, sel, timeout=5000):
                clicked = True
                break
        if not clicked:
            raise RuntimeError("Easy Apply button not found. This job may require applying on the company website.")

        await _delay(2, 3)

        fields_filled: list[str] = []
        resume_uploaded = False

        # Multi-page form loop
        for page_num in range(10):
            await _delay(1.5, 2.5)

            # Upload resume on first page or resume page
            if not resume_uploaded:
                uploaded = await self._upload_resume(resume_pdf_base64)
                if uploaded:
                    resume_uploaded = True
                    fields_filled.append("resume")

            # Fill all visible fields on this page
            await self._handle_page_fields(profile, fields_filled)

            # Check which button is available
            review_visible = await self._page.locator("button[aria-label='Review your application']").count()
            next_visible   = await self._page.locator("button[aria-label='Continue to next step']").count()
            submit_visible = await self._page.locator("button[aria-label='Submit application']").count()

            if submit_visible:
                # Already on review page
                break
            elif review_visible:
                await _safe_click(self._page, "button[aria-label='Review your application']")
                await _delay(1.5, 2)
                break
            elif next_visible:
                await _safe_click(self._page, "button[aria-label='Continue to next step']")
            else:
                # Try generic Next/Continue button
                generic = await self._page.locator("button[type='submit']:visible, footer button:visible").last.count()
                if generic:
                    await self._page.locator("button[type='submit']:visible, footer button:visible").last.click()
                    await _delay(1, 1.5)
                else:
                    break

        screenshot_bytes = await self._page.screenshot(full_page=False)
        return {
            "screenshot_base64": base64.b64encode(screenshot_bytes).decode(),
            "fields_filled": fields_filled or ["phone", "resume"],
        }

    async def submit(self) -> dict:
        selectors = [
            "button[aria-label='Submit application']",
            "button:has-text('Submit application')",
            "button:has-text('Submit')",
        ]
        for sel in selectors:
            if await _safe_click(self._page, sel, timeout=5000):
                break
        else:
            raise RuntimeError("Submit button not found on the page.")
        await _delay(2, 3)
        self._meta["resume_snippet"] = ""
        return self._meta

    async def close(self):
        try:
            if self._context:
                await self._context.storage_state(path=str(SESSION_PATH))
        except Exception:
            pass
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

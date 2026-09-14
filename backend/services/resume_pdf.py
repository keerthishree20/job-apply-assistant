"""Turn the tailored resume text into a real PDF.

The frontend used to base64 the plain text and send it as `resume_pdf_base64`, so
every application uploaded a text file with a .pdf name. This renders the text
through headless Chromium instead: Playwright is already a dependency, so a real
PDF costs no new package.

The renderer always runs headless, whatever APPLY_HEADLESS says. `page.pdf()` is
only supported by headless Chromium, and it is a separate browser from the bot's.
"""

import html
import re

from playwright.async_api import async_playwright

_BULLET = re.compile(r"^\s*[-•*▪●]\s+")

_CSS = """
@page { size: A4; margin: 16mm 16mm; }
body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 10.5pt; line-height: 1.38; color: #111; }
h1 { font-size: 18pt; margin: 0 0 4pt; }
h2 { font-size: 11pt; letter-spacing: .06em; border-bottom: 1px solid #999; margin: 12pt 0 4pt; padding-bottom: 2pt; }
p { margin: 0 0 2pt; }
ul { margin: 0 0 4pt 14pt; padding: 0; }
li { margin: 0 0 1.5pt; }
"""


def _is_heading(line: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", line)
    return 2 < len(letters) and letters.isupper() and len(line) <= 60


def resume_html(text: str) -> str:
    """Plain resume text to simple semantic HTML. First non-empty line is the name."""
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    parts: list[str] = []
    in_list = False
    title_done = False
    for line in lines:
        if not line.strip():
            if in_list:
                parts.append("</ul>")
                in_list = False
            continue
        esc = html.escape(line.strip())
        if not title_done:
            parts.append(f"<h1>{esc}</h1>")
            title_done = True
            continue
        if _BULLET.match(line):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{html.escape(_BULLET.sub('', line).strip())}</li>")
            continue
        if in_list:
            parts.append("</ul>")
            in_list = False
        parts.append(f"<h2>{esc}</h2>" if _is_heading(line) else f"<p>{esc}</p>")
    if in_list:
        parts.append("</ul>")
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>{''.join(parts)}</body></html>"


async def render_resume_pdf(text: str) -> bytes:
    if not text.strip():
        raise ValueError("Resume text is empty.")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(resume_html(text), wait_until="load")
            return await page.pdf(format="A4", print_background=True)
        finally:
            await browser.close()

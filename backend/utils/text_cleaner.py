import re
from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\t', ' ', text)
    return text.strip()


def extract_largest_text_block(soup: BeautifulSoup) -> str:
    """Fallback: find the largest <div> text block by character count."""
    candidates = []
    for tag in soup.find_all(['div', 'section', 'article', 'main']):
        text = tag.get_text(separator='\n', strip=True)
        if len(text) > 200:
            candidates.append(text)
    if not candidates:
        return soup.get_text(separator='\n', strip=True)
    return clean_text(max(candidates, key=len))


def remove_boilerplate(soup: BeautifulSoup) -> None:
    """Remove nav, footer, header, script, style tags in-place."""
    for tag in soup(['nav', 'footer', 'header', 'script', 'style', 'noscript',
                     'aside', 'form', 'button', 'iframe']):
        tag.decompose()

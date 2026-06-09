import httpx
from bs4 import BeautifulSoup
from utils.text_cleaner import clean_text, extract_largest_text_block, remove_boilerplate

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

JOB_BOARD_CONFIGS = {
    "linkedin.com": {
        "desc": "div.description__text",
        "title": "h1.top-card-layout__title",
        "company": "a.topcard__org-name-link",
    },
    "indeed.com": {
        "desc": "#jobDescriptionText",
        "title": "h1.jobsearch-JobInfoHeader-title",
        "company": "div[data-testid='inlineHeader-companyName']",
    },
    "naukri.com": {
        "desc": "div.job-desc",
        "title": "h1.jd-header-title",
        "company": "a.jd-header-comp-name",
    },
    "internshala.com": {
        "desc": "div#about-internship",
        "title": "h1.heading_4",
        "company": "a.link_display_like_text",
    },
}

ATS_CONFIGS = {
    "myworkdayjobs.com": {
        "desc": "div[data-automation-id='jobPostingDescription']",
        "title": "h2[data-automation-id='jobPostingHeader']",
        "company": None,
    },
    "boards.greenhouse.io": {
        "desc": "div#content",
        "title": "h1.app-title",
        "company": "h2.company-name",
    },
    "greenhouse.io": {
        "desc": "div.job__description",
        "title": "h1.job-title",
        "company": None,
    },
    "jobs.lever.co": {
        "desc": "div.section-wrapper.page-full-width",
        "title": "h2",
        "company": None,
    },
    "icims.com": {
        "desc": "div.iCIMS_JobContent",
        "title": "h1.iCIMS_Header",
        "company": None,
    },
    "taleo.net": {
        "desc": "div#requisitionDescriptionInterface",
        "title": "span.jobtitle",
        "company": None,
    },
    "smartrecruiters.com": {
        "desc": "div.job-sections",
        "title": "h1.job-title",
        "company": "span.hiring-company-name",
    },
}


def detect_site(url: str) -> tuple[str, dict | None]:
    for pattern, config in JOB_BOARD_CONFIGS.items():
        if pattern in url:
            return pattern, config
    for pattern, config in ATS_CONFIGS.items():
        if pattern in url:
            return pattern, config
    return "unknown", None


def _select_text(soup: BeautifulSoup, selector: str | None) -> str:
    if not selector:
        return ""
    el = soup.select_one(selector)
    return clean_text(el.get_text()) if el else ""


async def scrape_job(url: str) -> dict:
    site, config = detect_site(url)

    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=HEADERS)
            resp.raise_for_status()
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError):
            return {
                "error": "blocked",
                "message": "Could not scrape this URL. Please paste the job description manually.",
            }

    soup = BeautifulSoup(resp.text, "html.parser")
    remove_boilerplate(soup)

    if config:
        description = _select_text(soup, config.get("desc"))
        title = _select_text(soup, config.get("title"))
        company = _select_text(soup, config.get("company"))
    else:
        description = ""
        title = ""
        company = ""

    if not description:
        description = extract_largest_text_block(soup)
    if not title:
        title_tag = soup.find("title")
        title = title_tag.get_text().split("|")[0].strip() if title_tag else ""

    if len(description) < 100:
        return {
            "error": "blocked",
            "message": "Could not extract job description. Please paste it manually.",
        }

    return {
        "job_title": title,
        "company": company,
        "job_description": description,
        "source": site,
    }

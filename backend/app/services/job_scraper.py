"""
Job URL Scraper — extracts job posting data from any URL.

Supports LinkedIn, Indeed, Glassdoor, and generic job pages.
Uses httpx + BeautifulSoup to fetch and parse the page.

LinkedIn strategy: tries the PUBLIC guest API first (no login required),
then falls back to parsing the direct page HTML.
Based on legacy/scripts/linkedin_job_fetcher.py.
"""

import re
import json
import logging
import httpx
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


# ── Browser-like headers ─────────────────────────────────────────────────

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def scrape_job_url(url: str) -> dict:
    """
    Scrape a job posting URL and extract structured data.

    Returns dict with keys:
        job_title, company_name, location, description,
        employment_type, seniority_level, work_type, salary_info,
        source_url, raw_html_length
    """
    url = url.strip()

    # ── LinkedIn: use guest API strategy (from legacy) ──────────────
    if "linkedin.com" in url.lower():
        return _scrape_linkedin(url)

    # ── All other sites: fetch page and parse ───────────────────────
    with httpx.Client(
        headers=_HEADERS,
        follow_redirects=True,
        timeout=20,
        verify=False,
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Remove script/style tags to get cleaner text
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    if "indeed.com" in url:
        data = _extract_indeed(soup)
    elif "glassdoor.com" in url:
        data = _extract_glassdoor(soup)
    else:
        data = _extract_generic(soup)

    # Enrich with OG/meta tags as fallback
    data = _enrich_with_meta(soup, data)

    data["source_url"] = url
    data["raw_html_length"] = len(html)

    # Clean up empty strings → None
    for k, v in data.items():
        if isinstance(v, str) and not v.strip():
            data[k] = None

    return data


# ══════════════════════════════════════════════════════════════════════════
# ██  LinkedIn — Guest API strategy (from legacy linkedin_job_fetcher.py)
# ══════════════════════════════════════════════════════════════════════════


def extract_linkedin_job_id(url: str) -> Optional[str]:
    """
    Extract job ID from various LinkedIn URL formats:
      - https://www.linkedin.com/jobs/view/1234567890
      - https://www.linkedin.com/jobs/search/?currentJobId=1234567890&...
      - https://www.linkedin.com/jobs/collections/recommended/?currentJobId=1234567890
    """
    if not url:
        return None

    # Pattern 1: /jobs/view/JOB_ID
    match = re.search(r'/jobs/view/(\d+)', url)
    if match:
        return match.group(1)

    # Pattern 2: currentJobId=JOB_ID in query string
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if 'currentJobId' in params:
        return params['currentJobId'][0]

    return None


def _scrape_linkedin(url: str) -> dict:
    """
    LinkedIn-specific scraper with multi-strategy approach:
      1. Guest API (public, no login) ← from legacy, works best
      2. Direct page parse (fallback)
      3. Meta/OG tag enrichment (last resort)
    """
    data = _empty_data()
    job_id = extract_linkedin_job_id(url)

    with httpx.Client(
        headers=_HEADERS,
        follow_redirects=True,
        timeout=20,
        verify=False,
    ) as client:

        # ── Strategy 1: Guest API (the key fix from legacy) ─────────
        if job_id:
            guest_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
            logger.info(f"LinkedIn: trying guest API for job {job_id}")
            try:
                guest_resp = client.get(guest_url)
                if guest_resp.status_code == 200:
                    guest_soup = BeautifulSoup(guest_resp.text, "html.parser")
                    data = _parse_linkedin_guest(guest_soup, data)
                    if data.get("job_title") and data.get("company_name"):
                        logger.info(f"LinkedIn guest API success: {data['job_title']} at {data['company_name']}")
                        # Normalize URL and finalize
                        data["source_url"] = f"https://www.linkedin.com/jobs/view/{job_id}"
                        data["raw_html_length"] = len(guest_resp.text)
                        _clean_empty(data)
                        return data
                    else:
                        logger.info("LinkedIn guest API: partial data, trying fallback")
                else:
                    logger.info(f"LinkedIn guest API returned {guest_resp.status_code}, trying fallback")
            except Exception as e:
                logger.warning(f"LinkedIn guest API failed: {e}, trying fallback")

        # ── Strategy 2: Direct page parse ───────────────────────────
        logger.info(f"LinkedIn: trying direct page fetch for {url}")
        try:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            data = _parse_linkedin_direct(soup, html, data)

            # Enrich with meta tags
            # Re-parse the original HTML since we decomposed elements
            meta_soup = BeautifulSoup(html, "html.parser")
            data = _enrich_with_meta(meta_soup, data)

            data["source_url"] = url
            data["raw_html_length"] = len(html)

        except Exception as e:
            logger.warning(f"LinkedIn direct page fetch failed: {e}")
            data["source_url"] = url
            data["raw_html_length"] = 0

    _clean_empty(data)
    return data


def _parse_linkedin_guest(soup: BeautifulSoup, data: dict) -> dict:
    """
    Parse the LinkedIn guest/public job API response.
    Uses selectors from the battle-tested legacy linkedin_job_fetcher.py.
    """
    # Job title (note: guest API uses h2, not h1)
    title_el = (
        soup.find("h2", class_="top-card-layout__title")
        or soup.find("h1", class_="top-card-layout__title")
        or soup.find("h1", class_="topcard__title")
        or soup.select_one("h1[class*='job-title']")
        or soup.find("h2")
    )
    if title_el:
        data["job_title"] = title_el.get_text(strip=True)

    # Company name
    company_el = (
        soup.find("a", class_="topcard__org-name-link")
        or soup.find("span", class_="topcard__flavor")
        or soup.select_one("a[class*='company-name']")
    )
    if company_el:
        data["company_name"] = company_el.get_text(strip=True)

    # Location
    loc_el = (
        soup.find("span", class_="topcard__flavor--bullet")
        or soup.select_one("span[class*='location']")
    )
    if loc_el:
        data["location"] = loc_el.get_text(strip=True)

    # Job description
    desc_el = (
        soup.find("div", class_="description__text")
        or soup.find("div", class_="show-more-less-html__markup")
        or soup.select_one("section[class*='description']")
    )
    if desc_el:
        data["description"] = desc_el.get_text(separator="\n", strip=True)

    # Job criteria (seniority, employment type, etc.)
    criteria_items = soup.select("li.description__job-criteria-item")
    for item in criteria_items:
        header = item.select_one("h3")
        value = item.select_one("span")
        if header and value:
            label = header.get_text(strip=True).lower()
            val = value.get_text(strip=True)
            if "seniority" in label:
                data["seniority_level"] = val
            elif "employment" in label or "type" in label:
                data["employment_type"] = val

    # Also try JSON-LD if present
    data = _extract_jsonld(soup, data)

    return data


def _parse_linkedin_direct(soup: BeautifulSoup, html: str, data: dict) -> dict:
    """
    Parse the regular LinkedIn job view page (logged-out view).
    Fallback when guest API doesn't work.
    """
    # Title — try multiple selectors
    if not data.get("job_title"):
        title_el = (
            soup.select_one("h1.top-card-layout__title")
            or soup.select_one("h1.topcard__title")
            or soup.select_one("h1[class*='job-title']")
            or soup.select_one(".job-details-jobs-unified-top-card__job-title")
            or soup.select_one("h1")
        )
        if title_el:
            data["job_title"] = title_el.get_text(strip=True)

    # Company
    if not data.get("company_name"):
        company_el = (
            soup.select_one("a.topcard__org-name-link")
            or soup.select_one("a[class*='company-name']")
            or soup.select_one(".job-details-jobs-unified-top-card__company-name")
            or soup.select_one("span.topcard__flavor")
            or soup.select_one("span.topcard__org-name")
        )
        if company_el:
            data["company_name"] = company_el.get_text(strip=True)

    # Location
    if not data.get("location"):
        loc_el = (
            soup.select_one("span.topcard__flavor--bullet")
            or soup.select_one("span[class*='location']")
        )
        if loc_el:
            loc_text = loc_el.get_text(strip=True)
            if loc_text and "ago" not in loc_text.lower():
                data["location"] = loc_text

    # Description
    if not data.get("description"):
        desc_el = (
            soup.select_one("div.show-more-less-html__markup")
            or soup.select_one("div.description__text")
            or soup.select_one(".jobs-description__content")
            or soup.select_one("div[class*='job-description']")
            or soup.select_one("section[class*='description']")
        )
        if desc_el:
            data["description"] = desc_el.get_text(separator="\n", strip=True)

    # Try JSON-LD structured data (LinkedIn often includes this)
    data = _extract_jsonld(soup, data)

    # Job criteria list (seniority, type, etc.)
    criteria_items = soup.select("li.description__job-criteria-item")
    for item in criteria_items:
        header = item.select_one("h3")
        value = item.select_one("span")
        if header and value:
            label = header.get_text(strip=True).lower()
            val = value.get_text(strip=True)
            if "seniority" in label and not data.get("seniority_level"):
                data["seniority_level"] = val
            elif ("employment" in label or "type" in label) and not data.get("employment_type"):
                data["employment_type"] = val

    return data


# ── Helpers ──────────────────────────────────────────────────────────────

def _empty_data() -> dict:
    """Return an empty job data dict."""
    return {
        "job_title": None,
        "company_name": None,
        "location": None,
        "description": None,
        "employment_type": None,
        "seniority_level": None,
        "work_type": None,
        "salary_info": None,
    }


def _clean_empty(data: dict) -> None:
    """Convert empty strings to None, in-place."""
    for k, v in data.items():
        if isinstance(v, str) and not v.strip():
            data[k] = None


# ── Indeed ────────────────────────────────────────────────────────────────

def _extract_indeed(soup: BeautifulSoup) -> dict:
    data = _empty_data()

    title_el = soup.select_one("h1.jobsearch-JobInfoHeader-title") or soup.select_one("h1")
    if title_el:
        data["job_title"] = title_el.get_text(strip=True)

    company_el = soup.select_one("div[data-company-name]") or soup.select_one("span.companyName")
    if company_el:
        data["company_name"] = company_el.get_text(strip=True)

    loc_el = soup.select_one("div.companyLocation") or soup.select_one("span.companyLocation")
    if loc_el:
        data["location"] = loc_el.get_text(strip=True)

    desc_el = soup.select_one("div#jobDescriptionText") or soup.select_one("div.jobsearch-jobDescriptionText")
    if desc_el:
        data["description"] = desc_el.get_text(separator="\n", strip=True)

    salary_el = soup.select_one("div#salaryInfoAndJobType") or soup.select_one("span.salary-snippet")
    if salary_el:
        data["salary_info"] = salary_el.get_text(strip=True)

    data = _extract_jsonld(soup, data)
    return data


# ── Glassdoor ─────────────────────────────────────────────────────────────

def _extract_glassdoor(soup: BeautifulSoup) -> dict:
    data = _empty_data()

    title_el = soup.select_one("div[class*='JobDetails'] h1") or soup.select_one("h1")
    if title_el:
        data["job_title"] = title_el.get_text(strip=True)

    desc_el = soup.select_one("div.desc") or soup.select_one("div[class*='JobDesc']")
    if desc_el:
        data["description"] = desc_el.get_text(separator="\n", strip=True)

    data = _extract_jsonld(soup, data)
    return data


# ── Generic (any URL) ─────────────────────────────────────────────────────

def _extract_generic(soup: BeautifulSoup) -> dict:
    """Best-effort extraction from any job page using common patterns."""
    data = _empty_data()

    # Try JSON-LD first — many job sites use it
    data = _extract_jsonld(soup, data)

    # Title fallback
    if not data["job_title"]:
        h1 = soup.select_one("h1")
        if h1:
            data["job_title"] = h1.get_text(strip=True)

    # Description — look for large text blocks
    if not data["description"]:
        # Try common selectors
        for selector in [
            "div[class*='description']",
            "div[class*='job-desc']",
            "div[class*='posting']",
            "article",
            "main",
        ]:
            desc_el = soup.select_one(selector)
            if desc_el:
                text = desc_el.get_text(separator="\n", strip=True)
                if len(text) > 200:  # Only use if substantial
                    data["description"] = text
                    break

        # Ultimate fallback: body text
        if not data["description"]:
            body = soup.select_one("body")
            if body:
                text = body.get_text(separator="\n", strip=True)
                # Trim to a reasonable size
                if len(text) > 500:
                    data["description"] = text[:8000]

    return data


# ── JSON-LD structured data extraction ────────────────────────────────────

def _extract_jsonld(soup: BeautifulSoup, data: dict) -> dict:
    """Extract data from JSON-LD structured data (schema.org/JobPosting)."""
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            ld = json.loads(script.string or "")
            if isinstance(ld, list):
                ld = next((x for x in ld if x.get("@type") == "JobPosting"), None)
            if not ld or ld.get("@type") != "JobPosting":
                continue

            if not data.get("job_title"):
                data["job_title"] = ld.get("title", "")
            if not data.get("company_name"):
                org = ld.get("hiringOrganization", {})
                if isinstance(org, dict):
                    data["company_name"] = org.get("name", "")
            if not data.get("location"):
                loc = ld.get("jobLocation", {})
                if isinstance(loc, dict):
                    addr = loc.get("address", {})
                    if isinstance(addr, dict):
                        parts = [addr.get("addressLocality", ""), addr.get("addressRegion", ""), addr.get("addressCountry", "")]
                        data["location"] = ", ".join(p for p in parts if p)
                    elif isinstance(addr, str):
                        data["location"] = addr
            if not data.get("description"):
                desc = ld.get("description", "")
                if desc:
                    # JSON-LD description may contain HTML
                    desc_soup = BeautifulSoup(desc, "html.parser")
                    data["description"] = desc_soup.get_text(separator="\n", strip=True)
            if not data.get("employment_type"):
                data["employment_type"] = ld.get("employmentType", "")
            if not data.get("salary_info"):
                salary = ld.get("baseSalary", {})
                if isinstance(salary, dict):
                    val = salary.get("value", {})
                    if isinstance(val, dict):
                        data["salary_info"] = f"{val.get('minValue', '')}–{val.get('maxValue', '')} {salary.get('currency', '')}"
                    elif val:
                        data["salary_info"] = str(val)

        except (json.JSONDecodeError, AttributeError, TypeError):
            continue

    return data


# ── Meta tag enrichment ──────────────────────────────────────────────────

def _enrich_with_meta(soup: BeautifulSoup, data: dict) -> dict:
    """Fill gaps using OpenGraph and standard meta tags."""
    if not data.get("job_title"):
        og_title = soup.select_one('meta[property="og:title"]')
        if og_title:
            data["job_title"] = og_title.get("content", "")
        else:
            title_tag = soup.select_one("title")
            if title_tag:
                data["job_title"] = title_tag.get_text(strip=True)

    if not data.get("description"):
        og_desc = soup.select_one('meta[property="og:description"]')
        if og_desc:
            data["description"] = og_desc.get("content", "")
        else:
            meta_desc = soup.select_one('meta[name="description"]')
            if meta_desc:
                data["description"] = meta_desc.get("content", "")

    if not data.get("company_name"):
        og_site = soup.select_one('meta[property="og:site_name"]')
        if og_site:
            data["company_name"] = og_site.get("content", "")

    return data

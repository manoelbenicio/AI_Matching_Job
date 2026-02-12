"""
Job URL Scraper — extracts job posting data from any URL.

Supports LinkedIn, Indeed, Glassdoor, and generic job pages.
Uses httpx + BeautifulSoup to fetch and parse the page.
"""

import re
import json
import httpx
from bs4 import BeautifulSoup
from typing import Optional


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

    # Fetch the page
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

    # Try platform-specific extraction first, then generic
    if "linkedin.com" in url:
        data = _extract_linkedin(soup, html)
    elif "indeed.com" in url:
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


# ── LinkedIn ─────────────────────────────────────────────────────────────

def _extract_linkedin(soup: BeautifulSoup, html: str) -> dict:
    """Extract job data from LinkedIn job posting page."""
    data = {
        "job_title": None,
        "company_name": None,
        "location": None,
        "description": None,
        "employment_type": None,
        "seniority_level": None,
        "work_type": None,
        "salary_info": None,
    }

    # Title — try multiple selectors
    title_el = (
        soup.select_one("h1.top-card-layout__title")
        or soup.select_one("h1.topcard__title")
        or soup.select_one("h1[class*='job-title']")
        or soup.select_one("h1")
    )
    if title_el:
        data["job_title"] = title_el.get_text(strip=True)

    # Company
    company_el = (
        soup.select_one("a.topcard__org-name-link")
        or soup.select_one("a[class*='company-name']")
        or soup.select_one("span.topcard__flavor")
    )
    if company_el:
        data["company_name"] = company_el.get_text(strip=True)

    # Location
    loc_el = (
        soup.select_one("span.topcard__flavor--bullet")
        or soup.select_one("span[class*='location']")
    )
    if loc_el:
        data["location"] = loc_el.get_text(strip=True)

    # Description
    desc_el = (
        soup.select_one("div.show-more-less-html__markup")
        or soup.select_one("div.description__text")
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
            if "seniority" in label:
                data["seniority_level"] = val
            elif "employment" in label or "type" in label:
                data["employment_type"] = val
            elif "function" in label or "industry" in label:
                pass  # could capture if needed

    return data


# ── Indeed ────────────────────────────────────────────────────────────────

def _extract_indeed(soup: BeautifulSoup) -> dict:
    data = {
        "job_title": None,
        "company_name": None,
        "location": None,
        "description": None,
        "employment_type": None,
        "seniority_level": None,
        "work_type": None,
        "salary_info": None,
    }

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
    data = {
        "job_title": None,
        "company_name": None,
        "location": None,
        "description": None,
        "employment_type": None,
        "seniority_level": None,
        "work_type": None,
        "salary_info": None,
    }

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
    data = {
        "job_title": None,
        "company_name": None,
        "location": None,
        "description": None,
        "employment_type": None,
        "seniority_level": None,
        "work_type": None,
        "salary_info": None,
    }

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

            if not data["job_title"]:
                data["job_title"] = ld.get("title", "")
            if not data["company_name"]:
                org = ld.get("hiringOrganization", {})
                if isinstance(org, dict):
                    data["company_name"] = org.get("name", "")
            if not data["location"]:
                loc = ld.get("jobLocation", {})
                if isinstance(loc, dict):
                    addr = loc.get("address", {})
                    if isinstance(addr, dict):
                        parts = [addr.get("addressLocality", ""), addr.get("addressRegion", ""), addr.get("addressCountry", "")]
                        data["location"] = ", ".join(p for p in parts if p)
                    elif isinstance(addr, str):
                        data["location"] = addr
            if not data["description"]:
                desc = ld.get("description", "")
                if desc:
                    # JSON-LD description may contain HTML
                    desc_soup = BeautifulSoup(desc, "html.parser")
                    data["description"] = desc_soup.get_text(separator="\n", strip=True)
            if not data["employment_type"]:
                data["employment_type"] = ld.get("employmentType", "")
            if not data["salary_info"]:
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

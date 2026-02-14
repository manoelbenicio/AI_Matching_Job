"""Jobs CRUD routes."""

import json
import logging
import os
import re
from datetime import datetime as _dt
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlparse
from ..db import db

router = APIRouter()
logger = logging.getLogger(__name__)

_SECTION_DIMENSIONS = {
    "technical_skills": "Technical Skills",
    "experience_level": "Experience Level",
    "industry_domain": "Industry & Domain",
    "leadership_management": "Leadership & Management",
    "certifications_education": "Education & Certifications",
    "cloud_platforms": "Cloud Platforms",
    "soft_skills": "Soft Skills",
    "location_arrangement": "Cultural & Location Fit",
}
_DEFAULT_QUALIFICATION_THRESHOLD = int(os.getenv("SCORE_THRESHOLD_DEFAULT", "80"))


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def _compute_interview_probability(score: int) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"


def _get_qualification_threshold() -> int:
    """Read runtime qualification threshold from app_settings.score_threshold."""
    try:
        with db() as (conn, cur):
            cur.execute("SELECT value FROM app_settings WHERE key = 'score_threshold'")
            row = cur.fetchone()
            if row and row.get("value") is not None:
                return max(0, min(100, int(row["value"])))
    except Exception:
        pass
    return max(0, min(100, _DEFAULT_QUALIFICATION_THRESHOLD))


def _normalize_section(section: dict[str, Any], fallback_dimension: str) -> dict[str, Any]:
    score = _to_int(section.get("score"), 0)
    strong = _to_list(section.get("strong")) or _to_list(section.get("strong_points")) or _to_list(section.get("matches"))
    weak = (
        _to_list(section.get("weak"))
        or _to_list(section.get("weak_points"))
        or _to_list(section.get("weaknesses"))
        or _to_list(section.get("gaps"))
    )
    recommendations = _to_list(section.get("recommendations"))
    weight = section.get("weight")
    dimension = str(section.get("dimension") or section.get("name") or fallback_dimension)

    normalized: dict[str, Any] = {
        "dimension": dimension,
        "score": score,
        "strong": strong,
        "weak": weak,
        "strong_points": strong,
        "weak_points": weak,
        "recommendations": recommendations,
    }
    if isinstance(weight, (int, float)):
        normalized["weight"] = float(weight)
    return normalized


def _normalize_sections(base: dict[str, Any]) -> list[dict[str, Any]]:
    sections = base.get("sections")
    if isinstance(sections, list):
        return [
            _normalize_section(sec, f"Dimension {idx + 1}")
            for idx, sec in enumerate(sections)
            if isinstance(sec, dict)
        ]

    if isinstance(sections, dict):
        normalized: list[dict[str, Any]] = []
        for key, sec in sections.items():
            if isinstance(sec, dict):
                normalized.append(_normalize_section(sec, _SECTION_DIMENSIONS.get(key, str(key).replace("_", " ").title())))
        return normalized

    legacy_sections = base.get("section_evaluations")
    if isinstance(legacy_sections, dict):
        normalized = []
        for key, sec in legacy_sections.items():
            if isinstance(sec, dict):
                copy_sec = dict(sec)
                if "recommendations" not in copy_sec:
                    copy_sec["recommendations"] = _to_list(copy_sec.get("notes"))
                normalized.append(_normalize_section(copy_sec, _SECTION_DIMENSIONS.get(key, str(key).replace("_", " ").title())))
        return normalized

    score_map = base.get("section_scores")
    if isinstance(score_map, dict):
        normalized = []
        for key, val in score_map.items():
            normalized.append(
                _normalize_section(
                    {"score": val, "strong": [], "weak": [], "recommendations": []},
                    _SECTION_DIMENSIONS.get(str(key), str(key).replace("_", " ").title()),
                )
            )
        return normalized

    return []


def _normalize_detailed_score(detailed_score: Any, scored_at: Optional[str] = None) -> Optional[dict[str, Any]]:
    if not detailed_score:
        return None

    if isinstance(detailed_score, str):
        try:
            detailed_score = json.loads(detailed_score)
        except Exception:
            logger.warning("Could not decode detailed_score JSON string")
            return None

    if not isinstance(detailed_score, dict):
        return None

    compare_mode = bool(detailed_score.get("compare_mode"))
    results = detailed_score.get("results") if isinstance(detailed_score.get("results"), dict) else {}
    best_provider = detailed_score.get("best_provider")

    base = detailed_score
    if compare_mode and results:
        if isinstance(best_provider, str) and best_provider in results and isinstance(results[best_provider], dict):
            base = results[best_provider]
        else:
            # deterministic fallback
            first = next((k for k in ("openai", "gemini") if isinstance(results.get(k), dict)), None)
            if first:
                best_provider = first
                base = results[first]

    overall_score = _to_int(base.get("overall_score", base.get("score", 0)), 0)
    overall_justification = (
        base.get("overall_justification")
        or base.get("executive_summary")
        or base.get("justification")
        or ""
    )

    key_risks = _to_list(base.get("key_risks")) or _to_list(base.get("critical_gaps")) or _to_list(base.get("gaps"))
    priorities = (
        _to_list(base.get("cv_enhancement_priority"))
        or _to_list(base.get("cv_enhancement_priorities"))
        or _to_list(base.get("cv_enhancement_suggestions"))
    )

    provider = str(base.get("provider") or "").strip().lower()
    model = str(base.get("model") or "").strip()
    fit_assessment_label = str(base.get("fit_assessment_label") or "").strip()
    gap_analysis = base.get("gap_analysis") if isinstance(base.get("gap_analysis"), dict) else {}
    interview_probability_model = str(
        base.get("interview_probability")
        or base.get("interview_probability_model")
        or ""
    ).strip().upper()
    if interview_probability_model not in {"HIGH", "MEDIUM", "LOW"}:
        interview_probability_model = ""
    interview_probability = (
        interview_probability_model
        if interview_probability_model
        else _compute_interview_probability(overall_score)
    )
    if provider and model:
        model_used = f"{provider.title()} ({model})"
    elif model:
        model_used = model
    elif provider:
        model_used = provider.title()
    else:
        model_used = "Unknown"

    normalized: dict[str, Any] = {
        "overall_score": overall_score,
        "overall_justification": overall_justification,
        "interview_probability_model": interview_probability_model,
        "interview_probability": interview_probability,
        "sections": _normalize_sections(base),
        "key_risks": key_risks,
        "cv_enhancement_priority": priorities,
        "cv_enhancement_priorities": priorities,
        "fit_assessment_label": fit_assessment_label,
        "gap_analysis": gap_analysis,
        "model": model,
        "provider": provider,
        "model_used": model_used,
        "skills_matched": _to_list(base.get("skills_matched")) or _to_list(base.get("key_strengths")),
        "skills_missing": _to_list(base.get("skills_missing")) or _to_list(base.get("critical_gaps")),
        "scored_at": scored_at,
    }

    if "compensation_insight" in base:
        normalized["compensation_insight"] = base["compensation_insight"]

    if compare_mode:
        normalized["compare_mode"] = True
        normalized["best_provider"] = best_provider
        normalized["results"] = results
        normalized["errors"] = detailed_score.get("errors", {})

    return normalized


def _serialize_job(row) -> dict:
    """Convert a DB row (RealDictRow) to a JSON-safe dict."""
    if not row:
        return {}
    d = dict(row)
    # Convert datetime objects to ISO strings
    for k in ("created_at", "updated_at", "posted_date", "scraped_at", "scored_at", "processed_at", "time_posted"):
        if k not in d or d[k] is None:
            continue
        val = d[k]
        if hasattr(val, "isoformat"):
            d[k] = val.isoformat()
        elif isinstance(val, str):
            # Already serialized by DB adapter or persisted as text
            d[k] = val
        else:
            d[k] = str(val)
    if "detailed_score" in d:
        d["detailed_score"] = _normalize_detailed_score(d.get("detailed_score"), d.get("scored_at"))
    return d


ALLOWED_SORT_COLUMNS = {
    'id', 'job_title', 'company_name', 'score', 'status',
    'work_type', 'location', 'updated_at', 'created_at', 'posted_date',
    'seniority_level', 'employment_type', 'time_posted',
}


class JobUpdate(BaseModel):
    status: Optional[str] = None
    score: Optional[int] = None
    justification: Optional[str] = None
    custom_resume_url: Optional[str] = None
    version: int  # Optimistic lock


class BulkUpdate(BaseModel):
    ids: list[int]
    status: str


@router.get("/jobs/stats")
def job_stats():
    """Get aggregate stats for the dashboard metrics bar."""
    qualification_threshold = _get_qualification_threshold()
    with db() as (conn, cur):
        cur.execute("SELECT COUNT(*) as count FROM jobs")
        total = cur.fetchone()["count"]

        cur.execute("SELECT status, COUNT(*) as count FROM jobs GROUP BY status")
        by_status = {row["status"]: row["count"] for row in cur.fetchall()}

        cur.execute("SELECT AVG(score) as avg_score FROM jobs WHERE score IS NOT NULL")
        avg_row = cur.fetchone()
        avg_score = round(float(avg_row["avg_score"]), 1) if avg_row["avg_score"] else None

        cur.execute("SELECT COUNT(*) as count FROM jobs WHERE score >= %s", [qualification_threshold])
        high_score_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM jobs WHERE created_at >= CURRENT_DATE")
        today_count = cur.fetchone()["count"]

    return {
        "total": total,
        "by_status": by_status,
        "avg_score": avg_score,
        "high_score_count": high_score_count,
        "qualification_threshold": qualification_threshold,
        "today_count": today_count,
    }


@router.patch("/jobs/bulk")
def bulk_update_jobs_route(body: BulkUpdate):
    """Bulk update job statuses."""
    if not body.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")

    placeholders = ", ".join(["%s"] * len(body.ids))
    with db() as (conn, cur):
        cur.execute(
            f"UPDATE jobs SET status = %s, updated_at = NOW() WHERE id IN ({placeholders})",
            [body.status] + body.ids,
        )
        updated = cur.rowcount

    return {"updated": updated}


@router.get("/jobs")
def list_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    status: Optional[str] = None,
    work_type: Optional[str] = None,
    score_min: Optional[int] = None,
    score_max: Optional[int] = None,
    sort: Optional[str] = None,
):
    """List jobs with filtering, pagination, and sorting."""
    conditions = []
    params = []

    if search:
        conditions.append("(job_title ILIKE %s OR company_name ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    if status:
        statuses = [s.strip() for s in status.split(",")]
        placeholders = ", ".join(["%s"] * len(statuses))
        conditions.append(f"status IN ({placeholders})")
        params.extend(statuses)

    if work_type:
        types = [t.strip() for t in work_type.split(",")]
        placeholders = ", ".join(["%s"] * len(types))
        conditions.append(f"work_type IN ({placeholders})")
        params.extend(types)

    if score_min is not None:
        conditions.append("score >= %s")
        params.append(score_min)

    if score_max is not None:
        conditions.append("score <= %s")
        params.append(score_max)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Sorting
    order_clause = "updated_at DESC"
    if sort:
        parts = sort.split(":")
        col = parts[0]
        direction = parts[1].upper() if len(parts) > 1 else "ASC"
        if col in ALLOWED_SORT_COLUMNS and direction in ("ASC", "DESC"):
            # Nulls last for score
            nulls = "NULLS LAST" if col == "score" else ""
            order_clause = f"{col} {direction} {nulls}"

    offset = (page - 1) * limit

    with db() as (conn, cur):
        # Count
        cur.execute(f"SELECT COUNT(*) FROM jobs WHERE {where_clause}", params)
        total = cur.fetchone()["count"]

        # Data
        cur.execute(
            f"""
            SELECT id, job_id, job_title, company_name, location, work_type,
                   employment_type, seniority_level, salary_info, score, status,
                   justification, job_url, apply_url, job_description,
                   custom_resume_url, posted_date, time_posted, sector, num_applicants,
                   created_at, updated_at, version
            FROM jobs
            WHERE {where_clause}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        rows = cur.fetchall()

    return {
        "data": [_serialize_job(r) for r in rows],
        "total": total,
        "page": page,
        "limit": limit,
        "has_more": (page * limit) < total,
    }


@router.get("/jobs/{job_id}")
def get_job(job_id: int):
    """Get a single job by ID."""
    with db() as (conn, cur):
        cur.execute(
            """
            SELECT id, job_id, job_title, company_name, location, work_type,
                   employment_type, seniority_level, salary_info, score, status,
                   justification, score_justification, job_url, apply_url,
                   job_description, custom_resume_url, posted_date, sector,
                   num_applicants, recruiter_name, recruiter_url, company_url,
                   error_message, detailed_score, scraped_at, scored_at, processed_at,
                   created_at, updated_at, version
            FROM jobs WHERE id = %s
            """,
            [job_id],
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(row)


@router.patch("/jobs/{job_id}")
def update_job(job_id: int, body: JobUpdate):
    """Update a single job (with optimistic concurrency via version)."""
    updates = []
    params = []
    changed_fields: list[tuple[str, str | None]] = []  # (field, new_value)

    if body.status is not None:
        updates.append("status = %s")
        params.append(body.status)
        changed_fields.append(("status", body.status))
    if body.score is not None:
        updates.append("score = %s")
        params.append(body.score)
        changed_fields.append(("score", str(body.score)))
    if body.justification is not None:
        updates.append("justification = %s")
        params.append(body.justification)
        changed_fields.append(("justification", body.justification))
    if body.custom_resume_url is not None:
        updates.append("custom_resume_url = %s")
        params.append(body.custom_resume_url)
        changed_fields.append(("custom_resume_url", body.custom_resume_url))

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = NOW()")
    updates.append("version = version + 1")
    params.extend([job_id, body.version])

    with db() as (conn, cur):
        # Grab old values for audit trail
        if changed_fields:
            fields_list = [f[0] for f in changed_fields]
            cur.execute(
                f"SELECT {', '.join(fields_list)} FROM jobs WHERE id = %s",
                [job_id],
            )
            old_row = cur.fetchone()
        else:
            old_row = None

        cur.execute(
            f"""
            UPDATE jobs SET {', '.join(updates)}
            WHERE id = %s AND version = %s
            RETURNING id, job_id, job_title, company_name, location, work_type,
                      employment_type, seniority_level, salary_info, score, status,
                      justification, job_url, apply_url, job_description,
                      custom_resume_url, posted_date, sector, num_applicants,
                      created_at, updated_at, version
            """,
            params,
        )
        row = cur.fetchone()
        if not row:
            # Either job doesn't exist or version mismatch (optimistic lock conflict)
            cur.execute("SELECT id FROM jobs WHERE id = %s", [job_id])
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Version conflict — another update occurred. Refresh and retry.")
            raise HTTPException(status_code=404, detail="Job not found")

        # Insert audit log entries
        for field, new_value in changed_fields:
            action_map = {
                "status": "status_change",
                "score": "score_change",
                "justification": "justification_change",
                "custom_resume_url": "resume_url_change",
            }
            old_val = str(old_row[field]) if old_row and old_row.get(field) is not None else None
            cur.execute(
                """
                INSERT INTO audit_log (job_id, action, field, old_value, new_value)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [job_id, action_map.get(field, "field_change"), field, old_val, new_value],
            )

    return _serialize_job(row)


# ── Excel Export ──────────────────────────────────────────────────────────

@router.get("/jobs/export")
def export_jobs_to_excel(
    status: Optional[str] = Query(None, description="Filter by status"),
    min_score: int = Query(0, description="Minimum score filter"),
    limit: int = Query(1000, description="Max rows"),
    ids: Optional[str] = Query(None, description="Comma-separated job IDs for selected export"),
):
    """Generate and download an Excel file of jobs matching the given filters."""
    from ..services.export_service import generate_excel_export

    job_ids = None
    if ids:
        try:
            job_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid job IDs format")

    try:
        buffer = generate_excel_export(
            status=status,
            min_score=min_score,
            limit=limit,
            job_ids=job_ids,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    timestamp = _dt.now().strftime("%Y%m%d_%H%M")
    filename = f"AI_Job_Matcher_Export_{timestamp}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Job fetch from URL ────────────────────────────────────────────────────

class FetchUrlRequest(BaseModel):
    url: str


def _is_valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and "." in parsed.netloc
    except Exception:
        return False


def _extract_first_http_url(text: str) -> Optional[str]:
    m = re.search(r"https?://[^\s<>'\"`]+", text, flags=re.IGNORECASE)
    return m.group(0) if m else None


def _maybe_linkedin_from_job_id(text: str) -> Optional[str]:
    m = re.search(r"(?:currentJobId=|/jobs/view/)(\d{6,})", text)
    if m:
        return f"https://www.linkedin.com/jobs/view/{m.group(1)}"
    return None


def _normalize_job_url_input(raw: str) -> str:
    """
    Normalize Quick Add input into a usable job URL.

    Handles:
    - Plain URLs
    - Percent-encoded tracking blobs
    - Query params containing the real URL (url/u/redirect/target/etc.)
    - LinkedIn currentJobId only input
    """
    text = (raw or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please paste a job URL.")

    # Strip surrounding punctuation common from copy/paste
    text = text.strip(" \t\r\n<>'\"")

    # Candidate pool from progressively decoded variants
    candidates: list[str] = [text]
    dec = text
    for _ in range(3):
        new_dec = unquote(dec)
        if new_dec == dec:
            break
        candidates.append(new_dec)
        dec = new_dec

    # 1) Direct http(s) URL found in any variant
    for c in candidates:
        direct = _extract_first_http_url(c)
        if direct and _is_valid_http_url(direct):
            return direct

    # 2) Parse as URL-ish and inspect query params for nested URL
    nested_keys = {
        "url", "u", "q", "target", "dest", "destination", "redirect",
        "redirect_url", "continue", "next", "joburl", "job_url", "link", "href",
    }
    for c in candidates:
        maybe = c
        if not maybe.startswith(("http://", "https://")) and "." in maybe:
            maybe = f"https://{maybe}"
        try:
            parsed = urlparse(maybe)
            params = parse_qs(parsed.query)
            for key, values in params.items():
                if key.lower() not in nested_keys:
                    continue
                for v in values:
                    v = unquote(v)
                    nested = _extract_first_http_url(v) or v
                    if nested and _is_valid_http_url(nested):
                        return nested
        except Exception:
            continue

    # 3) LinkedIn job id from tracking blobs or partial paths
    for c in candidates:
        li = _maybe_linkedin_from_job_id(c)
        if li:
            return li

    # 4) LinkedIn path without domain
    for c in candidates:
        path_m = re.search(r"(/jobs/view/\d{6,}[^\s<>'\"`]*)", c)
        if path_m:
            return f"https://www.linkedin.com{path_m.group(1)}"

    # 5) Last resort: if it looks like a host, prepend https
    if text.startswith(("http://", "https://")):
        candidate = text
    elif "." in text:
        candidate = f"https://{text}"
    else:
        candidate = ""

    if candidate and _is_valid_http_url(candidate):
        return candidate

    raise HTTPException(
        status_code=400,
        detail="Invalid URL input. Paste the full job URL (e.g., LinkedIn/Indeed/Glassdoor).",
    )


@router.post("/jobs/fetch-url")
def fetch_job_from_url(body: FetchUrlRequest):
    """
    Accept any job posting URL, scrape the full job data, and either
    return the existing job or create a new record with all extracted fields.
    Supports LinkedIn, Indeed, Glassdoor, and generic job pages.
    """
    from ..services.job_scraper import scrape_job_url

    url = _normalize_job_url_input(body.url)

    # Check if job already exists by URL
    with db() as (conn, cur):
        cur.execute(
            """SELECT id, job_id, job_title, company_name, location, work_type,
                      employment_type, seniority_level, salary_info, score, status,
                      justification, job_url, job_description, created_at, version
               FROM jobs WHERE job_url = %s LIMIT 1""",
            (url,),
        )
        existing = cur.fetchone()
        if existing:
            return {
                "success": True,
                "already_existed": True,
                "job": _serialize_job(existing),
            }

    # Scrape the URL
    try:
        scraped = scrape_job_url(url)
    except Exception as e:
        logger.error(f"Scraping failed for {url}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch job data from URL: {str(e)}"
        )

    job_title = scraped.get("job_title") or "Unknown Position"
    company = scraped.get("company_name") or "Unknown Company"
    description = scraped.get("description") or ""
    location = scraped.get("location")
    employment_type = scraped.get("employment_type")
    seniority_level = scraped.get("seniority_level")
    work_type = scraped.get("work_type")
    salary_info = scraped.get("salary_info")

    # Use the normalized/canonical URL from the scraper if available
    canonical_url = scraped.get("source_url") or url

    # Extract a job_id from the URL (LinkedIn ID or hash)
    # Import the improved extractor that handles currentJobId query param
    from ..services.job_scraper import extract_linkedin_job_id
    li_job_id = extract_linkedin_job_id(url)
    job_id_val = li_job_id if li_job_id else f"url-{abs(hash(url)) % 10**10}"

    # Check again with canonical URL (handles currentJobId → /view/ID normalization)
    if canonical_url != url:
        with db() as (conn, cur):
            cur.execute(
                "SELECT id FROM jobs WHERE job_url = %s LIMIT 1",
                (canonical_url,),
            )
            if cur.fetchone():
                cur.execute(
                    """SELECT id, job_id, job_title, company_name, location, work_type,
                              employment_type, seniority_level, salary_info, score, status,
                              justification, job_url, job_description, created_at, version
                       FROM jobs WHERE job_url = %s LIMIT 1""",
                    (canonical_url,),
                )
                return {
                    "success": True,
                    "already_existed": True,
                    "job": _serialize_job(cur.fetchone()),
                }

    # Check by logical job_id as well (LinkedIn job id is unique across URL variants)
    with db() as (conn, cur):
        cur.execute(
            """SELECT id, job_id, job_title, company_name, location, work_type,
                      employment_type, seniority_level, salary_info, score, status,
                      justification, job_url, job_description, created_at, updated_at, version
               FROM jobs WHERE job_id = %s LIMIT 1""",
            (job_id_val,),
        )
        existing_by_job_id = cur.fetchone()
        if existing_by_job_id:
            return {
                "success": True,
                "already_existed": True,
                "job": _serialize_job(existing_by_job_id),
            }

    # Insert the job into the database
    with db() as (conn, cur):
        cur.execute(
            """INSERT INTO jobs (
                job_id, job_url, job_title, company_name, location,
                work_type, employment_type, seniority_level, salary_info,
                job_description, status, created_at, updated_at, version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', now(), now(), 1)
            ON CONFLICT (job_id) DO UPDATE
            SET updated_at = NOW()
            RETURNING id, job_id, job_title, company_name, location, work_type,
                      employment_type, seniority_level, salary_info, score, status,
                      justification, job_url, job_description, created_at, updated_at, version""",
            (job_id_val, canonical_url, job_title, company, location,
             work_type, employment_type, seniority_level, salary_info,
             description),
        )
        new_job = cur.fetchone()
        conn.commit()

    return {
        "success": True,
        "already_existed": False,
        "job": _serialize_job(new_job),
    }



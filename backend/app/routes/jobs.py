"""Jobs CRUD routes."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from ..db import db

router = APIRouter()


def _serialize_job(row) -> dict:
    """Convert a DB row (RealDictRow) to a JSON-safe dict."""
    if not row:
        return {}
    d = dict(row)
    # Convert datetime objects to ISO strings
    for k in ("created_at", "updated_at", "posted_date", "scraped_at", "scored_at", "processed_at", "time_posted"):
        if k in d and d[k] is not None:
            d[k] = d[k].isoformat()
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
    with db() as (conn, cur):
        cur.execute("SELECT COUNT(*) as count FROM jobs")
        total = cur.fetchone()["count"]

        cur.execute("SELECT status, COUNT(*) as count FROM jobs GROUP BY status")
        by_status = {row["status"]: row["count"] for row in cur.fetchall()}

        cur.execute("SELECT AVG(score) as avg_score FROM jobs WHERE score IS NOT NULL")
        avg_row = cur.fetchone()
        avg_score = round(float(avg_row["avg_score"]), 1) if avg_row["avg_score"] else None

        cur.execute("SELECT COUNT(*) as count FROM jobs WHERE score >= 80")
        high_score_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM jobs WHERE created_at >= CURRENT_DATE")
        today_count = cur.fetchone()["count"]

    return {
        "total": total,
        "by_status": by_status,
        "avg_score": avg_score,
        "high_score_count": high_score_count,
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
                   error_message, scraped_at, scored_at, processed_at,
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
    params.extend([body.version, job_id])

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
from datetime import datetime as _dt

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
import re
import logging

logger = logging.getLogger(__name__)

class FetchUrlRequest(BaseModel):
    url: str


@router.post("/jobs/fetch-url")
def fetch_job_from_url(body: FetchUrlRequest):
    """
    Accept any job posting URL, scrape the full job data, and either
    return the existing job or create a new record with all extracted fields.
    Supports LinkedIn, Indeed, Glassdoor, and generic job pages.
    """
    from ..services.job_scraper import scrape_job_url

    url = body.url.strip()
    if not url.startswith("http"):
        url = "https://" + url

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

    # Extract a job_id from the URL (LinkedIn ID or hash)
    linkedin_match = re.search(r'linkedin\.com/jobs/view/(\d+)', url)
    job_id_val = linkedin_match.group(1) if linkedin_match else f"url-{abs(hash(url)) % 10**10}"

    # Insert the job into the database
    with db() as (conn, cur):
        cur.execute(
            """INSERT INTO jobs (
                job_id, job_url, job_title, company_name, location,
                work_type, employment_type, seniority_level, salary_info,
                job_description, status, created_at, updated_at, version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'new', now(), now(), 1)
            RETURNING id, job_id, job_title, company_name, location, work_type,
                      employment_type, seniority_level, salary_info, score, status,
                      justification, job_url, job_description, created_at, updated_at, version""",
            (job_id_val, url, job_title, company, location,
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


def _serialize_job(row: dict) -> dict:
    """Convert a DB row to a JSON-safe dict."""
    result = dict(row)
    # Convert datetime objects to ISO strings
    for key in ('created_at', 'updated_at', 'posted_date', 'scraped_at', 'scored_at', 'processed_at'):
        if key in result and result[key] is not None:
            result[key] = result[key].isoformat()
    return result


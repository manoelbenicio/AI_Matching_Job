"""Jobs CRUD routes."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..db import db

router = APIRouter()

ALLOWED_SORT_COLUMNS = {
    'id', 'job_title', 'company_name', 'score', 'status',
    'work_type', 'location', 'updated_at', 'created_at', 'posted_date',
    'seniority_level', 'employment_type',
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
                   custom_resume_url, posted_date, sector, num_applicants,
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


@router.patch("/jobs/bulk")
def bulk_update_jobs(body: BulkUpdate):
    """Bulk update job statuses."""
    if not body.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")

    placeholders = ", ".join(["%s"] * len(body.ids))
    with db() as (conn, cur):
        cur.execute(
            f"""
            UPDATE jobs SET status = %s, updated_at = NOW()
            WHERE id IN ({placeholders})
            """,
            [body.status] + body.ids,
        )
        updated = cur.rowcount

    return {"updated": updated}


def _serialize_job(row: dict) -> dict:
    """Convert a DB row to a JSON-safe dict."""
    result = dict(row)
    # Convert datetime objects to ISO strings
    for key in ('created_at', 'updated_at', 'posted_date', 'scraped_at', 'scored_at', 'processed_at'):
        if key in result and result[key] is not None:
            result[key] = result[key].isoformat()
    return result

"""Audit trail routes."""

from fastapi import APIRouter
from ..db import db

router = APIRouter()


@router.get("/audit/{job_id}")
def get_audit_trail(job_id: int):
    """Return all audit events for a job, newest first."""
    with db() as (conn, cur):
        cur.execute(
            """
            SELECT id, job_id, action, field, old_value, new_value, created_at
            FROM audit_log
            WHERE job_id = %s
            ORDER BY created_at DESC
            """,
            [job_id],
        )
        rows = cur.fetchall()

    result = []
    for r in rows:
        item = dict(r)
        if item.get("created_at"):
            item["created_at"] = item["created_at"].isoformat()
        result.append(item)
    return result

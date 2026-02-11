"""Stats routes for the metrics bar."""

from fastapi import APIRouter
from ..db import db

router = APIRouter()


@router.get("/jobs/stats")
def job_stats():
    """Get aggregate stats for the dashboard metrics bar."""
    with db() as (conn, cur):
        # Total
        cur.execute("SELECT COUNT(*) as count FROM jobs")
        total = cur.fetchone()["count"]

        # By status
        cur.execute(
            "SELECT status, COUNT(*) as count FROM jobs GROUP BY status"
        )
        by_status = {row["status"]: row["count"] for row in cur.fetchall()}

        # Avg score (non-null only)
        cur.execute("SELECT AVG(score) as avg_score FROM jobs WHERE score IS NOT NULL")
        avg_row = cur.fetchone()
        avg_score = round(float(avg_row["avg_score"]), 1) if avg_row["avg_score"] else None

        # High score count (≥80)
        cur.execute("SELECT COUNT(*) as count FROM jobs WHERE score >= 80")
        high_score_count = cur.fetchone()["count"]

        # Today count
        cur.execute("SELECT COUNT(*) as count FROM jobs WHERE created_at >= CURRENT_DATE")
        today_count = cur.fetchone()["count"]

    return {
        "total": total,
        "by_status": by_status,
        "avg_score": avg_score,
        "high_score_count": high_score_count,
        "today_count": today_count,
    }

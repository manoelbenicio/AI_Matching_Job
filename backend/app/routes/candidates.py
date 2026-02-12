"""Candidates CRUD routes — CV Manager backend."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..db import db

router = APIRouter()


class CandidateCreate(BaseModel):
    name: str
    email: Optional[str] = ""
    resume_text: str


# ── List all candidates ───────────────────────────────────────────────────
@router.get("/candidates")
def list_candidates():
    """Return all candidates, newest first."""
    with db() as (conn, cur):
        cur.execute("""
            SELECT id, name, email, is_active, created_at,
                   LEFT(resume_text, 120) AS resume_preview
            FROM candidates
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
    return [
        {
            "id": r["id"],
            "name": r.get("name", "Unnamed"),
            "email": r.get("email", ""),
            "is_active": r.get("is_active", False),
            "created_at": str(r.get("created_at", "")),
            "resume_preview": r.get("resume_preview", ""),
        }
        for r in rows
    ]


# ── Get active candidate ─────────────────────────────────────────────────
@router.get("/candidates/active")
def get_active_candidate():
    """Return the currently-active candidate (the one used for scoring)."""
    with db() as (conn, cur):
        cur.execute("""
            SELECT id, name, resume_text
            FROM candidates WHERE is_active = TRUE LIMIT 1
        """)
        row = cur.fetchone()
    if not row:
        return None
    return {"id": row["id"], "name": row.get("name", ""), "resume_text": row.get("resume_text", "")}


# ── Create a candidate ───────────────────────────────────────────────────
@router.post("/candidates")
def create_candidate(body: CandidateCreate):
    """Create a new candidate with resume text."""
    with db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO candidates (name, email, resume_text, is_active, created_at)
            VALUES (%s, %s, %s, FALSE, now())
            RETURNING id, name
            """,
            (body.name, body.email or "", body.resume_text),
        )
        row = cur.fetchone()
        conn.commit()
    return {"id": row["id"], "name": row["name"]}


# ── Set a candidate as active ────────────────────────────────────────────
@router.put("/candidates/{candidate_id}/active")
def set_active(candidate_id: int):
    """Mark a candidate as the active one (deactivate all others)."""
    with db() as (conn, cur):
        cur.execute("UPDATE candidates SET is_active = FALSE WHERE is_active = TRUE")
        cur.execute(
            "UPDATE candidates SET is_active = TRUE WHERE id = %s RETURNING id",
            (candidate_id,),
        )
        row = cur.fetchone()
        if not row:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Candidate not found")
        conn.commit()
    return {"message": f"Candidate {candidate_id} is now active"}


# ── Delete a candidate ───────────────────────────────────────────────────
@router.delete("/candidates/{candidate_id}")
def delete_candidate(candidate_id: int):
    """Delete a candidate by ID."""
    with db() as (conn, cur):
        cur.execute("DELETE FROM candidates WHERE id = %s RETURNING id", (candidate_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Candidate not found")
        conn.commit()
    return {"message": f"Candidate {candidate_id} deleted"}

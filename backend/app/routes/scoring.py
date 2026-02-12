"""
AI Scoring Pipeline — SSE streaming endpoint.

Scores jobs against the candidate resume using OpenAI GPT-4o-mini,
streaming progress to the frontend via Server-Sent Events.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..db import db
from .settings import get_api_key

router = APIRouter()

# ── Cancellation flag (module-level) ─────────────────────────────────────
_cancel_flag = False
_running = False
_progress = {"scored": 0, "total": 0, "started_at": None}

# ── Candidate resume loader ──────────────────────────────────────────────
_RESUME_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "candidate_resume.txt")

def _load_candidate_resume() -> str:
    """Load candidate resume from file, or fall back to DB candidates table."""
    # Try loading from file first
    for path in [_RESUME_FILE, os.path.join(os.getcwd(), "candidate_resume.txt")]:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()

    # Fallback: load from candidates table
    try:
        with db() as (conn, cur):
            cur.execute("SELECT resume_text FROM candidates WHERE is_active = true LIMIT 1")
            row = cur.fetchone()
            if row and row.get("resume_text"):
                return row["resume_text"]
    except Exception:
        pass

    raise RuntimeError(
        "No candidate resume found. Place a candidate_resume.txt in the backend/ "
        "directory or insert a row into the candidates table."
    )

# Load once at module level (lazy on first use)
_cached_resume: Optional[str] = None

def _get_resume() -> str:
    global _cached_resume
    if _cached_resume is None:
        _cached_resume = _load_candidate_resume()
    return _cached_resume




# ── Request / Response models ────────────────────────────────────────────

class ScoringRequest(BaseModel):
    batch_size: int = 25
    status_filter: str = "Pending"  # only score jobs with this status
    sort_by: str = "newest_first"   # newest_first | oldest_first | id


# ── OpenAI helper ────────────────────────────────────────────────────────

def _score_job_openai(job_title: str, company: str, description: str) -> dict:
    """Call OpenAI GPT-4o-mini to score a single job against the resume."""
    from openai import OpenAI

    api_key = get_api_key("OPENAI_API_KEY") or ""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured. Set it in Settings or .env file.")

    client = OpenAI(api_key=api_key)

    system_prompt = """You are an expert LinkedIn job posting filtering agent.
Your task is to determine whether a job posting is suitable for the candidate whose resume is provided.
Think deeply about whether the candidate's skills, experience, and knowledge match the job posting.

Rate the match from 0 to 100:
- 0 = absolutely not suitable
- 100 = extremely suitable (perfect match)

Consider these dimensions:
1. Required skills alignment
2. Seniority level match
3. Industry/domain relevance
4. Location compatibility (remote-friendly counts)
5. Years of experience match

You MUST respond with ONLY valid JSON (no markdown, no code fences):
{
  "score": 75,
  "justification": "2-3 sentence explanation of why this score",
  "skills_matched": ["skill1", "skill2"],
  "skills_missing": ["skill1", "skill2"]
}"""

    user_prompt = f"""Here is the job posting information:
Company Name: {company}
Job Title: {job_title}
Job Posting Description:
{description[:6000]}

Here is the candidate's resume:
{_get_resume()}

Evaluate alignment and generate the JSON output."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=500,
        response_format={"type": "json_object"},
    )

    text = response.choices[0].message.content.strip()
    # Clean markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    result = json.loads(text)
    return {
        "score": int(result.get("score", 0)),
        "justification": result.get("justification", ""),
        "skills_matched": result.get("skills_matched", []),
        "skills_missing": result.get("skills_missing", []),
        "prompt_sent": user_prompt[:500] + "...",
        "raw_response": text,
        "model": model,
        "tokens_used": response.usage.total_tokens if response.usage else 0,
    }


# ── SSE generator ────────────────────────────────────────────────────────

def _sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _scoring_generator(batch_size: int, status_filter: str, sort_by: str = "newest_first"):
    """Generator that yields SSE events as jobs are scored."""
    global _cancel_flag, _running, _progress
    _cancel_flag = False
    _running = True
    _progress = {"scored": 0, "total": 0, "started_at": datetime.now(timezone.utc).isoformat()}

    try:
        # Fetch jobs to score
        with db() as (conn, cur):
            # Determine sort order
            order_clause = {
                "newest_first": "time_posted DESC NULLS LAST, id DESC",
                "oldest_first": "time_posted ASC NULLS LAST, id ASC",
                "id":           "id ASC",
            }.get(sort_by, "time_posted DESC NULLS LAST, id DESC")

            cur.execute(
                f"""
                SELECT id, job_title, company_name, job_description, score
                FROM jobs
                WHERE LOWER(status) = LOWER(%s) AND (score IS NULL OR score = 0)
                ORDER BY {order_clause}
                LIMIT %s
                """,
                [status_filter, batch_size],
            )
            jobs_to_score = [dict(row) for row in cur.fetchall()]

        total = len(jobs_to_score)
        _progress["total"] = total

        if total == 0:
            yield _sse_event("info", {
                "type": "info",
                "message": f"No unscored jobs with status '{status_filter}' found.",
            })
            return

        yield _sse_event("start", {
            "type": "start",
            "total": total,
            "batch_size": batch_size,
            "status_filter": status_filter,
            "started_at": _progress["started_at"],
        })

        scored_count = 0
        total_tokens = 0
        errors = 0

        for job in jobs_to_score:
            if _cancel_flag:
                yield _sse_event("cancelled", {
                    "type": "cancelled",
                    "scored": scored_count,
                    "total": total,
                    "message": "Scoring cancelled by user.",
                })
                return

            job_id = job["id"]
            job_title = job["job_title"] or "Unknown"
            company = job["company_name"] or "Unknown"
            description = job["job_description"] or ""

            # Send "scoring" event before calling AI
            yield _sse_event("scoring", {
                "type": "scoring",
                "job_id": job_id,
                "job_title": job_title,
                "company": company,
                "progress": scored_count,
                "total": total,
            })

            try:
                start_time = time.time()
                result = _score_job_openai(job_title, company, description)
                elapsed = round(time.time() - start_time, 2)

                # Persist to DB
                with db() as (conn, cur):
                    cur.execute(
                        """
                        UPDATE jobs
                        SET score = %s,
                            justification = %s,
                            scored_at = NOW(),
                            updated_at = NOW(),
                            version = version + 1
                        WHERE id = %s
                        """,
                        [result["score"], result["justification"], job_id],
                    )

                scored_count += 1
                total_tokens += result["tokens_used"]
                _progress["scored"] = scored_count

                yield _sse_event("scored", {
                    "type": "scored",
                    "job_id": job_id,
                    "job_title": job_title,
                    "company": company,
                    "score": result["score"],
                    "justification": result["justification"],
                    "skills_matched": result["skills_matched"],
                    "skills_missing": result["skills_missing"],
                    "model": result["model"],
                    "tokens_used": result["tokens_used"],
                    "elapsed_seconds": elapsed,
                    "prompt_preview": result["prompt_sent"],
                    "raw_response": result["raw_response"],
                    "progress": scored_count,
                    "total": total,
                })

            except Exception as e:
                errors += 1
                scored_count += 1
                _progress["scored"] = scored_count

                yield _sse_event("error", {
                    "type": "error",
                    "job_id": job_id,
                    "job_title": job_title,
                    "company": company,
                    "error": str(e),
                    "progress": scored_count,
                    "total": total,
                })

        # Summary
        yield _sse_event("complete", {
            "type": "complete",
            "scored": scored_count - errors,
            "errors": errors,
            "total": total,
            "total_tokens": total_tokens,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })

    finally:
        _running = False


# ── Routes ───────────────────────────────────────────────────────────────

@router.post("/scoring/start")
def start_scoring(body: ScoringRequest):
    """Start an AI scoring run. Returns an SSE stream."""
    global _running
    if _running:
        return StreamingResponse(
            iter([_sse_event("error", {
                "type": "error",
                "message": "A scoring run is already in progress.",
            })]),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        _scoring_generator(body.batch_size, body.status_filter, body.sort_by),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/scoring/stop")
def stop_scoring():
    """Cancel the current scoring run."""
    global _cancel_flag
    if not _running:
        return {"status": "idle", "message": "No scoring run in progress."}
    _cancel_flag = True
    return {"status": "cancelling", "message": "Scoring will stop after current job completes."}


@router.get("/scoring/status")
def scoring_status():
    """Return current scoring run status."""
    return {
        "running": _running,
        "progress": _progress,
    }


@router.get("/scoring/unscored-count")
def unscored_count(status: str = Query("Pending")):
    """Count jobs that haven't been scored yet."""
    with db() as (conn, cur):
        cur.execute(
            "SELECT COUNT(*) FROM jobs WHERE LOWER(status) = LOWER(%s) AND (score IS NULL OR score = 0)",
            [status],
        )
        count = cur.fetchone()["count"]
    return {"count": count, "status_filter": status}


# ── Single-job scoring (for Quick Add ad-hoc flow) ────────────────────────

class SingleScoreRequest(BaseModel):
    job_db_id: int  # The DB primary key (id column)


def _score_job_detailed(job_title: str, company: str, description: str) -> dict:
    """Score a single job with DETAILED section-by-section analysis.
    Returns granular breakdown — not just a number."""
    from openai import OpenAI

    api_key = get_api_key("OPENAI_API_KEY") or ""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured. Set it in Settings or .env file.")

    client = OpenAI(api_key=api_key)

    system_prompt = """You are an elite career advisor and job matching specialist.
Your task is to perform a DEEP, SECTION-BY-SECTION analysis of how well a candidate's resume matches a specific job posting.

You MUST evaluate EACH of the following dimensions independently with a score (0-100) and detailed justification:

1. **Technical Skills** — Do the candidate's technical skills align with what the job requires? Be VERY specific about which skills match and which are missing.
2. **Experience Level** — Does the candidate's years and depth of experience match the seniority expected? Is the candidate overqualified, underqualified, or just right?
3. **Industry & Domain** — Is the candidate's industry background relevant? Do they have domain expertise the role requires?
4. **Leadership & Management** — If the role requires leadership, does the candidate demonstrate it? Team size, scope of responsibility, strategic vs tactical.
5. **Education & Certifications** — Do qualifications match? Are there specific certifications required that the candidate has or lacks?
6. **Cultural & Location Fit** — Remote/hybrid/onsite compatibility. Language requirements. Travel requirements. Company culture alignment.
7. **Keywords & ATS Alignment** — Does the resume contain the exact keywords and phrases from the job description that ATS systems will scan for?

For EACH dimension you MUST provide:
- A score (0-100)
- What's STRONG (specific evidence from the resume)
- What's WEAK or MISSING (specific gaps)
- Actionable RECOMMENDATIONS to improve

CRITICAL: Be brutally honest. If information is missing from the resume, say so. Poor analysis leads to wasted interviews.

You MUST respond with ONLY valid JSON matching this schema:
{
  "overall_score": 75,
  "overall_justification": "2-3 sentence summary explaining the overall fit",
  "sections": [
    {
      "dimension": "Technical Skills",
      "score": 80,
      "strong": ["specific strength 1", "specific strength 2"],
      "weak": ["specific gap 1", "specific gap 2"],
      "recommendations": ["specific action 1", "specific action 2"]
    }
  ],
  "skills_matched": ["skill1", "skill2"],
  "skills_missing": ["skill1", "skill2"],
  "interview_probability": "HIGH|MEDIUM|LOW",
  "key_risks": ["risk1", "risk2"],
  "cv_enhancement_priority": ["section to improve first", "section to improve second"]
}"""

    user_prompt = f"""JOB POSTING:
Company: {company}
Title: {job_title}
Full Description:
{description[:8000]}

CANDIDATE'S RESUME:
{_get_resume()}

Perform the detailed section-by-section analysis now."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=3000,
        response_format={"type": "json_object"},
    )

    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    result = json.loads(text)
    result["model"] = model
    result["tokens_used"] = response.usage.total_tokens if response.usage else 0
    return result


@router.post("/scoring/single")
def score_single_job(body: SingleScoreRequest):
    """
    Score a single job (by DB id) with detailed section-by-section analysis.
    Used by the Quick Add ad-hoc flow after fetching a job URL.
    Returns full breakdown with strengths, weaknesses, and recommendations per dimension.
    """
    with db() as (conn, cur):
        cur.execute(
            """SELECT id, job_title, company_name, job_description
               FROM jobs WHERE id = %s""",
            [body.job_db_id],
        )
        job = cur.fetchone()

    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.get("job_description"):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Job has no description. Fetch the job URL first to get the full posting."
        )

    # Run the detailed scoring
    result = _score_job_detailed(
        job_title=job["job_title"] or "Unknown",
        company=job["company_name"] or "Unknown",
        description=job["job_description"],
    )

    overall_score = int(result.get("overall_score", 0))
    justification = result.get("overall_justification", "")

    # Save score + justification back to the job
    with db() as (conn, cur):
        cur.execute(
            """UPDATE jobs
               SET score = %s,
                   justification = %s,
                   status = 'Scored',
                   updated_at = NOW(),
                   version = version + 1
               WHERE id = %s
               RETURNING version""",
            [overall_score, justification, body.job_db_id],
        )
        conn.commit()

    return {
        "success": True,
        "job_db_id": body.job_db_id,
        "result": result,
    }

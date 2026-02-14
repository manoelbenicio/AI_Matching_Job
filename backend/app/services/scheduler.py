"""
Scheduler Service — APScheduler-based cron for batch scoring.

Reads config from app_settings (key: scheduler_*) with env fallbacks.
Starts a BackgroundScheduler in the FastAPI lifespan.

When auto_cv_generation is enabled, qualified jobs automatically get:
  1. Gap-aware CV enhancement via Gemini
  2. Premium DOCX export
  3. Google Drive upload
  4. Rich Telegram notification with APPLY + CV links
"""

import os
import json
import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger("scheduler")
_DEFAULT_SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD_DEFAULT", "80"))

_scheduler = None


def get_scheduler():
    """Return the global APScheduler instance (if initialised)."""
    return _scheduler


def start_scheduler():
    """Initialise and start the APScheduler."""
    global _scheduler

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("apscheduler not installed — scheduler disabled")
        return

    enabled = os.getenv("SCHEDULER_ENABLED", "false").lower() in ("true", "1", "yes")
    cron_expr = os.getenv("SCHEDULER_CRON", "0 8 * * *")

    # Also check DB settings
    try:
        from ..db import db
        with db() as (conn, cur):
            cur.execute("SELECT key, value FROM app_settings WHERE key LIKE 'scheduler_%'")
            for row in cur.fetchall():
                if row["key"] == "scheduler_enabled":
                    enabled = row["value"].lower() in ("true", "1", "yes")
                elif row["key"] == "scheduler_cron":
                    cron_expr = row["value"]
    except Exception:
        pass

    if not enabled:
        logger.info("Scheduler is disabled (set SCHEDULER_ENABLED=true to enable)")
        return

    _scheduler = BackgroundScheduler()

    # Parse cron: "minute hour day month dow"
    parts = cron_expr.split()
    trigger_kwargs = {}
    if len(parts) >= 5:
        trigger_kwargs = {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4],
        }
    else:
        trigger_kwargs = {"hour": "8", "minute": "0"}

    _scheduler.add_job(
        _run_batch_scoring,
        CronTrigger(**trigger_kwargs),
        id="batch_scoring",
        name="AI Job Scoring Batch",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(f"Scheduler started — cron: {cron_expr}")


def stop_scheduler():
    """Shut down the scheduler gracefully."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")


def get_scheduler_status() -> dict:
    """Return current scheduler status for the settings UI."""
    if not _scheduler or not _scheduler.running:
        return {
            "running": False,
            "next_run": None,
            "cron": os.getenv("SCHEDULER_CRON", "0 8 * * *"),
        }

    jobs = _scheduler.get_jobs()
    next_run = None
    if jobs:
        next_run_dt = jobs[0].next_run_time
        if next_run_dt:
            next_run = next_run_dt.isoformat()

    return {
        "running": True,
        "next_run": next_run,
        "cron": os.getenv("SCHEDULER_CRON", "0 8 * * *"),
        "jobs": len(jobs),
    }


def _is_auto_cv_enabled() -> bool:
    """Check if the autonomous CV pipeline toggle is enabled.

    Reads from app_settings key 'auto_cv_generation'. Default: OFF.
    """
    try:
        from ..db import db
        with db() as (conn, cur):
            cur.execute("SELECT value FROM app_settings WHERE key = 'auto_cv_generation'")
            row = cur.fetchone()
            if row:
                return row["value"].lower() in ("true", "1", "yes")
    except Exception:
        pass
    return os.getenv("AUTO_CV_GENERATION", "false").lower() in ("true", "1", "yes")


def _run_autonomous_cv_pipeline(job_id: int, job_data: dict, detailed_score: dict) -> Optional[str]:
    """Run the full autonomous CV pipeline for a qualified job.

    Returns the Google Drive URL if successful, None otherwise.
    Steps:
      1. Load resume text
      2. Extract gaps from detailed_score
      3. Generate enhanced CV via Gemini (with gap injection)
      4. Save CV version to DB
      5. Generate premium DOCX
      6. Upload to Google Drive

    Each step has its own error handling so failures are logged but don't crash.
    """
    drive_url = None

    try:
        from ..routes.cv import _call_gemini, _get_resume, _extract_gaps_from_score
        from ..db import db

        # 1. Load resume
        resume_text = _get_resume()

        # 2. Extract gaps
        gaps = _extract_gaps_from_score(detailed_score)

        # 3. Generate enhanced CV
        ai = _call_gemini(
            resume_text=resume_text,
            job_title=job_data.get("job_title", ""),
            company=job_data.get("company_name", ""),
            description=job_data.get("job_description", "")[:4000],
            gaps=gaps,
        )

        enhanced_cv = ai.get("enhanced_cv", "")
        skills_matched = ai.get("skills_matched", [])
        skills_missing = ai.get("skills_missing", [])
        fit_score = ai.get("fit_score")

        if not enhanced_cv:
            logger.warning(f"Pipeline: Gemini returned empty CV for job {job_id}")
            return None

        # 4. Save CV version
        with db() as (conn, cur):
            cur.execute(
                "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_ver FROM cv_versions WHERE job_id = %s",
                [job_id],
            )
            next_ver = cur.fetchone()["next_ver"]

            cur.execute(
                """
                INSERT INTO cv_versions (job_id, version_number, content, enhanced_content,
                                         skills_matched, skills_missing, fit_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                [
                    job_id,
                    next_ver,
                    resume_text,
                    enhanced_cv,
                    json.dumps(skills_matched),
                    json.dumps(skills_missing),
                    fit_score,
                ],
            )
            version_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO audit_log (job_id, action, field, new_value)
                VALUES (%s, 'auto_cv_generated', 'cv_version', %s)
                """,
                [job_id, str(next_ver)],
            )

        logger.info(f"Pipeline: CV version {next_ver} saved for job {job_id}")

        # 5. Generate premium DOCX + upload to Drive
        try:
            from ..services.premium_export import generate_premium_docx

            docx_buffer = generate_premium_docx(
                enhanced_html=enhanced_cv,
                job_title=job_data.get("job_title", ""),
                company=job_data.get("company_name", ""),
                fit_score=fit_score,
                skills_matched=skills_matched,
                skills_missing=skills_missing,
            )

            # 6. Upload to Drive
            try:
                from ..services.drive_service import upload_cv_to_drive

                result = upload_cv_to_drive(
                    job_id=job_id,
                    docx_buffer=docx_buffer,
                    job_title=job_data.get("job_title", ""),
                    company=job_data.get("company_name", ""),
                )
                drive_url = result.get("drive_url") if result else None

                if drive_url:
                    logger.info(f"Pipeline: CV uploaded to Drive for job {job_id}: {drive_url}")
                else:
                    logger.warning(f"Pipeline: Drive upload returned no URL for job {job_id}")
            except Exception as e:
                logger.warning(f"Pipeline: Drive upload failed for job {job_id}: {e}")

        except Exception as e:
            logger.warning(f"Pipeline: DOCX generation failed for job {job_id}: {e}")

    except Exception as e:
        logger.error(f"Pipeline: CV generation failed for job {job_id}: {e}")

    return drive_url


def _run_batch_scoring():
    """Execute batch scoring for all unscored jobs — called by APScheduler.

    When auto_cv_generation is enabled, qualified jobs also get the full
    autonomous pipeline: CV generation → DOCX export → Drive upload → rich notification.
    """
    logger.info("Scheduler: starting batch scoring...")

    try:
        from ..db import db

        batch_size = int(os.getenv("SCHEDULER_BATCH_SIZE", "50"))
        auto_cv = _is_auto_cv_enabled()

        if auto_cv:
            logger.info("Scheduler: autonomous CV pipeline is ENABLED")

        with db() as (conn, cur):
            cur.execute(
                "SELECT id FROM jobs WHERE score IS NULL ORDER BY created_at DESC LIMIT %s",
                [batch_size],
            )
            unscored = [r["id"] for r in cur.fetchall()]

        if not unscored:
            logger.info("Scheduler: no unscored jobs found")
            return

        logger.info(f"Scheduler: found {len(unscored)} unscored jobs, starting batch...")

        # Import scoring and run
        from ..routes.scoring import _score_single_job

        scored = 0
        errors = 0
        high_matches = 0
        total_score = 0
        qualified_jobs = []  # For rich batch notification

        # Determine threshold
        threshold = _DEFAULT_SCORE_THRESHOLD
        try:
            with db() as (conn, cur):
                cur.execute("SELECT value FROM app_settings WHERE key = 'score_threshold'")
                row = cur.fetchone()
                if row:
                    threshold = int(row["value"])
        except Exception:
            pass

        for job_id in unscored:
            try:
                result = _score_single_job(job_id)
                if result and result.get("score"):
                    scored += 1
                    s = result["score"]
                    total_score += s

                    if s >= threshold:
                        high_matches += 1

                        # Load full job data for notifications
                        job_data = {}
                        detailed_score = {}
                        try:
                            with db() as (conn, cur):
                                cur.execute(
                                    """SELECT job_title, company_name, job_description,
                                              location, job_url, apply_url, detailed_score, justification
                                       FROM jobs WHERE id = %s""",
                                    [job_id],
                                )
                                row = cur.fetchone()
                                if row:
                                    job_data = dict(row)
                                    ds = row.get("detailed_score")
                                    if ds:
                                        detailed_score = json.loads(ds) if isinstance(ds, str) else ds
                        except Exception:
                            pass

                        resume_url = None

                        # ── Autonomous CV pipeline (if enabled) ──
                        if auto_cv:
                            try:
                                resume_url = _run_autonomous_cv_pipeline(job_id, job_data, detailed_score)
                            except Exception as e:
                                logger.error(f"Scheduler: auto CV pipeline error for job {job_id}: {e}")

                        # Track for batch summary
                        qualified_jobs.append({
                            "company": job_data.get("company_name", "Unknown"),
                            "title": job_data.get("job_title", "Unknown"),
                            "score": s,
                            "apply_url": job_data.get("apply_url") or job_data.get("job_url", ""),
                            "resume_url": resume_url or "",
                        })

                        # ── Send rich per-job notification ──
                        try:
                            from ..services.alerts import notify_high_match
                            loop = asyncio.new_event_loop()
                            loop.run_until_complete(
                                notify_high_match(
                                    job_title=job_data.get("job_title", "Unknown"),
                                    company=job_data.get("company_name", "Unknown"),
                                    score=s,
                                    job_id=job_id,
                                    justification=job_data.get("justification", ""),
                                    location=job_data.get("location", ""),
                                    job_url=job_data.get("job_url", ""),
                                    apply_url=job_data.get("apply_url", ""),
                                    resume_url=resume_url or "",
                                )
                            )
                            loop.close()
                        except Exception as e:
                            logger.error(f"Scheduler: notification error for job {job_id}: {e}")

            except Exception as e:
                errors += 1
                logger.error(f"Scheduler: error scoring job {job_id}: {e}")

        avg_score = total_score / scored if scored > 0 else 0

        logger.info(
            f"Scheduler: batch complete — scored={scored}, errors={errors}, "
            f"high_matches={high_matches}, avg={avg_score:.1f}"
        )

        # Send batch completion notification (with qualified job details)
        try:
            from ..services.alerts import notify_batch_complete
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                notify_batch_complete(
                    total=len(unscored),
                    scored=scored,
                    errors=errors,
                    high_matches=high_matches,
                    avg_score=avg_score,
                    qualified_jobs=qualified_jobs if qualified_jobs else None,
                )
            )
            loop.close()
        except Exception as e:
            logger.error(f"Scheduler: notification error: {e}")

    except Exception as e:
        logger.error(f"Scheduler: batch scoring failed: {e}")

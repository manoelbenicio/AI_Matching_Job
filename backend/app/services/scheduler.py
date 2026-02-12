"""
Scheduler Service — APScheduler-based cron for batch scoring.

Reads config from app_settings (key: scheduler_*) with env fallbacks.
Starts a BackgroundScheduler in the FastAPI lifespan.
"""

import os
import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger("scheduler")

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


def _run_batch_scoring():
    """Execute batch scoring for all unscored jobs — called by APScheduler."""
    logger.info("Scheduler: starting batch scoring...")

    try:
        from ..db import db

        batch_size = int(os.getenv("SCHEDULER_BATCH_SIZE", "50"))

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

        for job_id in unscored:
            try:
                result = _score_single_job(job_id)
                if result and result.get("score"):
                    scored += 1
                    s = result["score"]
                    total_score += s
                    if s >= 70:
                        high_matches += 1
            except Exception as e:
                errors += 1
                logger.error(f"Scheduler: error scoring job {job_id}: {e}")

        avg_score = total_score / scored if scored > 0 else 0

        logger.info(
            f"Scheduler: batch complete — scored={scored}, errors={errors}, "
            f"high_matches={high_matches}, avg={avg_score:.1f}"
        )

        # Send completion notification
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
                )
            )
            loop.close()
        except Exception as e:
            logger.error(f"Scheduler: notification error: {e}")

    except Exception as e:
        logger.error(f"Scheduler: batch scoring failed: {e}")

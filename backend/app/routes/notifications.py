"""Notifications routes — Telegram + Email alert management."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..db import db

router = APIRouter()


class NotificationSettingsUpdate(BaseModel):
    telegram_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    score_threshold: Optional[int] = None


@router.get("/notifications/settings")
def get_notification_settings():
    """Get current notification preferences."""
    defaults = {
        "telegram_enabled": True,
        "email_enabled": False,
        "score_threshold": 70,
    }
    with db() as (conn, cur):
        cur.execute(
            "SELECT key, value FROM app_settings WHERE key IN ('telegram_enabled', 'email_enabled', 'score_threshold')"
        )
        for row in cur.fetchall():
            k = row["key"]
            v = row["value"]
            if k in ("telegram_enabled", "email_enabled"):
                defaults[k] = v.lower() in ("true", "1", "yes")
            elif k == "score_threshold":
                defaults[k] = int(v)
    return defaults


@router.put("/notifications/settings")
def save_notification_settings(body: NotificationSettingsUpdate):
    """Save notification preferences to app_settings."""
    updates = {}
    if body.telegram_enabled is not None:
        updates["telegram_enabled"] = str(body.telegram_enabled).lower()
    if body.email_enabled is not None:
        updates["email_enabled"] = str(body.email_enabled).lower()
    if body.score_threshold is not None:
        updates["score_threshold"] = str(body.score_threshold)

    with db() as (conn, cur):
        for key, value in updates.items():
            cur.execute(
                """INSERT INTO app_settings (key, value)
                   VALUES (%s, %s)
                   ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
                [key, value],
            )
    return {"message": f"Updated: {', '.join(updates.keys())}"}


@router.post("/notifications/test-telegram")
async def test_telegram():
    """Send a test message via Telegram."""
    from ..services.alerts import send_telegram

    result = await send_telegram(
        "🧪 <b>Test notification</b>\n\nYour AI Job Matcher alerts are working! 🎉"
    )
    return result


@router.post("/notifications/test-email")
def test_email():
    """Send a test email."""
    from ..services.alerts import send_email

    result = send_email(
        subject="🧪 AI Job Matcher — Test Notification",
        body="<h2>Test Notification</h2><p>Your AI Job Matcher email alerts are working! 🎉</p>",
    )
    return result

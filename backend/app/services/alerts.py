"""
Alerts Service — Telegram + Email notifications.

Uses Telegram Bot API (via httpx) and Python stdlib smtplib for email.
All credentials come from the .env / app_settings DB table.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict
import httpx

_DEFAULT_SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD_DEFAULT", "80"))


def _get_setting(key: str) -> Optional[str]:
    """Get a setting from app_settings table, with env fallback."""
    try:
        from ..db import db
        with db() as (conn, cur):
            cur.execute("SELECT value FROM app_settings WHERE key = %s", [key])
            row = cur.fetchone()
            if row and row["value"]:
                return row["value"]
    except Exception:
        pass
    return os.getenv(key)


async def send_telegram(message: str) -> dict:
    """Send a message via Telegram Bot API.

    Returns { ok: True, message: 'sent' } on success.
    """
    token = _get_setting("TELEGRAM_BOT_TOKEN")
    chat_id = _get_setting("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        return {"ok": False, "message": "Telegram not configured (missing bot token or chat ID)"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload)
        data = resp.json()
        if data.get("ok"):
            return {"ok": True, "message": "Telegram message sent successfully"}
        return {"ok": False, "message": f"Telegram API error: {data.get('description', 'unknown')}"}


def send_email(
    subject: str,
    body: str,
    to_email: Optional[str] = None,
) -> dict:
    """Send an email via SMTP (Gmail / generic).

    Returns { ok: True, message: 'sent' } on success.
    """
    smtp_host = _get_setting("SMTP_HOST") or "smtp.gmail.com"
    smtp_port = int(_get_setting("SMTP_PORT") or "587")
    smtp_user = _get_setting("SMTP_USER")
    smtp_pass = _get_setting("SMTP_PASSWORD")
    from_addr = _get_setting("SMTP_FROM") or smtp_user
    to_addr = to_email or _get_setting("ALERT_EMAIL_TO")

    if not smtp_user or not smtp_pass or not to_addr:
        return {"ok": False, "message": "Email not configured (missing SMTP credentials or recipient)"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return {"ok": True, "message": f"Email sent to {to_addr}"}
    except Exception as e:
        return {"ok": False, "message": f"Email send failed: {str(e)}"}


async def notify_high_match(
    job_title: str,
    company: str,
    score: int,
    job_id: int,
    # Rich notification fields (backward-compatible):
    justification: str = "",
    location: str = "",
    job_url: str = "",
    apply_url: str = "",
    resume_url: str = "",
) -> None:
    """Send high-match notification via all enabled channels.

    Supports rich formatting with APPLY NOW link, CV download link,
    location, and justification snippet (backported from legacy pattern).
    """
    from ..db import db

    # Check if notifications are enabled
    telegram_enabled = True  # default on
    email_enabled = False
    threshold = _DEFAULT_SCORE_THRESHOLD

    try:
        with db() as (conn, cur):
            cur.execute("SELECT key, value FROM app_settings WHERE key IN ('telegram_enabled', 'email_enabled', 'score_threshold')")
            for row in cur.fetchall():
                if row["key"] == "telegram_enabled":
                    telegram_enabled = row["value"].lower() in ("true", "1", "yes")
                elif row["key"] == "email_enabled":
                    email_enabled = row["value"].lower() in ("true", "1", "yes")
                elif row["key"] == "score_threshold":
                    threshold = int(row["value"])
    except Exception:
        pass

    if score < threshold:
        return

    # ── Build rich message (legacy-inspired) ──
    message = (
        f"🎉 <b>New Qualified Match!</b>\n\n"
        f"🏢 <b>{company}</b>\n"
        f"💼 {job_title}\n"
    )
    if location:
        message += f"📍 {location}\n"
    message += f"📊 Score: <b>{score}%</b>\n"

    if justification:
        snippet = justification[:200]
        message += f"\n📝 <i>{snippet}</i>\n"

    message += f"\n{'='*30}\n📱 <b>QUICK ACTIONS</b>\n{'='*30}\n\n"

    if apply_url:
        message += f"🚀 <a href='{apply_url}'><b>APPLY NOW</b></a>\n\n"
    elif job_url:
        message += f"🚀 <a href='{job_url}'><b>VIEW & APPLY</b></a>\n\n"

    if resume_url:
        message += f"📄 <a href='{resume_url}'><b>Your Enhanced CV</b></a>\n\n"

    if job_url and job_url != apply_url:
        message += f"🔗 <a href='{job_url}'>View Job Details</a>"

    message += f"\n\n🆔 Job ID: {job_id}"

    if telegram_enabled:
        await send_telegram(message)

    if email_enabled:
        # Rich HTML email
        email_body = f"""
        <h2>🎉 New Qualified Match!</h2>
        <p><b>{job_title}</b> at <b>{company}</b></p>
        {'<p>📍 ' + location + '</p>' if location else ''}
        <p>Score: <b>{score}/100</b></p>
        {'<blockquote>' + justification[:300] + '</blockquote>' if justification else ''}
        <hr>
        {'<p><a href="' + apply_url + '">🚀 APPLY NOW</a></p>' if apply_url else ''}
        {'<p><a href="' + resume_url + '">📄 Your Enhanced CV</a></p>' if resume_url else ''}
        {'<p><a href="' + job_url + '">🔗 View Job Details</a></p>' if job_url else ''}
        """
        send_email(
            subject=f"🎉 Qualified Match: {job_title} at {company} ({score}%)",
            body=email_body,
        )


async def notify_batch_complete(
    total: int,
    scored: int,
    errors: int,
    high_matches: int,
    avg_score: float,
    qualified_jobs: Optional[List[Dict]] = None,
) -> None:
    """Send batch completion summary via all enabled channels.

    If `qualified_jobs` is provided, each entry is included with its details
    (company, title, score, apply link) — matching legacy's send_batch_summary.
    """
    telegram_enabled = True
    try:
        from ..db import db
        with db() as (conn, cur):
            cur.execute("SELECT value FROM app_settings WHERE key = 'telegram_enabled'")
            row = cur.fetchone()
            if row:
                telegram_enabled = row["value"].lower() in ("true", "1", "yes")
    except Exception:
        pass

    message = (
        f"📊 <b>Batch Scoring Complete</b>\n\n"
        f"📋 Total: {total}\n"
        f"✅ Scored: {scored}\n"
        f"❌ Errors: {errors}\n"
        f"🎯 High matches: {high_matches}\n"
        f"📈 Average score: {avg_score:.1f}"
    )

    # Append qualified job details if available
    if qualified_jobs:
        message += f"\n\n{'='*30}\n🏆 <b>QUALIFIED JOBS</b>\n{'='*30}\n"
        for qj in qualified_jobs[:10]:  # Cap at 10 to avoid message length limits
            message += (
                f"\n• <b>{qj.get('company', '—')}</b> — {qj.get('title', '—')}\n"
                f"  Score: {qj.get('score', '?')}%"
            )
            if qj.get("apply_url"):
                message += f" | <a href='{qj['apply_url']}'>Apply</a>"
            if qj.get("resume_url"):
                message += f" | <a href='{qj['resume_url']}'>CV</a>"
            message += "\n"

    if telegram_enabled:
        await send_telegram(message)

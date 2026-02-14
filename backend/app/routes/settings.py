"""Application settings routes — manage API keys and configuration."""

import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..db import db

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_setting(key: str) -> Optional[str]:
    """Read a setting from DB, fallback to os.environ."""
    try:
        with db() as (conn, cur):
            cur.execute("SELECT value FROM app_settings WHERE key = %s", (key,))
            row = cur.fetchone()
            if row:
                return row["value"]
    except Exception:
        pass  # Table might not exist yet
    return os.environ.get(key)


def _set_setting(key: str, value: str):
    """Upsert a setting in the DB."""
    with db() as (conn, cur):
        cur.execute(
            """INSERT INTO app_settings (key, value)
               VALUES (%s, %s)
               ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
            (key, value),
        )


def get_api_key(key_name: str) -> Optional[str]:
    """Public helper — used by scoring.py and cv.py to resolve an API key.
    Checks DB first, then falls back to environment variable.
    """
    return _get_setting(key_name)


def get_groq_api_keys() -> list[str]:
    """Return configured Groq API keys from one comma-separated setting."""
    raw = _get_setting("GROQ_API_KEYS")
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k and k.strip()]


# ── Models ─────────────────────────────────────────────────────────────────

class ApiKeysBody(BaseModel):
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_keys: Optional[str] = None


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings():
    """Return which API keys are configured (without revealing the values)."""
    openai = _get_setting("OPENAI_API_KEY")
    gemini = _get_setting("GEMINI_API_KEY")
    groq_keys = get_groq_api_keys()
    return {
        "openai_key_set": bool(openai and len(openai) > 8),
        "gemini_key_set": bool(gemini and len(gemini) > 8),
        "openai_key_preview": f"{openai[:4]}...{openai[-4:]}" if openai and len(openai) > 12 else "",
        "gemini_key_preview": f"{gemini[:4]}...{gemini[-4:]}" if gemini and len(gemini) > 12 else "",
        "groq_keys_count": len(groq_keys),
        "groq_keys_preview": [
            f"{key[:4]}...{key[-4:]}" if len(key) > 8 else key
            for key in groq_keys
        ],
    }


@router.put("/settings/api-keys")
async def save_api_keys(body: ApiKeysBody):
    """Save API keys to the database."""
    saved = []
    if body.openai_api_key is not None and body.openai_api_key.strip():
        _set_setting("OPENAI_API_KEY", body.openai_api_key.strip())
        saved.append("OPENAI_API_KEY")
    if body.gemini_api_key is not None and body.gemini_api_key.strip():
        _set_setting("GEMINI_API_KEY", body.gemini_api_key.strip())
        saved.append("GEMINI_API_KEY")
    if body.groq_api_keys is not None and body.groq_api_keys.strip():
        _set_setting("GROQ_API_KEYS", body.groq_api_keys.strip())
        saved.append("GROQ_API_KEYS")
    if not saved:
        raise HTTPException(status_code=400, detail="No keys provided")
    return {"saved": saved, "message": f"Saved {len(saved)} key(s) successfully"}


@router.post("/settings/test-openai")
async def test_openai():
    """Test the OpenAI API key with a minimal request."""
    key = _get_setting("OPENAI_API_KEY")
    if not key:
        raise HTTPException(status_code=400, detail="OpenAI API key not configured")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
        if resp.status_code == 200:
            return {"ok": True, "message": "OpenAI connection successful"}
        elif resp.status_code == 401:
            return {"ok": False, "message": "Invalid API key"}
        else:
            return {"ok": False, "message": f"OpenAI returned status {resp.status_code}"}
    except Exception as e:
        return {"ok": False, "message": f"Connection error: {str(e)}"}


@router.post("/settings/test-gemini")
async def test_gemini():
    """Test the Gemini API key with a minimal request."""
    key = _get_setting("GEMINI_API_KEY")
    if not key:
        raise HTTPException(status_code=400, detail="Gemini API key not configured")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
            )
        if resp.status_code == 200:
            return {"ok": True, "message": "Gemini connection successful"}
        elif resp.status_code in (400, 403):
            return {"ok": False, "message": "Invalid API key"}
        else:
            return {"ok": False, "message": f"Gemini returned status {resp.status_code}"}
    except Exception as e:
        return {"ok": False, "message": f"Connection error: {str(e)}"}


@router.post("/settings/test-groq")
async def test_groq():
    """Validate all configured Groq keys against /models endpoint."""
    keys = get_groq_api_keys()
    if not keys:
        raise HTTPException(status_code=400, detail="Groq API keys not configured")

    details = []
    valid = 0
    async with httpx.AsyncClient(timeout=15) as client:
        for idx, key in enumerate(keys, start=1):
            preview = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else key
            try:
                resp = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                if resp.status_code == 200:
                    valid += 1
                    details.append(
                        {"index": idx, "key_preview": preview, "ok": True, "status_code": 200, "message": "valid"}
                    )
                elif resp.status_code in (401, 403):
                    details.append(
                        {"index": idx, "key_preview": preview, "ok": False, "status_code": resp.status_code, "message": "invalid"}
                    )
                else:
                    details.append(
                        {
                            "index": idx,
                            "key_preview": preview,
                            "ok": False,
                            "status_code": resp.status_code,
                            "message": f"status {resp.status_code}",
                        }
                    )
            except Exception as e:
                details.append(
                    {
                        "index": idx,
                        "key_preview": preview,
                        "ok": False,
                        "status_code": None,
                        "message": f"connection error: {str(e)}",
                    }
                )

    total = len(keys)
    return {
        "ok": valid == total,
        "message": f"{valid}/{total} keys valid",
        "details": details,
    }

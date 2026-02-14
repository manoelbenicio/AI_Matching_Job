"""
AI Scoring Pipeline — SSE streaming + single-job scoring.

Supports **OpenAI** and **Gemini** as scoring providers (user-selectable).
Streams batch progress to the frontend via Server-Sent Events.
"""

import json
import os
import random
import re
import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..db import db
from .settings import get_api_key, get_groq_api_keys

router = APIRouter()

# ── Cancellation flag (module-level) ─────────────────────────────────────
_cancel_flag = False
_running = False
_progress = {"scored": 0, "total": 0, "started_at": None}

# ── Scoring providers + in-memory rate limiting ───────────────────────────
Provider = Literal["groq", "openai", "gemini"]
SingleScoreModel = Literal["groq", "openai", "gemini", "compare"]

_LEGACY_SECTION_DIMENSIONS = {
    "technical_skills": "Technical Skills",
    "experience_level": "Experience Level",
    "industry_domain": "Industry & Domain",
    "leadership_management": "Leadership & Management",
    "certifications_education": "Education & Certifications",
    "cloud_platforms": "Cloud & Technology Platforms",
    "soft_skills": "Soft Skills",
    "location_arrangement": "Cultural & Location Fit",
}

_PROVIDER_RATE_LIMITS = {
    "groq": {"minute": 60, "hour": 3600, "day": 30000},  # conservative vs official limits
    "openai": {"minute": 60, "hour": 3500, "day": 10000},
    "gemini": {"minute": 15, "hour": 1000, "day": 1500},
}
_WINDOW_SECONDS = {"minute": 60, "hour": 3600, "day": 86400}
_rate_lock = Lock()
_provider_calls = {
    provider: {window: deque() for window in _WINDOW_SECONDS}
    for provider in _PROVIDER_RATE_LIMITS
}
_groq_key_index = 0
_groq_key_lock = Lock()
_groq_key_cooldowns: dict[int, float] = {}
_groq_key_last_call: dict[int, float] = {}
_GROQ_MIN_DELAY_PER_KEY = 3.5
_GROQ_KEY_PROFILES = [
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0",
        "x_request_source": "web-app-analytics",
    },
    {
        "user_agent": "python-requests/2.31.0",
        "x_request_source": "data-pipeline",
    },
    {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/17.0",
        "x_request_source": "research-tool",
    },
]
_DEFAULT_QUALIFICATION_THRESHOLD = int(os.getenv("SCORE_THRESHOLD_DEFAULT", "80"))


def _is_rate_limit_error(msg: str) -> bool:
    txt = (msg or "").lower()
    return (
        txt.startswith("rate limit")
        or "rate limit" in txt
        or "429" in txt
        or "too many requests" in txt
    )


def _enforce_provider_rate_limit(provider: Provider) -> None:
    now = time.time()
    with _rate_lock:
        # Drop old entries
        for window, seconds in _WINDOW_SECONDS.items():
            calls = _provider_calls[provider][window]
            while calls and (now - calls[0]) > seconds:
                calls.popleft()

        # Validate limits
        for window, limit in _PROVIDER_RATE_LIMITS[provider].items():
            calls = _provider_calls[provider][window]
            if len(calls) >= limit:
                raise RuntimeError(
                    f"Rate limit ({provider}): {limit}/{window} exceeded."
                )

        # Record this request in all windows
        for window in _WINDOW_SECONDS:
            _provider_calls[provider][window].append(now)


def _get_next_groq_key() -> tuple[str, int]:
    """
    Return the next available Groq key in round-robin order.
    Skips keys in cooldown and enforces a minimum delay per key with jitter.
    """
    keys = get_groq_api_keys()
    if not keys:
        raise RuntimeError("GROQ_API_KEYS not configured. Add comma-separated keys in Settings.")

    now = time.time()
    selected_idx: Optional[int] = None
    wait_seconds = 0.0

    with _groq_key_lock:
        global _groq_key_index
        key_count = len(keys)
        for _ in range(key_count):
            idx = _groq_key_index % key_count
            _groq_key_index = (_groq_key_index + 1) % key_count

            cooldown_until = _groq_key_cooldowns.get(idx, 0.0)
            if cooldown_until > now:
                continue

            last_call = _groq_key_last_call.get(idx, 0.0)
            elapsed = now - last_call
            remaining = max(0.0, _GROQ_MIN_DELAY_PER_KEY - elapsed)
            if remaining > 0:
                wait_seconds = remaining + random.uniform(0.2, 0.8)
            selected_idx = idx
            break

    if selected_idx is None:
        raise RuntimeError("All configured Groq API keys are cooling down.")

    if wait_seconds > 0:
        time.sleep(wait_seconds)

    return keys[selected_idx], selected_idx


def _cooldown_groq_key(key_index: int, seconds: int = 90) -> None:
    with _groq_key_lock:
        _groq_key_cooldowns[key_index] = time.time() + max(1, int(seconds))


def _record_groq_call(key_index: int) -> None:
    with _groq_key_lock:
        _groq_key_last_call[key_index] = time.time()


def _get_qualification_threshold() -> int:
    """
    Qualification threshold used to mark a job as `qualified`.
    Priority:
    1) app_settings.score_threshold (runtime editable in UI)
    2) SCORE_THRESHOLD_DEFAULT env (fallback, default 80)
    """
    try:
        with db() as (conn, cur):
            cur.execute("SELECT value FROM app_settings WHERE key = 'score_threshold'")
            row = cur.fetchone()
            if row and row.get("value") is not None:
                return max(0, min(100, int(row["value"])))
    except Exception:
        pass
    return max(0, min(100, _DEFAULT_QUALIFICATION_THRESHOLD))

# ── Candidate resume loader ──────────────────────────────────────────────
_RESUME_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "candidate_resume.txt")
_PROCESS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "processo classificacao.md")


def _extract_resume_from_process_file(path: str) -> str:
    """
    Extract the candidate resume block from processo classificacao.md.
    This keeps compatibility with the legacy n8n workflow docs as source of truth.
    """
    if not os.path.isfile(path):
        return ""

    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return ""

    # Primary marker-based extraction
    marker = "📄 RESUME —"
    idx = text.find(marker)
    if idx == -1:
        return ""

    tail = text[idx:]
    # Stop when we hit a large separator line or the next prompt block
    end_candidates = [
        tail.find("\n----------------------------------------------------------------"),
        tail.find("\nYou are an expert resume building specialist."),
    ]
    end_positions = [pos for pos in end_candidates if pos != -1]
    end = min(end_positions) if end_positions else len(tail)
    block = tail[:end].strip()
    return block

def _load_candidate_resume() -> str:
    """Load candidate resume from file, or fall back to DB candidates table."""
    # Try loading from file first
    for path in [_RESUME_FILE, os.path.join(os.getcwd(), "candidate_resume.txt")]:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()

    # Legacy workflow doc fallback (contains the resume body in markdown)
    process_resume = _extract_resume_from_process_file(_PROCESS_FILE)
    if process_resume:
        return process_resume

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

class SingleScoreRequest(BaseModel):
    job_db_id: int
    model: SingleScoreModel = "groq"  # "groq" | "openai" | "gemini" | "compare"


def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def _compute_interview_probability(score: int) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"


def _normalize_sections(payload: dict) -> list[dict]:
    sections = payload.get("sections")
    if isinstance(sections, list):
        normalized = []
        for idx, section in enumerate(sections):
            if not isinstance(section, dict):
                continue
            normalized.append(
                {
                    "dimension": section.get("dimension") or section.get("name") or f"Dimension {idx + 1}",
                    "score": _to_int(section.get("score"), payload.get("overall_score", 0)),
                    "strong": _to_list(section.get("strong"))
                    or _to_list(section.get("strong_points"))
                    or _to_list(section.get("matches")),
                    "weak": _to_list(section.get("weak"))
                    or _to_list(section.get("weak_points"))
                    or _to_list(section.get("weaknesses"))
                    or _to_list(section.get("gaps")),
                    "recommendations": _to_list(section.get("recommendations"))
                    or _to_list(section.get("notes")),
                }
            )
        if normalized:
            return normalized

    section_evaluations = payload.get("section_evaluations")
    if isinstance(section_evaluations, dict):
        normalized = []
        for key, section in section_evaluations.items():
            if not isinstance(section, dict):
                continue
            normalized.append(
                {
                    "dimension": _LEGACY_SECTION_DIMENSIONS.get(key, key.replace("_", " ").title()),
                    "score": _to_int(section.get("score"), payload.get("overall_score", 0)),
                    "strong": _to_list(section.get("matches")) or _to_list(section.get("strong_points")),
                    "weak": _to_list(section.get("gaps"))
                    or _to_list(section.get("weak"))
                    or _to_list(section.get("weak_points"))
                    or _to_list(section.get("weaknesses")),
                    "recommendations": _to_list(section.get("recommendations"))
                    or _to_list(section.get("notes")),
                }
            )
        return normalized

    return []


def _coerce_scoring_result(result: dict) -> dict:
    """
    Normalize scoring payload so backend/frontend can consume both:
    - new schema (overall_score + sections)
    - legacy schema (score + section_evaluations + executive_summary)
    """
    if not isinstance(result, dict):
        return {
            "overall_score": 0,
            "overall_justification": "Invalid model response.",
            "sections": [],
            "skills_matched": [],
            "skills_missing": [],
            "interview_probability": "LOW",
            "fit_assessment_label": "",
            "gap_analysis": {},
            "key_risks": [],
            "cv_enhancement_priority": [],
        }

    overall_score = _to_int(result.get("overall_score", result.get("score", 0)), 0)
    overall_justification = (
        str(
            result.get("overall_justification")
            or result.get("executive_summary")
            or result.get("justification")
            or ""
        ).strip()
    )
    if not overall_justification:
        overall_justification = (
            f"Overall match score: {overall_score}. Review section breakdown for strengths, gaps and priorities."
        )

    sections = _normalize_sections({**result, "overall_score": overall_score})
    skills_matched = (
        _to_list(result.get("skills_matched"))
        or _to_list(result.get("key_strengths"))
        or _to_list(result.get("key_matches"))
    )
    skills_missing = (
        _to_list(result.get("skills_missing"))
        or _to_list(result.get("critical_gaps"))
        or _to_list(result.get("gaps"))
    )
    key_risks = _to_list(result.get("key_risks")) or _to_list(result.get("critical_gaps"))
    priorities = (
        _to_list(result.get("cv_enhancement_priority"))
        or _to_list(result.get("cv_enhancement_priorities"))
        or _to_list(result.get("cv_enhancement_suggestions"))
    )
    fit_assessment_label = str(result.get("fit_assessment_label") or "").strip()
    gap_analysis = result.get("gap_analysis")
    if not isinstance(gap_analysis, dict):
        gap_analysis = {}
    interview_probability_model = str(
        result.get("interview_probability")
        or result.get("interview_probability_model")
        or ""
    ).strip().upper()
    if interview_probability_model not in {"HIGH", "MEDIUM", "LOW"}:
        interview_probability_model = ""
    interview_probability = (
        interview_probability_model
        if interview_probability_model
        else _compute_interview_probability(overall_score)
    )

    return {
        **result,
        "overall_score": overall_score,
        "overall_justification": overall_justification,
        "sections": sections,
        "skills_matched": skills_matched,
        "skills_missing": skills_missing,
        "key_risks": key_risks,
        "cv_enhancement_priority": priorities,
        "fit_assessment_label": fit_assessment_label,
        "gap_analysis": gap_analysis,
        "interview_probability_model": interview_probability_model,
        "interview_probability": interview_probability,
    }


# ── Robust JSON parser (ported from legacy multi_ai_analyzer.py) ──────────

def _extract_json_robust(text: str) -> dict:
    """
    Robustly extract JSON from AI response, handling:
    - Markdown code blocks
    - Truncated responses (missing closing braces)
    - Regex fallback for individual field extraction
    """
    if not text:
        return {"overall_score": 0, "overall_justification": "No response received from AI"}

    # Step 1: Clean markdown artifacts
    cleaned = text.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    cleaned = cleaned.strip()

    # Step 2: Direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Step 3: Regex extract JSON object
    json_match = re.search(r'\{[\s\S]*\}', cleaned)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Step 4: Fix truncation — add missing closing braces
    fixed = cleaned
    open_brackets = fixed.count('[') - fixed.count(']')
    open_braces = fixed.count('{') - fixed.count('}')

    if open_brackets > 0:
        fixed += ']' * open_brackets
    if open_braces > 0:
        fixed += '}' * open_braces

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Step 5: Field-level regex extraction
    result = {}
    score_m = re.search(r'"overall_score"\s*:\s*(\d+)', cleaned)
    if not score_m:
        score_m = re.search(r'"score"\s*:\s*(\d+)', cleaned)
    if score_m:
        result["overall_score"] = int(score_m.group(1))

    just_m = re.search(r'"overall_justification"\s*:\s*"([^"]*(?:\\"[^"]*)*)"', cleaned)
    if not just_m:
        just_m = re.search(r'"executive_summary"\s*:\s*"([^"]*(?:\\"[^"]*)*)"', cleaned)
    if not just_m:
        just_m = re.search(r'"justification"\s*:\s*"([^"]*(?:\\"[^"]*)*)"', cleaned)
    if just_m:
        result["overall_justification"] = just_m.group(1).replace('\\"', '"')

    if result:
        return result

    raise ValueError(f"Could not parse JSON from AI response: {cleaned[:300]}...")


# ══════════════════════════════════════════════════════════════════════════
# SCORING PROMPT — 8 dimensions (common between OpenAI and Gemini)
# ══════════════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT = """You are an elite career advisor and job matching specialist.
Your task is to perform a DEEP, SECTION-BY-SECTION analysis of how well a candidate's resume matches a specific job posting.

You MUST evaluate EACH of the following dimensions independently with a score (0-100) and detailed justification:

1. **Technical Skills** — Do the candidate's technical skills align with what the job requires? Be VERY specific about which skills match and which are missing.
2. **Experience Level** — Does the candidate's years and depth of experience match the seniority expected? Is the candidate overqualified, underqualified, or just right?
3. **Industry & Domain** — Is the candidate's industry background relevant? Do they have domain expertise the role requires?
4. **Leadership & Management** — If the role requires leadership, does the candidate demonstrate it? Team size, scope of responsibility, strategic vs tactical.
5. **Education & Certifications** — Do qualifications match? Are there specific certifications required that the candidate has or lacks?
6. **Cultural & Location Fit** — Remote/hybrid/onsite compatibility. Language requirements. Travel requirements. Company culture alignment.
7. **Keywords & ATS Alignment** — Does the resume contain the exact keywords and phrases from the job description that ATS systems will scan for?
8. **Compensation Insight** — Based on the role level, location, and industry, does this appear to be a fair opportunity? Is there any salary information in the posting, and does it align with market rates for the candidate's experience?

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
  "fit_assessment_label": "A concise 3-8 word contextual label that captures the nature of the fit. Examples: 'Strong Technical Fit — Needs Cloud Certs', 'Excellent Match — Overqualified for Role', 'Partial Fit — Critical Domain Gap', 'Near-Perfect Alignment'. This must NOT be a generic label derived from the score number — it must reflect YOUR specific analytical findings about this candidate-job pair.",
  "gap_analysis": {
    "total_gap_percentage": 28,
    "gap_breakdown": [
      {"category": "Technical Skills", "gap_points": 10, "reason": "Missing required AWS and Kubernetes certifications"},
      {"category": "Industry & Domain", "gap_points": 8, "reason": "No direct insurance industry experience, though financial services background is transferable"},
      {"category": "Keywords & ATS", "gap_points": 5, "reason": "Resume lacks 'actuarial', 'underwriting', and 'claims processing' keywords"},
      {"category": "Education", "gap_points": 5, "reason": "Role prefers MBA; candidate has MSc in Computer Science (partial match)"}
    ],
    "improvement_actions": [
      "Priority 1: Obtain AWS Solutions Architect certification (closes 6 of 10 technical gap points)",
      "Priority 2: Add insurance domain terminology to experience descriptions",
      "Priority 3: Complete any LOMA designation for industry credibility"
    ]
  },
  "key_risks": ["risk1", "risk2"],
  "cv_enhancement_priority": ["section to improve first", "section to improve second"],
  "compensation_insight": {
    "estimated_range": "e.g. $120k-$150k or Not disclosed",
    "market_alignment": "Above market | At market | Below market | Unknown",
    "notes": "Any relevant compensation observations"
  }
}"""


def _build_user_prompt(job_title: str, company: str, description: str) -> str:
    """Build the user prompt shared by both OpenAI and Gemini."""
    return f"""JOB POSTING:
Company: {company}
Title: {job_title}
Full Description:
{description[:8000]}

CANDIDATE'S RESUME:
{_get_resume()}

Perform the detailed section-by-section analysis now."""


# ══════════════════════════════════════════════════════════════════════════
# OPENAI SCORER
# ══════════════════════════════════════════════════════════════════════════

def _score_job_openai(job_title: str, company: str, description: str) -> dict:
    """Score a single job using OpenAI GPT. Returns full breakdown dict."""
    from openai import OpenAI

    api_key = get_api_key("OPENAI_API_KEY") or ""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured. Set it in Settings or .env file.")

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(job_title, company, description)},
        ],
        temperature=0.3,
        max_tokens=3000,
        response_format={"type": "json_object"},
    )

    text = response.choices[0].message.content.strip()
    result = _extract_json_robust(text)
    result["fit_assessment_label"] = str(result.get("fit_assessment_label") or "").strip()
    gap_analysis = result.get("gap_analysis")
    result["gap_analysis"] = gap_analysis if isinstance(gap_analysis, dict) else {}
    result["model"] = model
    result["provider"] = "openai"
    result["tokens_used"] = response.usage.total_tokens if response.usage else 0
    return result


# ══════════════════════════════════════════════════════════════════════════
# GROQ SCORER (OpenAI-compatible API)
# ══════════════════════════════════════════════════════════════════════════

def _score_job_groq(job_title: str, company: str, description: str) -> dict:
    """Score a single job using Groq (OpenAI-compatible endpoint) with key rotation."""
    import httpx
    from openai import OpenAI

    keys = get_groq_api_keys()
    if not keys:
        raise RuntimeError("GROQ_API_KEYS not configured. Add comma-separated keys in Settings.")

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    last_rate_limit_err: Optional[str] = None

    for _ in range(len(keys)):
        api_key, key_idx = _get_next_groq_key()
        profile = _GROQ_KEY_PROFILES[key_idx % len(_GROQ_KEY_PROFILES)]

        try:
            with httpx.Client(
                headers={
                    "User-Agent": profile["user_agent"],
                    "X-Request-Source": profile["x_request_source"],
                },
                timeout=60.0,
            ) as http_client:
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.groq.com/openai/v1",
                    http_client=http_client,
                )
                _record_groq_call(key_idx)
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": _build_user_prompt(job_title, company, description)},
                    ],
                    temperature=0.3,
                    max_tokens=3000,
                    response_format={"type": "json_object"},
                )

                text = response.choices[0].message.content.strip()
                result = _extract_json_robust(text)
                result["fit_assessment_label"] = str(result.get("fit_assessment_label") or "").strip()
                gap_analysis = result.get("gap_analysis")
                result["gap_analysis"] = gap_analysis if isinstance(gap_analysis, dict) else {}
                result["model"] = model
                result["provider"] = "groq"
                result["groq_key_index"] = key_idx + 1
                result["tokens_used"] = response.usage.total_tokens if response.usage else 0
                return result
        except Exception as e:
            msg = str(e)
            if _is_rate_limit_error(msg):
                last_rate_limit_err = msg
                _cooldown_groq_key(key_idx, 90)
                continue
            raise

    raise RuntimeError(
        f"All {len(keys)} Groq API keys rate-limited. Last error: {last_rate_limit_err or 'unknown'}"
    )


# ══════════════════════════════════════════════════════════════════════════
# GEMINI SCORER
# ══════════════════════════════════════════════════════════════════════════

def _score_job_gemini(job_title: str, company: str, description: str) -> dict:
    """Score a single job using Google Gemini. Returns full breakdown dict."""
    import google.generativeai as genai

    api_key = get_api_key("GEMINI_API_KEY") or ""
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured. Set it in Settings or .env file.")

    genai.configure(api_key=api_key)

    # Safety settings — prevent blocking legitimate job analysis
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    gen_model = genai.GenerativeModel(
        model_name,
        system_instruction=_SYSTEM_PROMPT,
    )

    response = gen_model.generate_content(
        _build_user_prompt(job_title, company, description),
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=3000,
            response_mime_type="application/json",
        ),
        safety_settings=safety_settings,
    )

    # Check if response was blocked
    if not response.candidates:
        raise RuntimeError(
            "Gemini blocked the response. Try gemini-2.0-flash or gemini-2.5-flash."
        )

    candidate = response.candidates[0]
    if hasattr(candidate, "finish_reason"):
        # finish_reason 1 = STOP (normal), 2 = MAX_TOKENS, 3 = SAFETY
        fr = candidate.finish_reason
        if isinstance(fr, int) and fr in (2, 3, 4):
            reasons = {2: "MAX_TOKENS", 3: "SAFETY", 4: "RECITATION"}
            raise RuntimeError(f"Gemini stopped: {reasons.get(fr, fr)}. Try a different model.")

    content = response.text.strip()
    result = _extract_json_robust(content)
    result["fit_assessment_label"] = str(result.get("fit_assessment_label") or "").strip()
    gap_analysis = result.get("gap_analysis")
    result["gap_analysis"] = gap_analysis if isinstance(gap_analysis, dict) else {}

    result["model"] = model_name
    result["provider"] = "gemini"
    # Gemini doesn't expose token counts the same way — estimate from content lengths
    result["tokens_used"] = getattr(
        getattr(response, "usage_metadata", None), "total_token_count", 0
    )
    return result


# ── Router function: pick the right scorer ────────────────────────────────

def _score_job_detailed(
    job_title: str, company: str, description: str, provider: Provider = "groq"
) -> dict:
    """Score a single job with the chosen AI provider. Returns full breakdown."""
    _enforce_provider_rate_limit(provider)

    if provider == "groq":
        try:
            return _coerce_scoring_result(_score_job_groq(job_title, company, description))
        except RuntimeError as e:
            if not _is_rate_limit_error(str(e)):
                raise

            # Failover chain: Groq -> Gemini -> OpenAI
            gemini_key = get_api_key("GEMINI_API_KEY") or ""
            if gemini_key:
                try:
                    _enforce_provider_rate_limit("gemini")
                    out = _coerce_scoring_result(_score_job_gemini(job_title, company, description))
                    out["failover_from"] = "groq"
                    return out
                except Exception:
                    pass

            openai_key = get_api_key("OPENAI_API_KEY") or ""
            if openai_key:
                _enforce_provider_rate_limit("openai")
                out = _coerce_scoring_result(_score_job_openai(job_title, company, description))
                out["failover_from"] = "groq"
                return out

            raise
    if provider == "gemini":
        return _coerce_scoring_result(_score_job_gemini(job_title, company, description))
    if provider == "openai":
        return _coerce_scoring_result(_score_job_openai(job_title, company, description))
    raise ValueError(f"Unsupported provider: {provider}")


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
        qualification_threshold = _get_qualification_threshold()

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
                result = _score_job_detailed(job_title, company, description)
                elapsed = round(time.time() - start_time, 2)

                overall_score = int(result.get("overall_score", 0))
                justification = result.get("overall_justification", "")

                # Persist to DB — including detailed_score JSONB
                with db() as (conn, cur):
                    new_status = "qualified" if overall_score >= qualification_threshold else "low_score"
                    cur.execute(
                        """
                        UPDATE jobs
                        SET score = %s,
                            justification = %s,
                            status = %s,
                            detailed_score = %s,
                            scored_at = NOW(),
                            updated_at = NOW(),
                            version = version + 1
                        WHERE id = %s
                        """,
                        [overall_score, justification, new_status, json.dumps(result), job_id],
                    )

                scored_count += 1
                total_tokens += result.get("tokens_used", 0)
                _progress["scored"] = scored_count

                yield _sse_event("scored", {
                    "type": "scored",
                    "job_id": job_id,
                    "job_title": job_title,
                    "company": company,
                    "score": overall_score,
                    "justification": justification,
                    "skills_matched": result.get("skills_matched", []),
                    "skills_missing": result.get("skills_missing", []),
                    "model": result.get("model", ""),
                    "provider": result.get("provider", "openai"),
                    "tokens_used": result.get("tokens_used", 0),
                    "elapsed_seconds": elapsed,
                    "sections": result.get("sections", []),
                    "interview_probability": result.get("interview_probability", ""),
                    "key_risks": result.get("key_risks", []),
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


# ── Single-job scoring (with AI model selector) ──────────────────────────

@router.post("/scoring/single")
def score_single_job(body: SingleScoreRequest):
    """
    Score a single job (by DB id) with detailed section-by-section analysis.
    Supports model selection: "openai" | "gemini" | "compare".

    In "compare" mode, scores with BOTH providers and returns side-by-side results.
    """
    with db() as (conn, cur):
        cur.execute(
            """SELECT id, job_title, company_name, job_description
               FROM jobs WHERE id = %s""",
            [body.job_db_id],
        )
        job = cur.fetchone()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.get("job_description"):
        raise HTTPException(
            status_code=400,
            detail="Job has no description. Fetch the job URL first to get the full posting."
        )

    jt = job["job_title"] or "Unknown"
    co = job["company_name"] or "Unknown"
    desc = job["job_description"]

    # ── Compare mode: run both providers ─────────────────────────
    if body.model == "compare":
        results = {}
        errors = {}

        # Try OpenAI
        try:
            results["openai"] = _score_job_detailed(jt, co, desc, provider="openai")
        except Exception as e:
            errors["openai"] = str(e)

        # Try Gemini
        try:
            results["gemini"] = _score_job_detailed(jt, co, desc, provider="gemini")
        except Exception as e:
            errors["gemini"] = str(e)

        if not results:
            only_rate_limited = all(_is_rate_limit_error(err) for err in errors.values() if err)
            if only_rate_limited:
                raise HTTPException(
                    status_code=429,
                    detail=f"Both providers rate-limited. OpenAI: {errors.get('openai')}. Gemini: {errors.get('gemini')}."
                )
            raise HTTPException(
                status_code=500,
                detail=f"Both providers failed. OpenAI: {errors.get('openai')}. Gemini: {errors.get('gemini')}."
            )

        # Use the higher-scoring result for DB persistence
        best_provider = max(results, key=lambda k: int(results[k].get("overall_score", 0)))
        best_result = results[best_provider]

        overall_score = int(best_result.get("overall_score", 0))
        justification = best_result.get("overall_justification", "")
        qualification_threshold = _get_qualification_threshold()

        # Save comparison data to DB
        compare_payload = {
            "compare_mode": True,
            "results": results,
            "errors": errors,
            "best_provider": best_provider,
            # Duplicate top-level fields from best for backward compat
            **best_result,
        }

        new_status = "qualified" if overall_score >= qualification_threshold else "low_score"
        with db() as (conn, cur):
            cur.execute(
                """UPDATE jobs
                   SET score = %s,
                       justification = %s,
                       status = %s,
                       detailed_score = %s,
                       updated_at = NOW(),
                       version = version + 1
                   WHERE id = %s
                   RETURNING version""",
                [overall_score, justification, new_status, json.dumps(compare_payload), body.job_db_id],
            )
            conn.commit()

        return {
            "success": True,
            "job_db_id": body.job_db_id,
            "mode": "compare",
            "result": compare_payload,
        }

    # ── Single provider mode ─────────────────────────────────────
    try:
        result = _score_job_detailed(jt, co, desc, provider=body.model)
    except RuntimeError as e:
        if _is_rate_limit_error(str(e)):
            raise HTTPException(status_code=429, detail=str(e))
        raise

    overall_score = int(result.get("overall_score", 0))
    justification = result.get("overall_justification", "")
    qualification_threshold = _get_qualification_threshold()

    # Save score + justification + detailed breakdown to the job
    new_status = "qualified" if overall_score >= qualification_threshold else "low_score"
    with db() as (conn, cur):
        cur.execute(
            """UPDATE jobs
               SET score = %s,
                   justification = %s,
                   status = %s,
                   detailed_score = %s,
                   updated_at = NOW(),
                   version = version + 1
               WHERE id = %s
               RETURNING version""",
            [overall_score, justification, new_status, json.dumps(result), body.job_db_id],
        )
        conn.commit()

    return {
        "success": True,
        "job_db_id": body.job_db_id,
        "mode": body.model,
        "result": result,
    }

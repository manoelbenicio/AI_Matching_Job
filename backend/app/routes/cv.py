"""CV enhancement routes — Gemini AI integration."""

import json
import os
import difflib
import re
import logging
from html import unescape, escape
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Optional
from ..db import db

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Resume loader (reads from candidate_resume.txt or DB) ──────────────────
_resume_cache: str | None = None
_PROCESS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "processo classificacao.md")
_DEFAULT_QUALIFICATION_THRESHOLD = int(os.getenv("SCORE_THRESHOLD_DEFAULT", "80"))


def _extract_resume_from_process_file(path: str) -> str:
    """Extract resume block from processo classificacao.md (legacy workflow source)."""
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return ""

    marker = "📄 RESUME —"
    idx = text.find(marker)
    if idx == -1:
        return ""

    tail = text[idx:]
    end_candidates = [
        tail.find("\n----------------------------------------------------------------"),
        tail.find("\nYou are an expert resume building specialist."),
    ]
    end_positions = [pos for pos in end_candidates if pos != -1]
    end = min(end_positions) if end_positions else len(tail)
    return tail[:end].strip()


def _get_resume() -> str:
    """Load the candidate resume from file or DB, cached after first call."""
    global _resume_cache
    if _resume_cache is not None:
        return _resume_cache

    # Try file first
    resume_path = os.path.join(os.path.dirname(__file__), "..", "..", "candidate_resume.txt")
    resume_path = os.path.normpath(resume_path)
    if os.path.exists(resume_path):
        with open(resume_path, encoding="utf-8") as f:
            _resume_cache = f.read()
        return _resume_cache

    # Legacy workflow doc fallback
    process_resume = _extract_resume_from_process_file(_PROCESS_FILE)
    if process_resume:
        _resume_cache = process_resume
        return _resume_cache

    # Fallback: try DB candidates table
    try:
        with db() as (conn, cur):
            cur.execute("SELECT resume_text FROM candidates ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row and row["resume_text"]:
                _resume_cache = row["resume_text"]
                return _resume_cache
    except Exception:
        pass

    raise RuntimeError(
        "No resume configured. Configure an active candidate in DB or place your CV in backend/candidate_resume.txt."
    )


def _get_qualification_threshold() -> int:
    """Read runtime qualification threshold from app_settings.score_threshold."""
    try:
        with db() as (conn, cur):
            cur.execute("SELECT value FROM app_settings WHERE key = 'score_threshold'")
            row = cur.fetchone()
            if row and row.get("value") is not None:
                return max(0, min(100, int(row["value"])))
    except Exception:
        pass
    return max(0, min(100, _DEFAULT_QUALIFICATION_THRESHOLD))


class CvEnhanceRequest(BaseModel):
    job_id: int
    resume_text: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────

def _compute_diff(original: str, enhanced: str) -> list[dict]:
    """Line-by-line diff returning DiffChunk[] JSON-safe list."""
    orig_lines = original.splitlines(keepends=True)
    enh_lines = enhanced.splitlines(keepends=True)

    chunks: list[dict] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, orig_lines, enh_lines
    ).get_opcodes():
        if tag == "equal":
            chunks.append({
                "type": "unchanged",
                "content": "".join(orig_lines[i1:i2]).rstrip("\n"),
            })
        elif tag == "replace":
            chunks.append({
                "type": "removed",
                "content": "".join(orig_lines[i1:i2]).rstrip("\n"),
            })
            chunks.append({
                "type": "added",
                "content": "".join(enh_lines[j1:j2]).rstrip("\n"),
            })
        elif tag == "delete":
            chunks.append({
                "type": "removed",
                "content": "".join(orig_lines[i1:i2]).rstrip("\n"),
            })
        elif tag == "insert":
            chunks.append({
                "type": "added",
                "content": "".join(enh_lines[j1:j2]).rstrip("\n"),
            })
    return chunks


def _extract_gaps_from_score(detailed_score) -> str:
    """Extract weaknesses + missing skills from a job's detailed_score JSONB.

    Handles:
    - New 8-dimension format (sections array)
    - Compare payload (best provider result)
    - Legacy section_evaluations / dict formats
    Returns a bullet-point string ready for prompt injection, or '' if no data.
    """
    if not detailed_score:
        return ""

    # detailed_score may be a JSON string or already a dict
    if isinstance(detailed_score, str):
        try:
            detailed_score = json.loads(detailed_score)
        except (json.JSONDecodeError, TypeError):
            return ""

    if not isinstance(detailed_score, dict):
        return ""

    # Compare payload support: use best provider output as the active payload
    payload = detailed_score
    if payload.get("compare_mode") and isinstance(payload.get("results"), dict):
        best = payload.get("best_provider")
        results = payload.get("results", {})
        if isinstance(best, str) and isinstance(results.get(best), dict):
            payload = results[best]
        else:
            for fallback in ("openai", "gemini"):
                if isinstance(results.get(fallback), dict):
                    payload = results[fallback]
                    break

    def _to_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(v).strip() for v in value if str(v).strip()]

    gaps: list[str] = []

    # Extract section weaknesses — handle array (new) and dict (legacy) formats
    sections = payload.get("sections", [])
    if isinstance(sections, list):
        # New format: [{"dimension": "...", "weak": [...], ...}]
        for section in sections:
            if isinstance(section, dict):
                dim = section.get("dimension", "Unknown")
                weak_points = (
                    _to_list(section.get("weak"))
                    or _to_list(section.get("weak_points"))
                    or _to_list(section.get("weaknesses"))
                    or _to_list(section.get("gaps"))
                )
                for w in weak_points:
                    gaps.append(f"- [{dim}] {w}")
                for r in _to_list(section.get("recommendations")):
                    gaps.append(f"- [{dim} Recommendation] {r}")
    elif isinstance(sections, dict):
        # Legacy format: {"section_name": {"weaknesses": [...]}}
        for name, section in sections.items():
            if isinstance(section, dict):
                weak_points = (
                    _to_list(section.get("weaknesses"))
                    or _to_list(section.get("weak"))
                    or _to_list(section.get("weak_points"))
                    or _to_list(section.get("gaps"))
                )
                for w in weak_points:
                    gaps.append(f"- [{name}] {w}")
                for r in _to_list(section.get("recommendations")):
                    gaps.append(f"- [{name} Recommendation] {r}")

    # Legacy section_evaluations support
    section_evaluations = payload.get("section_evaluations")
    if isinstance(section_evaluations, dict):
        for name, section in section_evaluations.items():
            if not isinstance(section, dict):
                continue
            for w in _to_list(section.get("gaps")):
                gaps.append(f"- [{name}] {w}")
            for r in _to_list(section.get("recommendations")):
                gaps.append(f"- [{name} Recommendation] {r}")

    # Extract top-level missing skills
    for skill in _to_list(payload.get("skills_missing")):
        gaps.append(f"- [Missing Skill] {skill}")

    # Also check top-level weaknesses / risks / legacy gaps
    for w in _to_list(payload.get("weaknesses")):
        gaps.append(f"- {w}")
    for r in _to_list(payload.get("key_risks")):
        gaps.append(f"- [Risk] {r}")
    for r in _to_list(payload.get("critical_gaps")):
        gaps.append(f"- [Risk] {r}")
    for suggestion in _to_list(payload.get("cv_enhancement_suggestions")):
        gaps.append(f"- [CV Suggestion] {suggestion}")

    # De-duplicate while preserving order
    deduped = list(dict.fromkeys(gaps))
    return "\n".join(deduped) if deduped else ""


def _extract_skill_hints_from_score(detailed_score: Any) -> tuple[list[str], list[str], Optional[int]]:
    """
    Extract fallback matched/missing skills and fit score from detailed_score payload.
    Supports compare mode + normalized/legacy payloads.
    """
    if not detailed_score:
        return [], [], None

    payload = detailed_score
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return [], [], None
    if not isinstance(payload, dict):
        return [], [], None

    if payload.get("compare_mode") and isinstance(payload.get("results"), dict):
        results = payload.get("results", {})
        best = payload.get("best_provider")
        if isinstance(best, str) and isinstance(results.get(best), dict):
            payload = results[best]
        else:
            for p in ("openai", "gemini"):
                if isinstance(results.get(p), dict):
                    payload = results[p]
                    break

    def _to_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        out: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                out.append(text)
        return out

    matched = _to_list(payload.get("skills_matched")) or _to_list(payload.get("key_strengths")) or _to_list(payload.get("key_matches"))
    missing = _to_list(payload.get("skills_missing")) or _to_list(payload.get("critical_gaps")) or _to_list(payload.get("gaps"))

    if not matched or not missing:
        sections = payload.get("sections")
        if isinstance(sections, list):
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                if not matched:
                    matched.extend(_to_list(sec.get("strong")) or _to_list(sec.get("strong_points")) or _to_list(sec.get("matches")))
                if not missing:
                    missing.extend(_to_list(sec.get("weak")) or _to_list(sec.get("weak_points")) or _to_list(sec.get("weaknesses")) or _to_list(sec.get("gaps")))
        elif isinstance(sections, dict):
            for sec in sections.values():
                if not isinstance(sec, dict):
                    continue
                if not matched:
                    matched.extend(_to_list(sec.get("strong")) or _to_list(sec.get("strong_points")) or _to_list(sec.get("matches")))
                if not missing:
                    missing.extend(_to_list(sec.get("weak")) or _to_list(sec.get("weak_points")) or _to_list(sec.get("weaknesses")) or _to_list(sec.get("gaps")))

    fit_score: Optional[int] = None
    raw_fit = payload.get("fit_score", payload.get("overall_score", payload.get("score")))
    try:
        if raw_fit is not None:
            fit_score = max(0, min(100, int(raw_fit)))
    except Exception:
        fit_score = None

    matched = list(dict.fromkeys(matched))
    missing = list(dict.fromkeys(missing))
    return matched[:12], missing[:12], fit_score


def _extract_enhanced_cv_from_json_like_text(text: str) -> Optional[str]:
    """Try to extract enhanced_cv field from a JSON-like string payload."""
    if not isinstance(text, str):
        return None
    stripped = text.strip()
    if not stripped:
        return None

    # Direct JSON parse first.
    try:
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            cv = payload.get("enhanced_cv")
            if isinstance(cv, str) and cv.strip():
                return cv.strip()
    except Exception:
        pass

    # Fallback for malformed/truncated JSON.
    key_match = re.search(r'"enhanced_cv"\s*:\s*"', stripped)
    if not key_match:
        return None

    raw_chars: list[str] = []
    escaped = False
    idx = key_match.end()
    while idx < len(stripped):
        ch = stripped[idx]
        if escaped:
            raw_chars.append(ch)
            escaped = False
            idx += 1
            continue
        if ch == "\\":
            raw_chars.append(ch)
            escaped = True
            idx += 1
            continue
        if ch == '"':
            # End of JSON string value.
            break
        raw_chars.append(ch)
        idx += 1

    raw = "".join(raw_chars).strip()
    if not raw:
        return None

    try:
        return json.loads(f'"{raw}"').strip()
    except Exception:
        # Best effort unescape for partial/truncated JSON strings.
        return (
            raw.replace('\\"', '"')
            .replace("\\n", "\n")
            .replace("\\r", "\n")
            .replace("\\t", "\t")
            .replace("\\/", "/")
            .replace("\\\\", "\\")
            .strip()
        )


def _normalize_enhanced_content(content: Any) -> str:
    """
    Return clean enhanced CV HTML text from different storage formats:
    - raw HTML
    - JSON object string containing {"enhanced_cv": "..."}
    - dict payload containing enhanced_cv
    """
    if isinstance(content, dict):
        content = content.get("enhanced_cv") or ""

    if not isinstance(content, str):
        return ""

    text = content.strip()
    if not text:
        return ""

    # Markdown fence cleanup.
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```html\s*", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```\s*", "", text).strip()
    text = re.sub(r"\s*```$", "", text).strip()

    # If the whole text is a JSON object (or malformed one containing enhanced_cv), extract HTML.
    extracted = _extract_enhanced_cv_from_json_like_text(text)
    if extracted:
        text = extracted

    # If the value is still a quoted JSON string, unquote once.
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        try:
            text = json.loads(text)
        except Exception:
            text = text[1:-1]

    return unescape(str(text).strip())


def _normalize_cv_ai_payload(payload: dict, raw_text_fallback: str = "") -> dict:
    """Normalize Gemini CV payload to stable contract."""
    enhanced_cv = _normalize_enhanced_content(payload.get("enhanced_cv"))
    if not isinstance(enhanced_cv, str) or not enhanced_cv.strip():
        if isinstance(raw_text_fallback, str) and raw_text_fallback.strip():
            enhanced_cv = _normalize_enhanced_content(raw_text_fallback.strip())
    if not isinstance(enhanced_cv, str) or not enhanced_cv.strip():
        raise ValueError("Gemini response did not include a valid enhanced_cv payload.")

    def _to_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        out = []
        for item in value:
            s = str(item).strip()
            if s:
                out.append(s)
        return out

    fit_score_raw = payload.get("fit_score", payload.get("overall_score", payload.get("score")))
    fit_score: Optional[int] = None
    try:
        if fit_score_raw is not None and str(fit_score_raw).strip() != "":
            fit_score = max(0, min(100, int(fit_score_raw)))
    except Exception:
        fit_score = None

    return {
        "enhanced_cv": enhanced_cv,
        "skills_matched": _to_list(payload.get("skills_matched")),
        "skills_missing": _to_list(payload.get("skills_missing")),
        "fit_score": fit_score,
    }


def _is_enhanced_cv_usable(enhanced_cv: str) -> bool:
    """Heuristic guard to reject truncated/malformed enhancement payloads."""
    if not isinstance(enhanced_cv, str):
        return False
    text = enhanced_cv.strip()
    if not text:
        return False
    lowered = text.lower()
    if '{"enhanced_cv"' in lowered or "'enhanced_cv'" in lowered:
        return False
    if len(text) < 900:
        return False
    if "<h1" not in lowered:
        return False
    if lowered.count("<h2") < 2:
        return False
    return True


def _build_structured_fallback_html(
    resume_text: str,
    job_title: str,
    company: str,
    skills_matched: list[str],
    skills_missing: list[str],
) -> str:
    """
    Deterministic fallback HTML builder when Gemini output is truncated.
    Guarantees a complete ATS-safe document skeleton.
    """
    raw_lines = [ln.strip() for ln in (resume_text or "").splitlines() if ln.strip()]
    cleaned_lines = [re.sub(r"^[\W_]+", "", ln).strip() for ln in raw_lines]
    cleaned_lines = [ln for ln in cleaned_lines if ln]

    name = cleaned_lines[0] if cleaned_lines else "Candidate"
    contact = ""
    start_idx = 1
    if len(cleaned_lines) > 1:
        second = cleaned_lines[1]
        if ("@" in second) or ("|" in second) or ("linkedin" in second.lower()) or ("+" in second):
            contact = second
            start_idx = 2

    heading_map = {
        "profile": "summary",
        "professional summary": "summary",
        "summary": "summary",
        "core competencies": "skills",
        "skills": "skills",
        "technical skills": "skills",
        "experience": "experience",
        "professional experience": "experience",
        "education": "education",
        "certifications": "certifications",
        "languages": "languages",
        "projects": "projects",
        "awards": "awards",
    }
    ordered_sections = [
        ("Professional Summary", "summary"),
        ("Experience", "experience"),
        ("Skills", "skills"),
        ("Education", "education"),
        ("Certifications", "certifications"),
        ("Projects", "projects"),
        ("Languages", "languages"),
        ("Awards", "awards"),
    ]
    bucket: dict[str, list[str]] = {key: [] for _, key in ordered_sections}
    current = "summary"

    for line in cleaned_lines[start_idx:]:
        normalized = re.sub(r"[^a-zA-Z ]", "", line).strip().lower()
        mapped = heading_map.get(normalized)
        if mapped:
            current = mapped
            continue
        bucket.setdefault(current, []).append(line)

    def _render_lines(lines: list[str]) -> str:
        html_parts: list[str] = []
        in_list = False
        for line in lines:
            bullet = re.match(r"^[-*•]\s+(.+)$", line)
            if bullet:
                if not in_list:
                    html_parts.append("<ul>")
                    in_list = True
                html_parts.append(f"<li>{escape(bullet.group(1).strip())}</li>")
            else:
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                html_parts.append(f"<p>{escape(line)}</p>")
        if in_list:
            html_parts.append("</ul>")
        return "".join(html_parts)

    parts = [
        f"<h1>{escape(name)}</h1>",
        f"<p><em>Targeting: {escape(job_title)} at {escape(company)}</em></p>",
    ]
    if contact:
        parts.append(f"<p>{escape(contact)}</p>")

    for title, key in ordered_sections:
        lines = bucket.get(key) or []
        if not lines:
            continue
        parts.append(f"<h2>{title}</h2>")
        parts.append(_render_lines(lines))

    if skills_matched:
        parts.append("<h2>Role Alignment Highlights</h2><ul>")
        for item in skills_matched[:10]:
            parts.append(f"<li>{escape(str(item))}</li>")
        parts.append("</ul>")

    if skills_missing:
        parts.append("<h2>Gap Mitigation Focus</h2><ul>")
        for item in skills_missing[:8]:
            parts.append(f"<li>Address in interviews/CV: {escape(str(item))}</li>")
        parts.append("</ul>")

    return "".join(parts)


def _extract_name_from_html(html: str) -> str:
    """Best-effort candidate name extraction from enhanced HTML content."""
    if not html:
        return ""

    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)
    if h1_match:
        raw = re.sub(r"<[^>]+>", " ", h1_match.group(1))
        raw = unescape(raw).strip()
        if raw:
            return raw

    plain = re.sub(r"<[^>]+>", "\n", html)
    for line in plain.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if len(candidate) > 80:
            continue
        if any(ch in candidate for ch in "@|"):
            continue
        return candidate
    return ""


def _extract_name_from_resume_text(resume_text: str) -> str:
    """Best-effort name extraction from raw resume text."""
    for line in (resume_text or "").splitlines():
        candidate = line.strip().lstrip("#").strip()
        if not candidate:
            continue
        if len(candidate) > 80:
            continue
        if any(ch in candidate for ch in "@|"):
            continue
        return candidate
    return ""


def _resolve_candidate_name(db_name: Optional[str], enhanced_content: Any) -> str:
    """
    Resolve candidate name robustly.
    Avoids generic placeholders like 'Default Candidate' when better data exists.
    """
    placeholder_names = {"candidate", "default candidate", "unknown", "unknown candidate"}
    raw_db_name = (db_name or "").strip()
    if raw_db_name and raw_db_name.lower() not in placeholder_names:
        return raw_db_name

    normalized = _normalize_enhanced_content(enhanced_content)
    from_html = _extract_name_from_html(normalized)
    if from_html and from_html.lower() not in placeholder_names:
        return from_html

    try:
        resume_name = _extract_name_from_resume_text(_get_resume())
        if resume_name and resume_name.lower() not in placeholder_names:
            return resume_name
    except Exception:
        pass

    return raw_db_name or "Candidate"


def _extract_json_robust_cv(text: str) -> dict:
    """Robust JSON extraction for CV enhancement responses."""
    if not text or not text.strip():
        raise ValueError("Empty Gemini response")

    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # 1) direct JSON parse
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return _normalize_cv_ai_payload(payload)
    except Exception:
        pass

    # 2) extract first JSON object
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if m:
        candidate = m.group(0)
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return _normalize_cv_ai_payload(payload)
        except Exception:
            # try closing truncation braces
            fixed = candidate
            open_brackets = fixed.count("[") - fixed.count("]")
            open_braces = fixed.count("{") - fixed.count("}")
            if open_brackets > 0:
                fixed += "]" * open_brackets
            if open_braces > 0:
                fixed += "}" * open_braces
            try:
                payload = json.loads(fixed)
                if isinstance(payload, dict):
                    return _normalize_cv_ai_payload(payload)
            except Exception:
                pass

    # 3) HTML fallback if model returned direct HTML instead of JSON
    if "<h1" in cleaned.lower() or ("<p" in cleaned.lower() and "<" in cleaned and ">" in cleaned):
        return _normalize_cv_ai_payload({}, raw_text_fallback=cleaned)

    raise ValueError("Gemini returned invalid JSON and no HTML fallback could be extracted.")


def _call_gemini(resume_text: str, job_title: str, company: str, description: str, gaps: str = "") -> dict:
    """Call Gemini 2.5 Flash to enhance the resume and return structured JSON.

    If `gaps` is provided (from the scoring phase), they are injected into the
    prompt so Gemini explicitly addresses each weakness using transferable skills.
    """
    import google.generativeai as genai

    from .settings import get_api_key
    api_key = get_api_key("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not configured. Set it in Settings or .env file."
        )

    genai.configure(api_key=api_key)

    resume_for_prompt = (resume_text or "")[:12000]
    prompt = f"""You are an expert resume building specialist.
Your task is to THINK DEEPLY to build AND enhance the originally provided resume based on the job requirements from the LinkedIn job postings.

INSTRUCTIONS:
1. Take the original resume content and the job posting details below
2. Recreate and enhance the resume to tailor and match the job requirements of the posting
3. Keep ALL original sections: Summary/Profile, Experience, Education, Skills, Certifications, Languages
4. Improve the content to highlight relevant skills and experiences that match the job requirements
5. Use EXACT keywords from the job posting wherever truthful
6. Quantify achievements wherever possible (numbers, percentages, dollar amounts)
7. Maintain professional structure and formatting
8. Output the COMPLETE enhanced resume with ALL sections — do not omit anything

CRITICAL FORMAT RULES for the "enhanced_cv" field:
- Output ONLY clean HTML content (NO markdown, NO code fences, NO backticks)
- Start with <h1> tag for the candidate name
- Use <h2> for section headers (Summary, Experience, Education, Skills, etc.)
- Use <h3> for job titles / company names within Experience
- Use <p> for paragraphs, <ul>/<li> for bullet points
- Use <strong> and <em> for emphasis where appropriate
- Do NOT include <html>, <head>, <body> wrapper tags — just the content HTML

TARGET POSITION:
Company: {company}
Title: {job_title}
Job Posting Description:
{description[:4000]}

CANDIDATE'S RESUME:
{resume_for_prompt}

{f'''## GAPS IDENTIFIED (from scoring phase)
These gaps were found between the candidate and job requirements.
For EACH gap, find transferable skills or related experience to cover it:
{gaps}''' if gaps else ''}

You MUST respond with ONLY valid JSON (no markdown, no code fences) matching this exact schema:
{{
  "enhanced_cv": "<h1>Candidate Name</h1><h2>Professional Summary</h2><p>...</p>...",
  "skills_matched": ["skill1", "skill2", ...],
  "skills_missing": ["skill1", "skill2", ...],
  "fit_score": 85
}}

CRITICAL: Output ONLY the JSON object. The enhanced_cv value must be clean HTML."""

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    model_name = os.getenv("GEMINI_CV_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=7000,
            response_mime_type="application/json",
        ),
        safety_settings=safety_settings,
    )

    # If blocked/empty, fail with actionable reason.
    if not getattr(response, "candidates", None):
        raise HTTPException(status_code=502, detail="Gemini returned no candidates (possibly blocked by safety filters).")

    try:
        text = (response.text or "").strip()
    except Exception:
        text = ""

    try:
        return _extract_json_robust_cv(text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini returned invalid JSON. {str(e)}")


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("/cv/parse")
async def parse_cv(file: UploadFile = File(...)):
    """Accept a CV file (TXT, PDF, DOCX) and return extracted text."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed = {"txt", "text", "pdf", "docx", "doc"}
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(allowed))}"
        )

    raw = await file.read()
    size_bytes = len(raw)

    # Extract text based on file type
    if ext in ("txt", "text"):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
    elif ext == "pdf":
        # Lightweight PDF text extraction (no external deps)
        text = _extract_pdf_text(raw)
    elif ext in ("docx", "doc"):
        text = _extract_docx_text(raw)
    else:
        text = raw.decode("utf-8", errors="replace")

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the uploaded file. Try a .txt file."
        )

    return {
        "text": text.strip(),
        "filename": file.filename,
        "size_bytes": size_bytes,
    }


def _extract_pdf_text(data: bytes) -> str:
    """Best-effort PDF text extraction without external libraries."""
    import re
    text_parts = []
    # Extract text between BT and ET operators (basic PDF text extraction)
    try:
        # Try to find text streams
        content = data.decode("latin-1")
        # Find text between parentheses in BT..ET blocks
        bt_blocks = re.findall(r"BT(.*?)ET", content, re.DOTALL)
        for block in bt_blocks:
            # Extract text from Tj and TJ operators
            strings = re.findall(r"\(([^)]+)\)", block)
            text_parts.extend(strings)
    except Exception:
        pass

    result = " ".join(text_parts)
    if not result.strip():
        return "[PDF text extraction requires the file to contain selectable text. Please paste your resume text directly or upload a .txt file.]"
    return result


def _extract_docx_text(data: bytes) -> str:
    """Extract text from DOCX using zipfile + XML parsing (no external deps)."""
    import zipfile
    import io
    import re

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            if "word/document.xml" not in zf.namelist():
                return "[Invalid DOCX file]"
            xml_content = zf.read("word/document.xml").decode("utf-8")
            # Strip XML tags to get plain text
            text = re.sub(r"<[^>]+>", "", xml_content)
            # Clean up whitespace
            text = re.sub(r"\s+", " ", text).strip()
            return text
    except Exception:
        return "[Could not parse DOCX. Please upload a .txt file instead.]"


@router.post("/cv/enhance")
def enhance_cv(body: CvEnhanceRequest):
    """Enhance a resume for a specific job using Gemini AI."""

    # 1. Load the job
    with db() as (conn, cur):
        cur.execute(
            "SELECT id, job_title, company_name, job_description, detailed_score FROM jobs WHERE id = %s",
            [body.job_id],
        )
        job = cur.fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    try:
        resume = body.resume_text or _get_resume()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 2. Extract gaps from detailed_score (if available)
    gaps = _extract_gaps_from_score(job.get("detailed_score"))

    # 3. Call Gemini (with gap injection)
    ai = _call_gemini(
        resume_text=resume,
        job_title=job["job_title"],
        company=job["company_name"],
        description=job["job_description"] or "",
        gaps=gaps,
    )

    fallback_matched, fallback_missing, fallback_fit = _extract_skill_hints_from_score(job.get("detailed_score"))
    enhanced_cv = _normalize_enhanced_content(ai.get("enhanced_cv", ""))

    raw_matched = ai.get("skills_matched")
    raw_missing = ai.get("skills_missing")
    skills_matched = [str(s).strip() for s in raw_matched] if isinstance(raw_matched, list) else []
    skills_missing = [str(s).strip() for s in raw_missing] if isinstance(raw_missing, list) else []
    skills_matched = [s for s in skills_matched if s]
    skills_missing = [s for s in skills_missing if s]
    if not skills_matched:
        skills_matched = fallback_matched
    if not skills_missing:
        skills_missing = fallback_missing

    if not _is_enhanced_cv_usable(enhanced_cv):
        enhanced_cv = _build_structured_fallback_html(
            resume_text=resume,
            job_title=job["job_title"] or "Position",
            company=job["company_name"] or "Company",
            skills_matched=skills_matched,
            skills_missing=skills_missing,
        )

    raw_fit_score = ai.get("fit_score")
    fit_score: Optional[int]
    try:
        fit_score = max(0, min(100, int(raw_fit_score))) if raw_fit_score is not None else None
    except Exception:
        fit_score = None
    fallback_score = fallback_fit if (fallback_fit is not None and fallback_fit > 0) else int(job.get("score") or 0)
    if fit_score is None or (fit_score <= 0 and fallback_score > 0):
        fit_score = fallback_score

    # 3. Compute diff
    diff_chunks = _compute_diff(resume, enhanced_cv)

    # 4. Persist to cv_versions
    with db() as (conn, cur):
        # Determine next version number
        cur.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_ver FROM cv_versions WHERE job_id = %s",
            [body.job_id],
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
                body.job_id,
                next_ver,
                resume,
                enhanced_cv,
                json.dumps(skills_matched or []),
                json.dumps(skills_missing or []),
                fit_score,
            ],
        )
        version_id = cur.fetchone()["id"]

        # 5. Audit log
        cur.execute(
            """
            INSERT INTO audit_log (job_id, action, field, new_value)
            VALUES (%s, 'cv_enhanced', 'cv_version', %s)
            """,
            [body.job_id, str(next_ver)],
        )

    return {
        "enhanced_cv": enhanced_cv,
        "diff": diff_chunks,
        "version_id": version_id,
        "fit_score": fit_score,
        "skills_matched": skills_matched,
        "skills_missing": skills_missing,
    }


@router.get("/cv/versions/{job_id}")
def get_cv_versions(job_id: int):
    """Return all CV versions for a job, newest first."""
    with db() as (conn, cur):
        cur.execute(
            """
            SELECT id, job_id, version_number, content, enhanced_content,
                   skills_matched, skills_missing, fit_score, created_at
            FROM cv_versions
            WHERE job_id = %s
            ORDER BY version_number DESC
            """,
            [job_id],
        )
        rows = cur.fetchall()

    result = []
    for r in rows:
        item = dict(r)
        if item.get("created_at"):
            item["created_at"] = item["created_at"].isoformat()
        if item.get("enhanced_content"):
            item["enhanced_content"] = _normalize_enhanced_content(item["enhanced_content"])
        # JSONB columns come as Python dicts/lists already from psycopg2
        result.append(item)
    return result


# ── Premium Export (ATS-Optimized DOCX) ────────────────────────────────

class PremiumExportRequest(BaseModel):
    job_id: int
    version_id: Optional[int] = None


@router.post("/cv/premium-export")
def premium_export(body: PremiumExportRequest):
    """Generate an ATS-optimized DOCX resume for a job (qualification-threshold gate)."""
    import io
    from ..services.premium_export import generate_premium_docx, _validate_enhancement_for_export

    # 1. Load the job and verify score gate
    qualification_threshold = _get_qualification_threshold()
    with db() as (conn, cur):
        cur.execute(
            "SELECT id, job_title, company_name, score, detailed_score FROM jobs WHERE id = %s",
            [body.job_id],
        )
        job = cur.fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        score = job["score"]
        if score is None or score < qualification_threshold:
            raise HTTPException(
                status_code=400,
                detail=f"Score ({score or 'N/A'}) is below the {qualification_threshold}% threshold for premium export.",
            )

        # 2. Get the latest enhanced CV version
        if body.version_id:
            cur.execute(
                "SELECT id, enhanced_content, skills_matched, skills_missing FROM cv_versions WHERE id = %s AND job_id = %s",
                [body.version_id, body.job_id],
            )
        else:
            cur.execute(
                """SELECT id, enhanced_content, skills_matched, skills_missing
                   FROM cv_versions WHERE job_id = %s
                   ORDER BY version_number DESC LIMIT 1""",
                [body.job_id],
            )
        version = cur.fetchone()
        if not version or not version["enhanced_content"]:
            raise HTTPException(
                status_code=404,
                detail="No enhanced CV found. Run CV enhancement first.",
            )

        # Get candidate name from active candidate
        cur.execute(
            "SELECT name FROM candidates WHERE is_active = true LIMIT 1"
        )
        cand = cur.fetchone()
        candidate_name = cand["name"] if cand else None

    # Parse JSONB fields
    skills_matched = version["skills_matched"]
    skills_missing = version["skills_missing"]
    if isinstance(skills_matched, str):
        try:
            skills_matched = json.loads(skills_matched)
        except Exception:
            skills_matched = []
    if isinstance(skills_missing, str):
        try:
            skills_missing = json.loads(skills_missing)
        except Exception:
            skills_missing = []
    fallback_matched, fallback_missing, _ = _extract_skill_hints_from_score(job.get("detailed_score"))
    if not isinstance(skills_matched, list) or not skills_matched:
        skills_matched = fallback_matched
    if not isinstance(skills_missing, list) or not skills_missing:
        skills_missing = fallback_missing
    enhanced_content = _normalize_enhanced_content(version["enhanced_content"])
    candidate_name = _resolve_candidate_name(candidate_name, enhanced_content)
    is_valid, validation_errors = _validate_enhancement_for_export(
        {
            "format": "docx",
            "content": enhanced_content,
            "rendered_text": enhanced_content,
        }
    )
    if not is_valid:
        logger.warning(
            "Premium DOCX export blocked for job_id=%s due to quality gate errors: %s",
            body.job_id,
            "; ".join(validation_errors),
        )
        raise HTTPException(
            status_code=422,
            detail=(
                f"Export blocked — quality gate failed with {len(validation_errors)} error(s): "
                + "; ".join(validation_errors)
            ),
        )

    # 3. Generate DOCX
    try:
        docx_bytes = generate_premium_docx(
            enhanced_cv_text=enhanced_content,
            job_title=job["job_title"],
            company=job["company_name"],
            candidate_name=candidate_name,
            skills_matched=skills_matched,
            skills_missing=skills_missing,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 4. Audit log
    with db() as (conn, cur):
        cur.execute(
            """INSERT INTO audit_log (job_id, action, field, new_value)
               VALUES (%s, 'premium_export', 'cv_docx', 'generated')""",
            [body.job_id],
        )

    # 5. Return as downloadable file
    safe_title = job["job_title"].replace(" ", "_")[:30]
    safe_company = job["company_name"].replace(" ", "_")[:20]
    filename = f"CV_{safe_company}_{safe_title}_ATS.docx"

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Google Drive Archive ──────────────────────────────────────────────

class DriveArchiveRequest(BaseModel):
    job_id: int
    version_id: Optional[int] = None


@router.post("/cv/archive-to-drive")
def archive_to_drive(body: DriveArchiveRequest):
    """Generate premium DOCX and upload to Google Drive."""
    import io
    from ..services.premium_export import generate_premium_docx, _validate_enhancement_for_export
    from ..services.drive_service import upload_to_drive

    # Reuse the same data-loading logic
    qualification_threshold = _get_qualification_threshold()
    with db() as (conn, cur):
        cur.execute(
            "SELECT id, job_title, company_name, score, detailed_score FROM jobs WHERE id = %s",
            [body.job_id],
        )
        job = cur.fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if (job["score"] or 0) < qualification_threshold:
            raise HTTPException(status_code=400, detail=f"Score below {qualification_threshold}% threshold")

        if body.version_id:
            cur.execute(
                "SELECT id, enhanced_content, skills_matched, skills_missing FROM cv_versions WHERE id = %s AND job_id = %s",
                [body.version_id, body.job_id],
            )
        else:
            cur.execute(
                """SELECT id, enhanced_content, skills_matched, skills_missing
                   FROM cv_versions WHERE job_id = %s
                   ORDER BY version_number DESC LIMIT 1""",
                [body.job_id],
            )
        version = cur.fetchone()
        if not version or not version["enhanced_content"]:
            raise HTTPException(status_code=404, detail="No enhanced CV found")

        cur.execute("SELECT name FROM candidates WHERE is_active = true LIMIT 1")
        cand = cur.fetchone()
        candidate_name = cand["name"] if cand else None

    skills_matched = version["skills_matched"]
    skills_missing = version["skills_missing"]
    if isinstance(skills_matched, str):
        try:
            skills_matched = json.loads(skills_matched)
        except Exception:
            skills_matched = []
    if isinstance(skills_missing, str):
        try:
            skills_missing = json.loads(skills_missing)
        except Exception:
            skills_missing = []
    fallback_matched, fallback_missing, _ = _extract_skill_hints_from_score(job.get("detailed_score"))
    if not isinstance(skills_matched, list) or not skills_matched:
        skills_matched = fallback_matched
    if not isinstance(skills_missing, list) or not skills_missing:
        skills_missing = fallback_missing
    enhanced_content = _normalize_enhanced_content(version["enhanced_content"])
    candidate_name = _resolve_candidate_name(candidate_name, enhanced_content)
    is_valid, validation_errors = _validate_enhancement_for_export(
        {
            "format": "docx",
            "content": enhanced_content,
            "rendered_text": enhanced_content,
        }
    )
    if not is_valid:
        logger.warning(
            "Drive archive blocked for job_id=%s due to quality gate errors: %s",
            body.job_id,
            "; ".join(validation_errors),
        )
        raise HTTPException(
            status_code=422,
            detail=(
                f"Export blocked — quality gate failed with {len(validation_errors)} error(s): "
                + "; ".join(validation_errors)
            ),
        )

    try:
        docx_bytes = generate_premium_docx(
            enhanced_cv_text=enhanced_content,
            job_title=job["job_title"],
            company=job["company_name"],
            candidate_name=candidate_name,
            skills_matched=skills_matched,
            skills_missing=skills_missing,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    safe_title = job["job_title"].replace(" ", "_")[:30]
    safe_company = job["company_name"].replace(" ", "_")[:20]
    filename = f"CV_{safe_company}_{safe_title}_ATS.docx"

    result = upload_to_drive(docx_bytes, filename)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message", "Drive upload failed"))

    # Audit log + stamp drive_url on cv_versions
    drive_url = result.get("drive_url", "")
    with db() as (conn, cur):
        cur.execute(
            """INSERT INTO audit_log (job_id, action, field, new_value)
               VALUES (%s, 'drive_archive', 'cv_docx', %s)""",
            [body.job_id, drive_url],
        )
        # Stamp drive_url on the exact exported version row.
        cur.execute(
            "UPDATE cv_versions SET drive_url = %s WHERE id = %s",
            [drive_url, version["id"]],
        )

    return result


# ── Premium HTML Export (ATS + Premium templates) ────────────────────────

class PremiumHtmlRequest(BaseModel):
    job_id: int
    version_id: Optional[int] = None
    template: str = "premium"  # "ats" | "premium"


@router.post("/cv/premium-html")
def premium_html(body: PremiumHtmlRequest):
    """Return a fully styled HTML version of the enhanced CV.

    Templates:
    - **ats**: Clean, B&W, no-frills — optimised for ATS parsers.
    - **premium**: Modern, gradient header, sidebar skills — for human readers.
    """
    from ..services.premium_export import _validate_enhancement_for_export

    template = (body.template or "").strip().lower()
    if template not in {"ats", "premium"}:
        raise HTTPException(status_code=400, detail="Invalid template. Use 'ats' or 'premium'.")

    # 1. Load the job
    with db() as (conn, cur):
        cur.execute(
            "SELECT id, job_title, company_name, score, detailed_score FROM jobs WHERE id = %s",
            [body.job_id],
        )
        job = cur.fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # 2. Get the latest (or specific) CV version
        if body.version_id:
            cur.execute(
                "SELECT enhanced_content, skills_matched, skills_missing, fit_score FROM cv_versions WHERE id = %s AND job_id = %s",
                [body.version_id, body.job_id],
            )
        else:
            cur.execute(
                """SELECT enhanced_content, skills_matched, skills_missing, fit_score
                   FROM cv_versions WHERE job_id = %s
                   ORDER BY version_number DESC LIMIT 1""",
                [body.job_id],
            )
        version = cur.fetchone()
        if not version or not version["enhanced_content"]:
            raise HTTPException(status_code=404, detail="No enhanced CV found. Run CV enhancement first.")

        # Get candidate name
        cur.execute("SELECT name FROM candidates WHERE is_active = true LIMIT 1")
        cand = cur.fetchone()
        candidate_name = cand["name"] if cand else None

    enhanced_html = version["enhanced_content"]
    skills_matched = version["skills_matched"]
    skills_missing = version["skills_missing"]
    if isinstance(skills_matched, str):
        try:
            skills_matched = json.loads(skills_matched)
        except Exception:
            skills_matched = []
    if isinstance(skills_missing, str):
        try:
            skills_missing = json.loads(skills_missing)
        except Exception:
            skills_missing = []
    fallback_matched, fallback_missing, _ = _extract_skill_hints_from_score(job.get("detailed_score"))
    if not isinstance(skills_matched, list) or not skills_matched:
        skills_matched = fallback_matched
    if not isinstance(skills_missing, list) or not skills_missing:
        skills_missing = fallback_missing
    enhanced_html = _normalize_enhanced_content(enhanced_html)
    candidate_name = _resolve_candidate_name(candidate_name, enhanced_html)
    is_valid, validation_errors = _validate_enhancement_for_export(
        {
            "format": "html",
            "html": enhanced_html,
            "content": enhanced_html,
            "rendered_text": enhanced_html,
        }
    )
    if not is_valid:
        logger.warning(
            "Premium HTML export blocked for job_id=%s due to quality gate errors: %s",
            body.job_id,
            "; ".join(validation_errors),
        )
        raise HTTPException(
            status_code=422,
            detail=(
                f"Export blocked — quality gate failed with {len(validation_errors)} error(s): "
                + "; ".join(validation_errors)
            ),
        )

    job_title = job["job_title"] or "Position"
    company = job["company_name"] or "Company"
    score = job["score"] or 0

    # Pick template
    if template == "ats":
        html = _render_ats_html(enhanced_html, candidate_name, job_title, company, skills_matched)
    else:
        html = _render_premium_html(enhanced_html, candidate_name, job_title, company, score, skills_matched, skills_missing)

    return {
        "html": html,
        "template": template,
        "job_title": job_title,
        "company": company,
    }


def _render_ats_html(
    content: str, name: str, title: str, company: str, skills: list
) -> str:
    """Clean ATS-friendly HTML — no colours, no layout tricks."""
    skills_html = ", ".join(skills[:25]) if skills else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — {title}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Calibri', 'Segoe UI', Arial, sans-serif; font-size: 11pt; color: #1a1a1a; line-height: 1.5; max-width: 800px; margin: 0 auto; padding: 40px 32px; }}
  h1 {{ font-size: 18pt; text-align: center; margin-bottom: 4px; letter-spacing: 1px; }}
  .target {{ text-align: center; font-style: italic; color: #666; font-size: 10pt; margin-bottom: 16px; }}
  hr {{ border: none; border-top: 1px solid #ccc; margin: 16px 0; }}
  h2 {{ font-size: 13pt; border-bottom: 1px solid #999; padding-bottom: 2px; margin: 20px 0 8px; }}
  h3 {{ font-size: 11pt; margin: 12px 0 4px; }}
  ul {{ margin-left: 18px; margin-bottom: 8px; }}
  li {{ margin-bottom: 3px; }}
  p {{ margin-bottom: 6px; }}
  .skills-footer {{ font-size: 9.5pt; color: #444; margin-top: 20px; padding-top: 12px; border-top: 1px solid #ddd; }}
  .generated {{ text-align: center; font-size: 8pt; color: #999; margin-top: 24px; font-style: italic; }}
</style>
</head>
<body>
  <h1>{name.upper()}</h1>
  <p class="target">Targeting: {title} at {company}</p>
  <hr>
  {content}
  {f'<div class="skills-footer"><strong>Core Competencies:</strong> {skills_html}</div>' if skills_html else ''}
  <p class="generated">ATS-Optimized Resume</p>
</body>
</html>"""


def _render_premium_html(
    content: str, name: str, title: str, company: str,
    score: int, skills_matched: list, skills_missing: list
) -> str:
    """Premium styled HTML — gradient header, skill badges, score indicator."""
    matched_badges = "".join(
        f'<span class="badge matched">{s}</span>' for s in (skills_matched or [])[:20]
    )
    missing_badges = "".join(
        f'<span class="badge missing">{s}</span>' for s in (skills_missing or [])[:10]
    )
    score_color = "#10b981" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Premium CV for {title}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 10.5pt; color: #1e293b; line-height: 1.6;
    max-width: 900px; margin: 0 auto; padding: 0;
    background: #f8fafc;
  }}
  .header {{
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0ea5e9 100%);
    color: white; padding: 40px 48px 32px; border-radius: 0 0 16px 16px;
    position: relative; overflow: hidden;
  }}
  .header::before {{
    content: ''; position: absolute; top: -50%; right: -20%;
    width: 400px; height: 400px; border-radius: 50%;
    background: rgba(255,255,255,0.03);
  }}
  .header h1 {{ font-size: 28pt; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 4px; position: relative; }}
  .header .subtitle {{
    font-size: 11pt; font-weight: 300; opacity: 0.85; position: relative;
  }}
  .score-badge {{
    position: absolute; top: 32px; right: 48px;
    width: 64px; height: 64px; border-radius: 50%;
    background: {score_color}; color: white;
    display: flex; align-items: center; justify-content: center;
    font-size: 18pt; font-weight: 700;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  }}
  .main {{ padding: 32px 48px; }}
  h2 {{
    font-size: 13pt; font-weight: 600; color: #0f172a;
    border-bottom: 2px solid #0ea5e9; padding-bottom: 4px;
    margin: 28px 0 12px; text-transform: uppercase; letter-spacing: 0.5px;
  }}
  h3 {{ font-size: 11pt; font-weight: 600; color: #334155; margin: 16px 0 6px; }}
  p {{ margin-bottom: 8px; color: #334155; }}
  ul {{ margin-left: 20px; margin-bottom: 10px; }}
  li {{ margin-bottom: 4px; color: #475569; }}
  li::marker {{ color: #0ea5e9; }}
  strong {{ color: #0f172a; }}
  em {{ color: #64748b; }}
  .skills-section {{
    margin-top: 28px; padding: 20px 24px;
    background: #f1f5f9; border-radius: 12px;
    border: 1px solid #e2e8f0;
  }}
  .skills-section h3 {{
    font-size: 10pt; text-transform: uppercase; letter-spacing: 1px;
    color: #64748b; margin: 0 0 10px; font-weight: 600;
  }}
  .badge {{
    display: inline-block; padding: 3px 10px; margin: 3px 4px;
    border-radius: 20px; font-size: 8.5pt; font-weight: 500;
  }}
  .badge.matched {{
    background: #dcfce7; color: #166534; border: 1px solid #86efac;
  }}
  .badge.missing {{
    background: #fef2f2; color: #991b1b; border: 1px solid #fca5a5;
  }}
  .footer {{
    text-align: center; padding: 20px 48px;
    font-size: 8pt; color: #94a3b8; font-style: italic;
    border-top: 1px solid #e2e8f0; margin-top: 32px;
  }}
  @media print {{
    body {{ background: white; }}
    .header {{ border-radius: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .score-badge {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>{name}</h1>
    <p class="subtitle">Targeting: {title} at {company}</p>
    <div class="score-badge">{score}</div>
  </div>

  <div class="main">
    {content}

    <div class="skills-section">
      <h3>✅ Skills Matched</h3>
      {matched_badges or '<span style="color:#94a3b8;font-size:9pt">Run AI scoring first to see matched skills</span>'}
    </div>
    {f'''
    <div class="skills-section" style="margin-top:12px; background:#fef2f2; border-color:#fecaca;">
      <h3>⚠️ Skills to Develop</h3>
      {missing_badges}
    </div>
    ''' if missing_badges else ''}
  </div>

  <div class="footer">
    Premium AI-Enhanced Resume &middot; Tailored for {title} at {company}
  </div>
</body>
</html>"""

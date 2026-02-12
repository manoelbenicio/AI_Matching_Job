"""CV enhancement routes — Gemini AI integration."""

import json
import os
import difflib
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from ..db import db

router = APIRouter()

# ── Resume loader (reads from candidate_resume.txt or DB) ──────────────────
_resume_cache: str | None = None


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

    _resume_cache = "(No resume configured — place your CV in backend/candidate_resume.txt)"
    return _resume_cache


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


def _call_gemini(resume_text: str, job_title: str, company: str, description: str) -> dict:
    """Call Gemini 2.0 Flash to enhance the resume and return structured JSON."""
    import google.generativeai as genai

    from .settings import get_api_key
    api_key = get_api_key("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not configured. Set it in Settings or .env file."
        )

    genai.configure(api_key=api_key)

    prompt = f"""You are an elite executive resume writer. Analyze the candidate's resume against the target job and produce a JSON response.

TARGET POSITION:
Company: {company}
Title: {job_title}
Job Description:
{description[:4000]}

CANDIDATE'S RESUME:
{resume_text}

INSTRUCTIONS:
1. Rewrite the resume tailored to this specific role — use EXACT keywords from the job posting.
2. Quantify achievements wherever possible.
3. Identify skills from the job description that match the candidate's experience.
4. Identify skills/requirements that the candidate appears to be missing.
5. Score the candidate's fit for the role from 0 to 100.

You MUST respond with ONLY valid JSON (no markdown, no code fences) matching this exact schema:
{{
  "enhanced_cv": "The full rewritten resume text tailored to this role",
  "skills_matched": ["skill1", "skill2", ...],
  "skills_missing": ["skill1", "skill2", ...],
  "fit_score": 85
}}

CRITICAL: Output ONLY the JSON object. No explanation, no markdown formatting."""

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=4000,
            response_mime_type="application/json",
        ),
        safety_settings=safety_settings,
    )

    text = response.text.strip()
    # Gemini sometimes wraps in code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Gemini returned invalid JSON.")


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
            "SELECT id, job_title, company_name, job_description FROM jobs WHERE id = %s",
            [body.job_id],
        )
        job = cur.fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    resume = body.resume_text or _get_resume()

    # 2. Call Gemini
    ai = _call_gemini(
        resume_text=resume,
        job_title=job["job_title"],
        company=job["company_name"],
        description=job["job_description"] or "",
    )

    enhanced_cv = ai.get("enhanced_cv", "")
    skills_matched = ai.get("skills_matched", [])
    skills_missing = ai.get("skills_missing", [])
    fit_score = ai.get("fit_score")

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
                json.dumps(skills_matched),
                json.dumps(skills_missing),
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
        # JSONB columns come as Python dicts/lists already from psycopg2
        result.append(item)
    return result


# ── Premium Export (ATS-Optimized DOCX) ────────────────────────────────

class PremiumExportRequest(BaseModel):
    job_id: int
    version_id: Optional[int] = None


@router.post("/cv/premium-export")
def premium_export(body: PremiumExportRequest):
    """Generate an ATS-optimized DOCX resume for a job (≥70% score gate)."""
    import io
    from ..services.premium_export import generate_premium_docx

    # 1. Load the job and verify score gate
    with db() as (conn, cur):
        cur.execute(
            "SELECT id, job_title, company_name, score FROM jobs WHERE id = %s",
            [body.job_id],
        )
        job = cur.fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        score = job["score"]
        if score is None or score < 70:
            raise HTTPException(
                status_code=400,
                detail=f"Score ({score or 'N/A'}) is below the 70% threshold for premium export.",
            )

        # 2. Get the latest enhanced CV version
        if body.version_id:
            cur.execute(
                "SELECT enhanced_content, skills_matched, skills_missing FROM cv_versions WHERE id = %s",
                [body.version_id],
            )
        else:
            cur.execute(
                """SELECT enhanced_content, skills_matched, skills_missing
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
        skills_matched = json.loads(skills_matched)
    if isinstance(skills_missing, str):
        skills_missing = json.loads(skills_missing)

    # 3. Generate DOCX
    docx_bytes = generate_premium_docx(
        enhanced_cv_text=version["enhanced_content"],
        job_title=job["job_title"],
        company=job["company_name"],
        candidate_name=candidate_name,
        skills_matched=skills_matched,
        skills_missing=skills_missing,
    )

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
    from ..services.premium_export import generate_premium_docx
    from ..services.drive_service import upload_to_drive

    # Reuse the same data-loading logic
    with db() as (conn, cur):
        cur.execute(
            "SELECT id, job_title, company_name, score FROM jobs WHERE id = %s",
            [body.job_id],
        )
        job = cur.fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if (job["score"] or 0) < 70:
            raise HTTPException(status_code=400, detail="Score below 70% threshold")

        if body.version_id:
            cur.execute(
                "SELECT enhanced_content, skills_matched, skills_missing FROM cv_versions WHERE id = %s",
                [body.version_id],
            )
        else:
            cur.execute(
                """SELECT enhanced_content, skills_matched, skills_missing
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
        skills_matched = json.loads(skills_matched)
    if isinstance(skills_missing, str):
        skills_missing = json.loads(skills_missing)

    docx_bytes = generate_premium_docx(
        enhanced_cv_text=version["enhanced_content"],
        job_title=job["job_title"],
        company=job["company_name"],
        candidate_name=candidate_name,
        skills_matched=skills_matched,
        skills_missing=skills_missing,
    )

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
        # Best-effort: stamp drive_url on the version row
        cur.execute(
            """UPDATE cv_versions SET drive_url = %s
               WHERE job_id = %s
               ORDER BY version_number DESC LIMIT 1""",
            [drive_url, body.job_id],
        )

    return result


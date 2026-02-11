"""CV enhancement routes — Gemini AI integration."""

import json
import os
import difflib
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from ..db import db

router = APIRouter()

# ── Default resume (same content as dashboard.py EMBEDDED_RESUME) ──────────
DEFAULT_RESUME = """Manoel Benicio
São Paulo, Brazil | manoel.benicio@icloud.com | +55 11 99364-4444 | linkedin.com/in/manoel-benicio-filho

Profile
Technology Modernization & Digital Transformation leader with 20+ years delivering enterprise-scale modernization and legacy migration programs. Strong expertise in application modernization, cloud adoption, and emerging technology integration. Proven impact across complex environments, including customer revenue growth (25% to 50.5%), IT cost reduction (37.4%), and system performance improvement (65%). Certified multi-cloud architect with hands-on leadership across AWS, Azure, GCP, and OCI.

Core Competencies
- Digital Transformation Strategy
- Application Modernization & Legacy Migration
- Cloud Adoption & Technology Roadmaps
- Innovation Leadership & Emerging Technologies
- Technical Debt Reduction & Architecture Governance
- Business Case Development & Executive Communication
- Revenue Growth (25% to 50.5%) and Cost Optimization

Experience

Head Strategic Business Development – Apps & Cloud Modernization
Indra-Tech | São Paulo, Brazil | 2023 – Present
- Managed a diverse engineering team delivering projects across Americas and EMEA.
- Developed products and solutions that increased customer revenue from 25% to 50.5% over 2 years.
- Managed annual budget of $200M, driving a 37.4% reduction in IT expenditure.
- Led cloud modernization initiatives, migrating legacy systems to cloud platforms with improved efficiency.

Sr Data & Analytics Practice Manager
Indra-Tech | São Paulo, Brazil | 2023 – Present
- Oversaw large-scale IT projects in the health services sector with timely execution.
- Led cross-functional teams of data engineers delivering data-driven strategies.
- Reduced project completion time by 25% through agile methodologies.
- Implemented data governance frameworks reducing data errors by 25%.

Head Cloud & Data Professional Services
Andela | New York, USA | 2022 – 2023
- Led developers, security, and infrastructure professionals for cloud and data programs.
- Facilitated successful legacy migrations and upgrades across cloud/data platforms.
- Built a culture of ownership, inclusiveness, accountability, and urgency.
- Delivered solutions aligned to well-architected frameworks.

Sr Cloud Operations Manager
Telefonica Tech | São Paulo, Brazil | 2021 – 2022
- Accelerated customers' cloud migration journeys and digital transformation programs.
- Reported directly to the COO, managing transformation initiatives end-to-end.
- Orchestrated cloud infrastructure projects with 30% cost decrease and 65% performance increase.
- Negotiated complex cross-stakeholder issues and drove alignment through consensus.

Head Contracts for Cloud Services
Telefonica Tech | São Paulo, Brazil | 2020 – 2021
- Led major B2B contracts for LATAM region at a global insurance client.
- Enabled the sales team to promote new products and solutions.
- Partnered with operations to migrate on-prem applications to public cloud platforms.
- Managed datacenter teams in Brazil and Miami, overseeing CAPEX/OPEX.

Program Manager – Public Safety
NICE | Dallas, USA | 2016 – 2020
- Led developers, security, and infrastructure professionals in public safety programs.
- Acted as main sponsor managing Business Partner contracts (SLAs, performance, training, delivery).
- Managed partners across US regions delivering professional services.
- Collaborated with engineering and product teams to design and deploy NICE solutions.

Education
- MBA – Solutions Architecture | FIAP | 2020
- Bachelor's – Computer Systems Networking and Telecommunications | 2017

Skills (Technical & Leadership)
- Cloud Platforms: AWS, Azure, GCP, OCI
- Modernization: Legacy migration, application modernization, technical debt reduction
- Governance: Architecture governance, roadmap development, data governance
- Delivery & Ops: Cloud operations, large-scale program leadership, cost optimization
- Business & Leadership: Budget ownership, executive communication, business case development

Certifications
- AWS Solution Architect
- AWS Security Specialty
- Azure Solutions Architect
- Azure Cybersecurity Architect
- Azure Security Engineer
- Azure Database Administrator
- Azure Network Engineer
- Oracle Multi-Cloud Architect
- Google Associate Cloud

Career Goal
To lead enterprise technology modernization initiatives that unlock innovation, reduce technical debt, and position organizations for sustainable competitive advantage.
"""


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

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not configured on the server."
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

    resume = body.resume_text or DEFAULT_RESUME

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

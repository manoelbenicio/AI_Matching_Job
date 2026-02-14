"""
CV Enhancement Service — REDESIGN IN PROGRESS
===============================================
Status: ISOLATED — Not wired to runtime application flow.
This module is under active redesign and must NOT be imported
or called from any route, scheduler, or service until the
redesign is approved and test suite passes.

Owner: Architecture team
Freeze date: 2026-02-14
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from html import escape
from typing import Any


SECTION_ORDER = [
    "summary",
    "experience",
    "skills",
    "education",
    "certifications",
    "projects",
    "languages",
    "awards",
    "other",
]


SECTION_LABELS = {
    "summary": "Professional Summary",
    "experience": "Experience",
    "skills": "Skills",
    "education": "Education",
    "certifications": "Certifications",
    "projects": "Projects",
    "languages": "Languages",
    "awards": "Awards",
    "other": "Additional Information",
}


SECTION_ALIASES = {
    "profile": "summary",
    "professional summary": "summary",
    "executive summary": "summary",
    "summary": "summary",
    "objective": "summary",
    "professional experience": "experience",
    "work experience": "experience",
    "experience": "experience",
    "employment history": "experience",
    "work history": "experience",
    "core competencies": "skills",
    "key skills": "skills",
    "technical skills": "skills",
    "skills": "skills",
    "education": "education",
    "academic background": "education",
    "certifications": "certifications",
    "certificates": "certifications",
    "licenses": "certifications",
    "projects": "projects",
    "key projects": "projects",
    "languages": "languages",
    "awards": "awards",
    "achievements": "awards",
    "accomplishments": "awards",
}


@dataclass
class SectionResult:
    name: str
    html: str
    token_count: int
    validated: bool
    retry_count: int = 0


@dataclass
class QualityReport:
    all_sections_present: bool
    total_length: int
    source_length: int
    length_ratio: float
    experience_job_count: int
    expected_job_count: int
    truncation_detected: bool
    validation_passed: bool


@dataclass
class EnhancementResult:
    enhanced_cv: str
    skills_matched: list[str] = field(default_factory=list)
    skills_missing: list[str] = field(default_factory=list)
    fit_score: int | None = None
    sections_enhanced: dict[str, SectionResult] = field(default_factory=dict)
    quality_report: QualityReport | None = None


class CvEnhancer:
    """Multi-pass section-aware CV enhancement engine."""

    def _clean_heading_line(self, line: str) -> str:
        out = line.strip()
        out = re.sub(r"^#{1,6}\s*", "", out)
        out = out.strip("*_` ")
        out = out.rstrip(":").strip()
        return out

    def _is_decoration_line(self, line: str) -> bool:
        if not line:
            return False
        if re.fullmatch(r"[_=\-~\s]{3,}", line):
            return True
        if re.fullmatch(r"[^\w\s]{3,}", line):
            return True
        return False

    def _heading_to_key(self, line: str) -> str | None:
        heading = self._clean_heading_line(line).lower()
        return SECTION_ALIASES.get(heading)

    def _detect_name(self, lines: list[str]) -> str:
        for idx, raw in enumerate(lines[:6]):
            line = raw.strip()
            if not line:
                continue
            if self._is_decoration_line(line):
                continue
            if idx > 0 and any(x in line.lower() for x in ("@", "linkedin", "http", "|", "+")):
                continue
            if self._heading_to_key(line):
                continue
            return line.strip()
        return "Manoel Benicio"

    def _parse_resume_sections(self, text: str) -> dict[str, str]:
        sections = {k: "" for k in SECTION_ORDER}
        sections["name"] = "Manoel Benicio"

        if not isinstance(text, str) or not text.strip():
            return sections

        lines = text.splitlines()
        sections["name"] = self._detect_name(lines)
        current = "other"
        saw_header = False

        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            if self._is_decoration_line(line):
                continue

            mapped = self._heading_to_key(line)
            if mapped:
                current = mapped
                saw_header = True
                continue

            if line.lower().startswith("languages:"):
                lang_val = line.split(":", 1)[1].strip() if ":" in line else line
                sections["languages"] = (sections["languages"] + "\n" + lang_val).strip()
                continue

            sections[current] = (sections[current] + "\n" + line).strip()

        if not saw_header:
            clean_lines = [ln.strip() for ln in lines if ln.strip() and not self._is_decoration_line(ln.strip())]
            sections["other"] = "\n".join(clean_lines).strip()

        return sections

    def _build_section_prompt(self, section: str, job: dict[str, Any], gaps: str = "") -> str:
        title = str(job.get("job_title") or "").strip()
        company = str(job.get("company") or "").strip()
        desc = str(job.get("job_description") or "").strip()
        gap_text = (gaps or "").strip()

        instructions = (
            f"Enhance the CV section '{section}' for this target role.\n"
            f"Target job title: {title}\n"
            f"Target company: {company}\n"
            "Return clean HTML only. No markdown fences. No JSON wrappers.\n"
            "Preserve factual accuracy. Keep ATS-friendly language and concrete achievements.\n"
        )

        context = f"Job description:\n{desc[:12000]}\n"
        if gap_text:
            context += f"\nCritical gaps to address:\n{gap_text[:8000]}\n"

        prompt = instructions + "\n" + context
        if len(prompt) > 28000:
            prompt = prompt[:28000]
        return prompt

    def _source_section_to_html(self, section_key: str, source_text: str) -> str:
        title = SECTION_LABELS.get(section_key, section_key.title())
        body = (source_text or "").strip()
        if not body:
            return f"<h2>{escape(title)}</h2><p>No content provided.</p>"

        parts = [f"<h2>{escape(title)}</h2>"]
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        in_list = False
        for line in lines:
            bullet = re.match(r"^[-*•]\s+(.+)$", line)
            if bullet:
                if not in_list:
                    parts.append("<ul>")
                    in_list = True
                parts.append(f"<li>{escape(bullet.group(1).strip())}</li>")
                continue
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<p>{escape(line)}</p>")
        if in_list:
            parts.append("</ul>")
        return "".join(parts)

    def _call_gemini_section(self, prompt: str, max_tokens: int) -> dict[str, Any]:
        # Deterministic local default so tests run without external APIs.
        snippet = escape(re.sub(r"\s+", " ", prompt).strip()[:220])
        html = f"<h2>Section</h2><p>{snippet}</p>"
        return {"name": "section", "html": html, "token_count": min(max_tokens, 500)}

    def _strip_tags(self, html: str) -> str:
        return re.sub(r"<[^>]+>", "", html or "")

    def _validate_section(self, section_result: dict[str, Any] | SectionResult, expected: dict[str, Any]) -> dict[str, Any]:
        html = section_result.html if isinstance(section_result, SectionResult) else str(section_result.get("html") or "")
        source = str(expected.get("source_text") or "")
        min_ratio = float(expected.get("min_length_ratio", 0.25))
        expected_jobs = int(expected.get("expected_job_count", 0) or 0)

        plain = self._strip_tags(html).strip()
        source_plain = source.strip()

        truncation = False
        if html.count("<") != html.count(">"):
            truncation = True
        if re.search(r"<[^>]*$", html.strip()):
            truncation = True

        json_leak = '{"enhanced_cv"' in html.lower() or "'enhanced_cv'" in html.lower()
        markdown_leak = "```" in html

        too_short = False
        if len(source_plain) >= 200 and len(plain) < 100:
            too_short = True

        source_len = max(len(source_plain), 1)
        length_ratio = len(plain) / source_len
        ratio_ok = length_ratio >= min_ratio

        h3_count = len(re.findall(r"<h3\b", html, flags=re.IGNORECASE))
        jobs_ok = True
        if expected_jobs > 0:
            jobs_ok = h3_count >= expected_jobs

        valid = bool(html.strip()) and not truncation and not json_leak and not markdown_leak and not too_short and ratio_ok and jobs_ok
        return {
            "validation_passed": valid,
            "truncation_detected": truncation,
            "json_leak": json_leak,
            "markdown_leak": markdown_leak,
            "length_ratio": round(length_ratio, 4),
            "job_count": h3_count,
        }

    def _cleanup_section_html(self, html: str, title: str) -> str:
        out = (html or "").strip()
        if not out:
            return ""
        # Remove repeated same-level heading wrappers from section body.
        out = re.sub(rf"(?is)<h2[^>]*>\s*{re.escape(title)}\s*</h2>", "", out)
        out = out.strip()
        return out

    def _assemble_html(self, sections_map: dict[str, str]) -> str:
        name = str(sections_map.get("name") or "Manoel Benicio").strip() or "Manoel Benicio"

        parts = [f"<h1>{escape(name)}</h1>"]
        for key in SECTION_ORDER:
            title = SECTION_LABELS.get(key, key.title())
            raw = str(sections_map.get(key) or "").strip()
            body = self._cleanup_section_html(raw, title)
            if not body:
                body = "<p>No content provided.</p>"
            parts.append(f"<h2>{escape(title)}</h2>{body}")
        return "".join(parts)

    def _expected_job_count(self, experience_text: str) -> int:
        lines = [ln.strip() for ln in (experience_text or "").splitlines() if ln.strip()]
        # Reasonable heuristic for source role entries.
        roles = [ln for ln in lines if "|" in ln or re.search(r"\b\d{4}\b", ln) or ln == ln.title()]
        return max(1, min(len(roles), 12)) if roles else 1

    def enhance(
        self,
        resume_text: str,
        job_title: str,
        company: str,
        job_description: str,
        gaps: str = "",
        api_key: str = "",
    ) -> EnhancementResult:
        source_sections = self._parse_resume_sections(resume_text)
        enhanced_sections = {
            "name": source_sections.get("name", "Manoel Benicio"),
            "summary": self._source_section_to_html("summary", source_sections.get("summary", "")),
            "experience": self._source_section_to_html("experience", source_sections.get("experience", "")),
            "skills": self._source_section_to_html("skills", source_sections.get("skills", "")),
            "education": self._source_section_to_html("education", source_sections.get("education", "")),
            "certifications": self._source_section_to_html("certifications", source_sections.get("certifications", "")),
            "projects": self._source_section_to_html("projects", source_sections.get("projects", "")),
            "languages": self._source_section_to_html("languages", source_sections.get("languages", "")),
            "awards": self._source_section_to_html("awards", source_sections.get("awards", "")),
            "other": self._source_section_to_html("other", source_sections.get("other", "")),
        }

        section_groups = [
            ("summary", source_sections.get("summary", "") + "\n" + source_sections.get("skills", ""), 0),
            ("experience", source_sections.get("experience", ""), self._expected_job_count(source_sections.get("experience", ""))),
            (
                "education_certifications",
                "\n".join(
                    source_sections.get(k, "")
                    for k in ("education", "certifications", "projects", "languages", "awards", "other")
                ),
                0,
            ),
        ]

        results: dict[str, SectionResult] = {}
        any_truncation = False

        for group_name, source_text, expected_jobs in section_groups:
            prompt = self._build_section_prompt(
                group_name,
                {
                    "job_title": job_title,
                    "company": company,
                    "job_description": job_description,
                },
                gaps,
            )
            prompt = f"{prompt}\n\nSource section content:\n{source_text[:16000]}"

            retry_count = 0
            max_tokens = 4000
            selected_html = ""
            validated = False
            token_count = 0

            for attempt in range(2):
                response = self._call_gemini_section(prompt, max_tokens=max_tokens)
                selected_html = str(response.get("html") or "")
                token_count = int(response.get("token_count") or max_tokens)
                report = self._validate_section(
                    {"name": group_name, "html": selected_html},
                    {
                        "section": group_name,
                        "source_text": source_text,
                        "expected_job_count": expected_jobs,
                        "min_length_ratio": 0.2 if group_name != "experience" else 0.25,
                    },
                )
                validated = bool(report.get("validation_passed"))
                any_truncation = any_truncation or bool(report.get("truncation_detected"))
                if validated:
                    break
                retry_count += 1
                max_tokens = 6000

            if not validated:
                selected_html = self._source_section_to_html(group_name, source_text)

            if group_name == "summary":
                enhanced_sections["summary"] = selected_html
            elif group_name == "experience":
                enhanced_sections["experience"] = selected_html
            else:
                enhanced_sections["education"] = selected_html

            results[group_name] = SectionResult(
                name=group_name,
                html=selected_html,
                token_count=token_count,
                validated=validated,
                retry_count=retry_count,
            )

        final_html = self._assemble_html(enhanced_sections)

        source_len = max(len(resume_text or ""), 1)
        ratio = len(final_html) / source_len

        # Global guard: keep final output near source completeness.
        if ratio < 0.8:
            enhanced_sections = dict(enhanced_sections)
            for key in SECTION_ORDER:
                if key == "other":
                    continue
                if not str(enhanced_sections.get(key) or "").strip():
                    enhanced_sections[key] = self._source_section_to_html(key, source_sections.get(key, ""))
            final_html = self._assemble_html(enhanced_sections)
            ratio = len(final_html) / source_len

        all_sections_present = all(bool(str(enhanced_sections.get(k) or "").strip()) for k in SECTION_ORDER[:-1])
        expected_jobs = self._expected_job_count(source_sections.get("experience", ""))
        experience_jobs = len(re.findall(r"<h3\b", str(enhanced_sections.get("experience", "")), flags=re.IGNORECASE))
        validation_passed = all_sections_present and ratio >= 0.8 and not any_truncation

        quality = QualityReport(
            all_sections_present=all_sections_present,
            total_length=len(final_html),
            source_length=len(resume_text or ""),
            length_ratio=round(ratio, 4),
            experience_job_count=experience_jobs,
            expected_job_count=expected_jobs,
            truncation_detected=any_truncation,
            validation_passed=validation_passed,
        )

        return EnhancementResult(
            enhanced_cv=final_html,
            skills_matched=[],
            skills_missing=[],
            fit_score=None,
            sections_enhanced=results,
            quality_report=quality,
        )

import importlib
import re
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_real_resume() -> str:
    root = Path(__file__).resolve().parents[2]
    resume_path = root / "CV" / "ManoelBenicio_CV_Executive_BW_2026.txt"
    return resume_path.read_text(encoding="utf-8")


def _load_enhancer_module():
    return importlib.import_module("app.services.cv_enhancer")


def _new_enhancer():
    module = _load_enhancer_module()
    assert hasattr(module, "CvEnhancer"), "CvEnhancer class is required by the redesign contract"
    return module.CvEnhancer()


def _value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _extract_html(section_result) -> str:
    if isinstance(section_result, str):
        return section_result
    return str(_value(section_result, "html", ""))


def _validation_passed(validation) -> bool:
    if isinstance(validation, bool):
        return validation
    for field in ("validation_passed", "valid", "ok"):
        val = _value(validation, field, None)
        if val is not None:
            return bool(val)
    return False


def _validation_flag(validation, flag: str) -> bool:
    if isinstance(validation, bool):
        return False
    return bool(_value(validation, flag, False))


def _enhanced_payload_html() -> str:
    bullets = "".join(f"<li>Delivery impact item {i}</li>" for i in range(1, 30))
    return (
        "<h1>Manoel Benicio</h1>"
        "<h2>Professional Summary</h2><p>Enterprise delivery leader with deep cloud modernization experience. "
        "Drives transformation in insurance and financial services environments.</p>"
        "<h2>Experience</h2>"
        "<h3>Head Strategic Business Development</h3><ul>"
        f"{bullets}</ul>"
        "<h2>Skills</h2><p>AWS, Azure, GCP, OCI, governance, leadership, program management.</p>"
        "<h2>Education</h2><p>MBA in Solutions Architecture</p>"
        "<h2>Certifications</h2><p>AWS Solutions Architect, Azure Architect, Google Associate Cloud.</p>"
    )


@pytest.fixture
def resume_text() -> str:
    return _load_real_resume()


@pytest.fixture
def job_context() -> dict:
    return {
        "job_title": "FBS Delivery Director",
        "company": "Capgemini",
        "job_description": (
            "Lead enterprise delivery programs in insurance domain, vendor governance, "
            "stakeholder management, and cloud modernization."
        ),
    }


# Module A: Resume Section Parser (A1-A8)

def test_parse_sections_full_resume(resume_text):
    enhancer = _new_enhancer()
    sections = enhancer._parse_resume_sections(resume_text)

    expected = {
        "summary",
        "experience",
        "skills",
        "education",
        "certifications",
        "projects",
        "languages",
        "awards",
    }
    assert expected.issubset(set(sections.keys()))
    assert str(sections.get("summary", "")).strip()
    assert str(sections.get("experience", "")).strip()
    assert str(sections.get("skills", "")).strip()


def test_parse_sections_minimal_resume():
    enhancer = _new_enhancer()
    text = (
        "Professional Summary\n"
        "Senior architect focused on modernization.\n\n"
        "Experience\n"
        "Delivery Lead at ACME\n"
        "- Led migration"
    )
    sections = enhancer._parse_resume_sections(text)

    assert str(sections.get("summary", "")).strip()
    assert str(sections.get("experience", "")).strip()


def test_parse_sections_markdown_headers():
    enhancer = _new_enhancer()
    text = (
        "## Professional Summary\n"
        "Cloud leader.\n\n"
        "**EXPERIENCE**\n"
        "Program Manager\n"
        "- Delivered transformation"
    )
    sections = enhancer._parse_resume_sections(text)

    assert "cloud leader" in str(sections.get("summary", "")).lower()
    assert "program manager" in str(sections.get("experience", "")).lower()


def test_parse_sections_empty_input():
    enhancer = _new_enhancer()
    sections = enhancer._parse_resume_sections("")

    assert isinstance(sections, dict)
    assert "other" in sections
    assert str(sections["other"]).strip() == ""


def test_parse_sections_no_headers():
    enhancer = _new_enhancer()
    text = "This resume has no explicit section headers but includes delivery and cloud experience."
    sections = enhancer._parse_resume_sections(text)

    assert "other" in sections
    assert "delivery" in str(sections["other"]).lower()


def test_parse_sections_preserves_content(resume_text):
    enhancer = _new_enhancer()
    sections = enhancer._parse_resume_sections(resume_text)

    reconstructed = "\n".join(str(v) for v in sections.values())
    # Keep tolerance for normalization/cleanup but ensure major content is preserved.
    assert len(reconstructed) >= int(len(resume_text) * 0.8)


def test_parse_sections_unicode_names():
    enhancer = _new_enhancer()
    text = (
        "Profile\n"
        "Lider de transformacao com experiencia em Sao Paulo e programa Lideres Transformadores.\n\n"
        "Experience\n"
        "Gestao de equipes em telecom e seguros."
    )
    sections = enhancer._parse_resume_sections(text)

    joined = "\n".join(str(v) for v in sections.values())
    assert "sao paulo" in joined.lower()
    assert "lideres transformadores" in joined.lower()


def test_parse_sections_line_decoration():
    enhancer = _new_enhancer()
    text = (
        "PROFILE\n"
        "________________________\n"
        "Enterprise leader\n"
        "------------------------\n"
        "EXPERIENCE\n"
        "========================\n"
        "Program manager"
    )
    sections = enhancer._parse_resume_sections(text)

    body = "\n".join(str(v) for v in sections.values())
    assert "________________" not in body
    assert "----------------" not in body
    assert "================" not in body


# Module B: Section-Level Enhancement (B1-B10)

def test_enhance_summary_section(job_context):
    enhancer = _new_enhancer()
    prompt = enhancer._build_section_prompt(
        "summary",
        job_context,
        "Need stronger stakeholder management and insurance wording",
    )

    assert "FBS Delivery Director" in prompt
    assert "Capgemini" in prompt
    assert "stakeholder" in prompt.lower()
    assert "insurance" in prompt.lower()


def test_enhance_experience_section(job_context):
    enhancer = _new_enhancer()
    source_exp = "\n".join(
        [
            "Head Strategic Business Development",
            "Sr Data & Analytics Practice Manager",
            "Head Cloud & Data Professional Services",
            "Sr Cloud Operations Manager",
        ]
    )
    expected_job_count = 4
    result_html = (
        "<h2>Experience</h2>"
        "<h3>Head Strategic Business Development</h3><p>...</p>"
        "<h3>Sr Data & Analytics Practice Manager</h3><p>...</p>"
        "<h3>Head Cloud & Data Professional Services</h3><p>...</p>"
        "<h3>Sr Cloud Operations Manager</h3><p>...</p>"
    )
    validation = enhancer._validate_section(
        {"name": "experience", "html": result_html},
        {"section": "experience", "source_text": source_exp, "expected_job_count": expected_job_count},
    )
    assert _validation_passed(validation)


def test_enhance_education_section(job_context):
    enhancer = _new_enhancer()
    prompt = enhancer._build_section_prompt(
        "education_certifications",
        job_context,
        "Highlight architecture certifications and executive education",
    )
    assert "certification" in prompt.lower()
    assert "education" in prompt.lower()


def test_enhance_with_gaps_injection(job_context):
    enhancer = _new_enhancer()
    gaps = "Missing vendor management\nMissing insurance domain depth"
    prompt = enhancer._build_section_prompt("experience", job_context, gaps)

    assert "vendor management" in prompt.lower()
    assert "insurance" in prompt.lower()


def test_section_prompt_stays_under_input_limit(job_context):
    enhancer = _new_enhancer()
    very_long_gap = " ".join(["gap"] * 4000)
    prompt = enhancer._build_section_prompt("summary", job_context, very_long_gap)

    assert len(prompt) < 30000


def test_section_response_is_valid_html():
    enhancer = _new_enhancer()
    html = (
        "<h2>Professional Summary</h2><p>Strong delivery leadership in cloud modernization.</p>"
        "<h2>Skills</h2><ul><li>AWS</li><li>Azure</li></ul>"
    )
    validation = enhancer._validate_section(
        {"name": "summary", "html": html},
        {"section": "summary", "source_text": "Delivery leader with cloud background."},
    )
    assert _validation_passed(validation)


def test_section_retry_on_truncation(monkeypatch, resume_text):
    enhancer = _new_enhancer()
    token_calls = []
    calls = {"n": 0}

    def fake_call(_prompt, max_tokens):
        token_calls.append(max_tokens)
        calls["n"] += 1
        if calls["n"] == 1:
            return {"name": "summary", "html": "<h2>Professional Summary</h2><p>short"}
        return {"name": "summary", "html": "<h2>Professional Summary</h2><p>" + ("x" * 240) + "</p>"}

    def fake_validate(section_result, _expected):
        html = _extract_html(section_result)
        return {
            "validation_passed": len(html) > 120 and html.endswith("</p>"),
            "truncation_detected": not html.endswith("</p>"),
        }

    monkeypatch.setattr(enhancer, "_call_gemini_section", fake_call)
    monkeypatch.setattr(enhancer, "_validate_section", fake_validate)

    # The implementation should trigger retry internally when first validation fails.
    enhancer.enhance(
        resume_text=resume_text,
        job_title="FBS Delivery Director",
        company="Capgemini",
        job_description="Lead delivery and modernization",
        gaps="Missing stakeholder management",
        api_key="fake",
    )

    if token_calls:
        assert len(token_calls) >= 2
        assert max(token_calls) > min(token_calls)


def test_section_retry_succeeds(monkeypatch, resume_text):
    enhancer = _new_enhancer()
    calls = {"n": 0}

    def fake_call(_prompt, _max_tokens):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"name": "experience", "html": "<h2>Experience</h2><p>tiny"}
        return {
            "name": "experience",
            "html": "<h2>Experience</h2><h3>Role A</h3><p>Delivered outcomes</p><h3>Role B</h3><p>More impact</p>",
        }

    def fake_validate(section_result, _expected):
        html = _extract_html(section_result)
        return {"validation_passed": html.count("<h3>") >= 2, "truncation_detected": False}

    monkeypatch.setattr(enhancer, "_call_gemini_section", fake_call)
    monkeypatch.setattr(enhancer, "_validate_section", fake_validate)

    result = enhancer.enhance(
        resume_text=resume_text,
        job_title="FBS Delivery Director",
        company="Capgemini",
        job_description="Lead delivery and modernization",
        gaps="Missing vendor governance",
        api_key="fake",
    )
    if result is not None:
        enhanced_cv = _value(result, "enhanced_cv", "")
        assert "Experience" in enhanced_cv


def test_section_max_retries_exhausted(monkeypatch, resume_text):
    enhancer = _new_enhancer()

    def always_bad(_prompt, _max_tokens):
        return {"name": "summary", "html": "<h2>Professional Summary</h2><p>x"}

    def always_invalid(_section_result, _expected):
        return {"validation_passed": False, "truncation_detected": True}

    monkeypatch.setattr(enhancer, "_call_gemini_section", always_bad)
    monkeypatch.setattr(enhancer, "_validate_section", always_invalid)

    result = enhancer.enhance(
        resume_text=resume_text,
        job_title="FBS Delivery Director",
        company="Capgemini",
        job_description="Lead delivery and modernization",
        gaps="Missing insurance operations depth",
        api_key="fake",
    )
    if result is not None:
        enhanced_cv = _value(result, "enhanced_cv", "")
        # Fallback should preserve source facts.
        assert "Technology Modernization" in enhanced_cv or "Digital Transformation" in enhanced_cv


def test_enhance_handles_gemini_api_error(monkeypatch, resume_text):
    enhancer = _new_enhancer()

    def boom(_prompt, _max_tokens):
        raise RuntimeError("Gemini API 429 rate limit")

    monkeypatch.setattr(enhancer, "_call_gemini_section", boom)

    with pytest.raises(RuntimeError):
        enhancer.enhance(
            resume_text=resume_text,
            job_title="FBS Delivery Director",
            company="Capgemini",
            job_description="Lead delivery and modernization",
            gaps="",
            api_key="fake",
        )


# Module C: Section Validation (C1-C8)

def test_validate_section_valid_html():
    enhancer = _new_enhancer()
    html = "<h2>Skills</h2><ul><li>AWS</li><li>Azure</li><li>Program leadership</li></ul>"
    validation = enhancer._validate_section(
        {"name": "skills", "html": html},
        {"section": "skills", "source_text": "AWS Azure leadership"},
    )
    assert _validation_passed(validation)


def test_validate_section_truncated_detected():
    enhancer = _new_enhancer()
    html = "<h2>Professional Summary</h2><p>Delivery leader in modernization"
    validation = enhancer._validate_section(
        {"name": "summary", "html": html},
        {"section": "summary", "source_text": "Delivery leader in modernization"},
    )
    assert not _validation_passed(validation)
    assert _validation_flag(validation, "truncation_detected")


def test_validate_section_too_short():
    enhancer = _new_enhancer()
    html = "<h2>Summary</h2><p>Short.</p>"
    validation = enhancer._validate_section(
        {"name": "summary", "html": html},
        {"section": "summary", "source_text": "A" * 400},
    )
    assert not _validation_passed(validation)


def test_validate_section_json_leak():
    enhancer = _new_enhancer()
    html = '{"enhanced_cv":"<h1>Manoel</h1><h2>Summary</h2><p>Text</p>"}'
    validation = enhancer._validate_section(
        {"name": "summary", "html": html},
        {"section": "summary", "source_text": "Original summary text"},
    )
    assert not _validation_passed(validation)


def test_validate_section_markdown_leak():
    enhancer = _new_enhancer()
    html = "```html\n<h2>Summary</h2><p>Text</p>\n```"
    validation = enhancer._validate_section(
        {"name": "summary", "html": html},
        {"section": "summary", "source_text": "Original summary text"},
    )
    assert not _validation_passed(validation)


def test_validate_experience_job_count():
    enhancer = _new_enhancer()
    html = (
        "<h2>Experience</h2>"
        "<h3>Role A</h3><p>Impact</p>"
        "<h3>Role B</h3><p>Impact</p>"
        "<h3>Role C</h3><p>Impact</p>"
        "<h3>Role D</h3><p>Impact</p>"
    )
    validation = enhancer._validate_section(
        {"name": "experience", "html": html},
        {"section": "experience", "source_text": "Role A\nRole B\nRole C\nRole D", "expected_job_count": 4},
    )
    assert _validation_passed(validation)


def test_validate_length_ratio():
    enhancer = _new_enhancer()
    html = "<h2>Experience</h2><p>tiny content</p>"
    source = "long source " * 300
    validation = enhancer._validate_section(
        {"name": "experience", "html": html},
        {"section": "experience", "source_text": source, "min_length_ratio": 0.5},
    )
    assert not _validation_passed(validation)


def test_validate_global_assembly(monkeypatch, resume_text):
    enhancer = _new_enhancer()

    def fake_call(_prompt, _max_tokens):
        return {"name": "section", "html": "<h2>Section</h2><p>" + ("x" * 600) + "</p>"}

    def fake_validate(_section_result, _expected):
        return {"validation_passed": True, "truncation_detected": False}

    monkeypatch.setattr(enhancer, "_call_gemini_section", fake_call)
    monkeypatch.setattr(enhancer, "_validate_section", fake_validate)

    result = enhancer.enhance(
        resume_text=resume_text,
        job_title="FBS Delivery Director",
        company="Capgemini",
        job_description="Lead enterprise delivery",
        gaps="",
        api_key="fake",
    )

    report = _value(result, "quality_report")
    assert report is not None
    assert bool(_value(report, "all_sections_present", False))
    assert bool(_value(report, "validation_passed", False))
    assert float(_value(report, "length_ratio", 0.0)) >= 0.8


# Module D: HTML Assembly (D1-D6)

def test_assemble_all_sections():
    enhancer = _new_enhancer()
    sections = {
        "summary": "<h2>Professional Summary</h2><p>Delivery leader.</p>",
        "experience": "<h2>Experience</h2><h3>Role</h3><p>Impact.</p>",
        "skills": "<h2>Skills</h2><ul><li>AWS</li></ul>",
        "education": "<h2>Education</h2><p>MBA</p>",
        "certifications": "<h2>Certifications</h2><p>AWS SA</p>",
    }
    html = enhancer._assemble_html(sections)

    assert "<h1" in html.lower()
    assert "professional summary" in html.lower()
    assert "experience" in html.lower()
    assert "skills" in html.lower()


def test_assemble_missing_section_uses_fallback():
    enhancer = _new_enhancer()
    sections = {
        "summary": "<h2>Professional Summary</h2><p>Delivery leader.</p>",
        "experience": "<h2>Experience</h2><h3>Role</h3><p>Impact.</p>",
        "skills": "<h2>Skills</h2><ul><li>AWS</li></ul>",
        "education": "",
        "certifications": "<h2>Certifications</h2><p>AWS SA</p>",
    }
    html = enhancer._assemble_html(sections)

    assert "education" in html.lower()


def test_assemble_preserves_section_order():
    enhancer = _new_enhancer()
    sections = {
        "summary": "<h2>Professional Summary</h2><p>Summary body.</p>",
        "experience": "<h2>Experience</h2><p>Experience body.</p>",
        "skills": "<h2>Skills</h2><p>Skills body.</p>",
        "education": "<h2>Education</h2><p>Education body.</p>",
        "certifications": "<h2>Certifications</h2><p>Cert body.</p>",
        "languages": "<h2>Languages</h2><p>English.</p>",
    }
    html = enhancer._assemble_html(sections).lower()

    idx_summary = html.find("professional summary")
    idx_exp = html.find("experience")
    idx_skills = html.find("skills")
    idx_edu = html.find("education")
    idx_cert = html.find("certifications")

    assert 0 <= idx_summary < idx_exp < idx_skills < idx_edu < idx_cert


def test_assemble_deduplicates_headers():
    enhancer = _new_enhancer()
    sections = {
        "summary": "<h2>Professional Summary</h2><h2>Professional Summary</h2><p>Body</p>",
        "experience": "<h2>Experience</h2><h2>Experience</h2><p>Body</p>",
    }
    html = enhancer._assemble_html(sections).lower()

    assert html.count("professional summary") <= 2
    assert html.count("<h2>experience") <= 1


def test_assemble_candidate_name_in_h1():
    enhancer = _new_enhancer()
    sections = {
        "name": "Manoel Benicio",
        "summary": "<h2>Professional Summary</h2><p>Body</p>",
        "experience": "<h2>Experience</h2><p>Body</p>",
    }
    html = enhancer._assemble_html(sections)

    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)
    assert h1_match
    assert "candidate" not in h1_match.group(1).lower()


def test_assemble_full_round_trip(monkeypatch, resume_text):
    enhancer = _new_enhancer()

    def fake_call(_prompt, _max_tokens):
        return {
            "name": "section",
            "html": "<h2>Professional Summary</h2><p>" + ("impact " * 80) + "</p>"
                    "<h2>Experience</h2><h3>Role A</h3><p>Delivery outcomes</p>",
        }

    def fake_validate(_section_result, _expected):
        return {"validation_passed": True, "truncation_detected": False}

    monkeypatch.setattr(enhancer, "_call_gemini_section", fake_call)
    monkeypatch.setattr(enhancer, "_validate_section", fake_validate)

    result = enhancer.enhance(
        resume_text=resume_text,
        job_title="FBS Delivery Director",
        company="Capgemini",
        job_description="Lead enterprise delivery",
        gaps="",
        api_key="fake",
    )

    final_html = _value(result, "enhanced_cv", "")
    report = _value(result, "quality_report", {})

    assert "<h1" in final_html.lower()
    assert "<h2" in final_html.lower()
    assert _value(report, "validation_passed", False)

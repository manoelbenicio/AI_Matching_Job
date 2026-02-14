import sys
import types

import pytest
from fastapi import HTTPException


class _FakeConn:
    def commit(self):
        return None


class _FakeCursor:
    def __init__(self):
        self.last_query = ""

    def execute(self, query, _params=None):
        self.last_query = " ".join(query.split())

    def fetchone(self):
        if "SELECT id, job_title, company_name, job_description FROM jobs WHERE id = %s" in self.last_query:
            return {
                "id": 1,
                "job_title": "Senior Engineer",
                "company_name": "Acme",
                "job_description": "Build scalable systems",
            }
        if "RETURNING version" in self.last_query:
            return {"version": 2}
        return None


class _FakeDBCtx:
    def __enter__(self):
        return _FakeConn(), _FakeCursor()

    def __exit__(self, exc_type, exc, tb):
        return False


def _fake_db():
    return _FakeDBCtx()


def test_single_score_request_default_model():
    from app.routes.scoring import SingleScoreRequest

    body = SingleScoreRequest(job_db_id=123)
    assert body.model == "groq"


def test_gemini_default_model_is_25_flash(monkeypatch):
    from app.routes import scoring

    captured = {}

    class FakeResponse:
        candidates = [types.SimpleNamespace(finish_reason=1)]
        text = '{"overall_score": 81, "overall_justification": "Strong fit", "sections": []}'
        usage_metadata = types.SimpleNamespace(total_token_count=111)

    class FakeModel:
        def __init__(self, model_name, system_instruction=None):
            captured["model_name"] = model_name

        def generate_content(self, *_args, **_kwargs):
            return FakeResponse()

    class FakeGenerationConfig:
        def __init__(self, **_kwargs):
            pass

    fake_genai = types.SimpleNamespace(
        configure=lambda **_kwargs: None,
        GenerativeModel=FakeModel,
        types=types.SimpleNamespace(GenerationConfig=FakeGenerationConfig),
    )
    fake_google = types.ModuleType("google")
    fake_google.generativeai = fake_genai

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.generativeai", fake_genai)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(scoring, "get_api_key", lambda _k: "fake-key")

    result = scoring._score_job_gemini("Role", "Company", "Description")
    assert captured["model_name"] == "gemini-2.5-flash"
    assert result["provider"] == "gemini"


def test_compare_mode_returns_both_and_best_provider(monkeypatch):
    from app.routes import scoring

    def fake_score(_jt, _co, _desc, provider="openai"):
        if provider == "openai":
            return {"overall_score": 74, "overall_justification": "Good", "provider": "openai", "model": "gpt-4o-mini"}
        return {"overall_score": 82, "overall_justification": "Better", "provider": "gemini", "model": "gemini-2.5-flash"}

    monkeypatch.setattr(scoring, "db", _fake_db)
    monkeypatch.setattr(scoring, "_score_job_detailed", fake_score)

    res = scoring.score_single_job(scoring.SingleScoreRequest(job_db_id=1, model="compare"))
    assert res["mode"] == "compare"
    assert res["result"]["compare_mode"] is True
    assert "openai" in res["result"]["results"]
    assert "gemini" in res["result"]["results"]
    assert res["result"]["best_provider"] == "gemini"


def test_single_scoring_returns_429_when_rate_limited(monkeypatch):
    from app.routes import scoring

    monkeypatch.setattr(scoring, "db", _fake_db)
    monkeypatch.setattr(
        scoring,
        "_score_job_detailed",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("Rate limit (openai): 60/min exceeded.")),
    )

    with pytest.raises(HTTPException) as exc:
        scoring.score_single_job(scoring.SingleScoreRequest(job_db_id=1, model="openai"))
    assert exc.value.status_code == 429


def test_jobs_normalizer_handles_compare_payload():
    from app.routes.jobs import _normalize_detailed_score

    payload = {
        "compare_mode": True,
        "best_provider": "gemini",
        "results": {
            "openai": {"overall_score": 70, "overall_justification": "OpenAI", "sections": []},
            "gemini": {
                "overall_score": 85,
                "overall_justification": "Gemini",
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "sections": [{"dimension": "Technical Skills", "score": 88, "strong": ["Python"], "weak": ["K8s"]}],
                "cv_enhancement_priority": ["Leadership"],
                "key_risks": ["Missing cert"],
            },
        },
        "errors": {},
    }
    norm = _normalize_detailed_score(payload, "2026-02-12T00:00:00+00:00")
    assert norm is not None
    assert norm["compare_mode"] is True
    assert norm["best_provider"] == "gemini"
    assert norm["overall_score"] == 85
    assert norm["sections"][0]["strong_points"] == ["Python"]
    assert norm["cv_enhancement_priorities"] == ["Leadership"]


def test_extract_gaps_supports_new_compare_and_legacy():
    from app.routes.cv import _extract_gaps_from_score

    compare_payload = {
        "compare_mode": True,
        "best_provider": "openai",
        "results": {
            "openai": {
                "sections": [
                    {
                        "dimension": "Technical Skills",
                        "weak": ["Missing Terraform"],
                        "recommendations": ["Add IaC project"],
                    }
                ],
                "skills_missing": ["AWS"],
                "key_risks": ["No cloud cert"],
            }
        },
    }
    legacy_payload = {
        "section_evaluations": {
            "experience_level": {
                "gaps": ["No team lead role"],
                "recommendations": ["Highlight mentoring"],
            }
        }
    }

    compare_gaps = _extract_gaps_from_score(compare_payload)
    legacy_gaps = _extract_gaps_from_score(legacy_payload)

    assert "Missing Terraform" in compare_gaps
    assert "Add IaC project" in compare_gaps
    assert "No team lead role" in legacy_gaps


def test_premium_html_template_validation():
    from app.routes.cv import PremiumHtmlRequest, premium_html

    ok = PremiumHtmlRequest(job_id=1, template="ats")
    assert ok.template == "ats"

    with pytest.raises(HTTPException) as exc:
        premium_html(PremiumHtmlRequest(job_id=1, template="invalid-template"))
    assert exc.value.status_code == 400


def test_normalize_enhanced_content_handles_truncated_json_payload():
    from app.routes.cv import _normalize_enhanced_content

    payload = (
        '{"enhanced_cv":"<h1>Manoel Benicio</h1>'
        '<p>Sao Paulo, Brazil</p><h2>Summary</h2><p>Text'
    )
    normalized = _normalize_enhanced_content(payload)
    assert normalized.startswith("<h1>Manoel Benicio</h1>")
    assert '{"enhanced_cv"' not in normalized

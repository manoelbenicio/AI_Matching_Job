import os
import uuid

import pytest
from fastapi.testclient import TestClient


def _db_available() -> bool:
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "job_matcher"),
            password=os.getenv("DB_PASSWORD", "JobMatcher2024!"),
            dbname=os.getenv("DB_NAME", "job_matcher"),
            connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Database not reachable")


def _db_connect():
    import psycopg2

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "job_matcher"),
        password=os.getenv("DB_PASSWORD", "JobMatcher2024!"),
        dbname=os.getenv("DB_NAME", "job_matcher"),
    )


def _long_enhanced_html() -> str:
    bullets = "".join(f"<li>Delivery impact item {i}</li>" for i in range(1, 40))
    return (
        "<h1>Manoel Benicio</h1>"
        "<p>Sao Paulo, Brazil | manoel.benicio@icloud.com | +55 11 99364-4444</p>"
        "<h2>Professional Summary</h2>"
        "<p>Technology modernization and digital transformation leader with extensive enterprise delivery experience "
        "across insurance and financial services. Strong focus on stakeholder management, governance, and cloud strategy.</p>"
        "<h2>Experience</h2>"
        "<h3>Head Strategic Business Development - Apps & Cloud Modernization</h3>"
        f"<ul>{bullets}</ul>"
        "<h2>Skills</h2><ul><li>AWS</li><li>Azure</li><li>GCP</li><li>OCI</li><li>Program Management</li></ul>"
        "<h2>Education</h2><p>MBA - Solutions Architecture</p>"
        "<h2>Certifications</h2><p>AWS Solutions Architect, Azure Solutions Architect, Google Associate Cloud</p>"
    )


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


@pytest.fixture
def seeded_job():
    conn = _db_connect()
    conn.autocommit = False
    cur = conn.cursor()

    suffix = uuid.uuid4().hex[:12]
    logical_job_id = f"itg-{suffix}"

    cur.execute(
        """
        INSERT INTO jobs (
            job_id, job_title, company_name, job_description, location,
            employment_type, work_type, seniority_level, status, score,
            created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        RETURNING id
        """,
        [
            logical_job_id,
            "FBS Delivery Director",
            "Capgemini",
            "Lead enterprise delivery in insurance and cloud modernization.",
            "Brazil",
            "full_time",
            "remote",
            "mid_senior",
            "qualified",
            85,
        ],
    )
    job_pk = cur.fetchone()[0]

    cur.execute(
        """
        INSERT INTO candidates (name, email, resume_text, is_active, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        RETURNING id
        """,
        [
            "Manoel Benicio",
            f"manoel+{suffix}@example.com",
            "Sample resume text for integration testing",
            True,
        ],
    )
    cand_pk = cur.fetchone()[0]
    conn.commit()

    try:
        yield {"job_id": job_pk, "candidate_id": cand_pk}
    finally:
        cur.execute("DELETE FROM audit_log WHERE job_id = %s", [job_pk])
        cur.execute("DELETE FROM cv_versions WHERE job_id = %s", [job_pk])
        cur.execute("DELETE FROM jobs WHERE id = %s", [job_pk])
        cur.execute("DELETE FROM candidates WHERE id = %s", [cand_pk])
        conn.commit()
        cur.close()
        conn.close()


def _fake_gemini_response(*_args, **_kwargs):
    return {
        "enhanced_cv": _long_enhanced_html(),
        "skills_matched": ["AWS", "Azure", "Leadership", "Program Management"],
        "skills_missing": ["Insurance claims ops"],
        "fit_score": 91,
    }


# Module G: End-to-End Integration (G1-G5)

def test_enhance_endpoint_returns_complete_cv(client, seeded_job, monkeypatch):
    from app.routes import cv as cv_route

    monkeypatch.setattr(cv_route, "_call_gemini", _fake_gemini_response)

    resp = client.post(
        "/api/cv/enhance",
        json={"job_id": seeded_job["job_id"], "resume_text": "Source resume text for testing."},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) >= {"enhanced_cv", "diff", "version_id", "fit_score", "skills_matched", "skills_missing"}
    assert len(data["enhanced_cv"]) >= 900


def test_enhance_then_premium_export(client, seeded_job, monkeypatch):
    from app.routes import cv as cv_route

    monkeypatch.setattr(cv_route, "_call_gemini", _fake_gemini_response)

    enh = client.post(
        "/api/cv/enhance",
        json={"job_id": seeded_job["job_id"], "resume_text": "Source resume text for testing."},
    )
    assert enh.status_code == 200

    exp = client.post("/api/cv/premium-export", json={"job_id": seeded_job["job_id"]})
    assert exp.status_code == 200
    assert exp.content[:2] == b"PK"


def test_enhance_stores_cv_version(client, seeded_job, monkeypatch):
    from app.routes import cv as cv_route

    monkeypatch.setattr(cv_route, "_call_gemini", _fake_gemini_response)

    resp = client.post(
        "/api/cv/enhance",
        json={"job_id": seeded_job["job_id"], "resume_text": "Source resume text for testing."},
    )
    assert resp.status_code == 200

    conn = _db_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MAX(version_number) FROM cv_versions WHERE job_id = %s", [seeded_job["job_id"]])
    count, max_version = cur.fetchone()
    cur.close()
    conn.close()

    assert count == 1
    assert max_version == 1


def test_enhance_idempotent_versioning(client, seeded_job, monkeypatch):
    from app.routes import cv as cv_route

    monkeypatch.setattr(cv_route, "_call_gemini", _fake_gemini_response)

    first = client.post(
        "/api/cv/enhance",
        json={"job_id": seeded_job["job_id"], "resume_text": "Source resume text for testing."},
    )
    second = client.post(
        "/api/cv/enhance",
        json={"job_id": seeded_job["job_id"], "resume_text": "Source resume text for testing."},
    )

    assert first.status_code == 200
    assert second.status_code == 200

    conn = _db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*), MIN(version_number), MAX(version_number) FROM cv_versions WHERE job_id = %s",
        [seeded_job["job_id"]],
    )
    count, min_ver, max_ver = cur.fetchone()
    cur.close()
    conn.close()

    assert count == 2
    assert min_ver == 1
    assert max_ver == 2


def test_premium_html_renders_enhanced_content(client, seeded_job, monkeypatch):
    from app.routes import cv as cv_route

    monkeypatch.setattr(cv_route, "_call_gemini", _fake_gemini_response)

    enh = client.post(
        "/api/cv/enhance",
        json={"job_id": seeded_job["job_id"], "resume_text": "Source resume text for testing."},
    )
    assert enh.status_code == 200

    html_resp = client.post(
        "/api/cv/premium-html",
        json={"job_id": seeded_job["job_id"], "template": "premium"},
    )
    assert html_resp.status_code == 200

    payload = html_resp.json()
    assert payload["template"] == "premium"
    assert "Manoel Benicio" in payload["html"]
    assert "Professional Summary" in payload["html"]

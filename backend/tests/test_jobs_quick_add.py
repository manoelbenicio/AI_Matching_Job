import pytest
from fastapi import HTTPException

from app.routes.jobs import _normalize_job_url_input


def test_normalize_keeps_direct_url():
    url = "https://www.linkedin.com/jobs/view/4357596542/?trk=public_jobs"
    assert _normalize_job_url_input(url).startswith("https://www.linkedin.com/jobs/view/4357596542")


def test_normalize_extracts_from_encoded_blob():
    raw = "url=https%3A%2F%2Fwww.linkedin.com%2Fjobs%2Fview%2F1234567890%2F%3FtrackingId%3Dabc"
    assert _normalize_job_url_input(raw).startswith("https://www.linkedin.com/jobs/view/1234567890")


def test_normalize_builds_from_current_job_id():
    raw = "trackingId=L%2B4y5TpECDbiAsezGFh7nQ%3D%3D&trk=flagship3_search_srp_jobs&currentJobId=9876543210"
    assert _normalize_job_url_input(raw) == "https://www.linkedin.com/jobs/view/9876543210"


def test_normalize_rejects_invalid_input():
    with pytest.raises(HTTPException) as exc:
        _normalize_job_url_input("%%%")
    assert exc.value.status_code == 400

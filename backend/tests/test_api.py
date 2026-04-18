import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add backend to path so "app" package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "RESULTS")

FAIL_REPORT = os.path.join(RESULTS_DIR, "html_report_3182026_at_154830.html")
PASS_REPORT = os.path.join(RESULTS_DIR, "html_report_3132026_at_114322.html")


@pytest.fixture
def client():
    """Sync test client — no running server needed."""
    return TestClient(app)


# ─── Health ────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ─── Parse: FAIL report ───────────────────────────────────

def test_parse_fail_report(client):
    with open(FAIL_REPORT, "rb") as f:
        resp = client.post("/parse", files={"file": ("report.html", f, "text/html")})

    assert resp.status_code == 200
    data = resp.json()

    assert data["total_tests"] == 1
    assert data["passed"] == 0
    assert data["failed"] == 1

    tc = data["test_cases"][0]
    assert tc["result"] == "FAIL"
    assert tc["test_name"] == "test_case_217_Support_of_audio_formats"
    assert tc["error_message"] is not None
    assert len(tc["steps"]) > 0


# ─── Parse: PASS report ───────────────────────────────────

def test_parse_pass_report(client):
    with open(PASS_REPORT, "rb") as f:
        resp = client.post("/parse", files={"file": ("report.html", f, "text/html")})

    assert resp.status_code == 200
    data = resp.json()

    assert data["total_tests"] >= 1
    assert data["passed"] >= 1
    assert data["failed"] == 0

    tc = data["test_cases"][0]
    assert tc["result"] == "PASS"
    assert tc["error_message"] is None
    assert tc["traceback"] is None


# ─── Parse: unsupported format → 415 ──────────────────────

def test_parse_unsupported_format(client):
    resp = client.post(
        "/parse",
        files={"file": ("report.pdf", b"not a real pdf", "application/pdf")},
    )
    assert resp.status_code == 415
    assert "No parser available" in resp.json()["detail"]


# ─── Parse: non-MTS HTML → 415 ────────────────────────────

def test_parse_non_mts_html(client):
    fake_html = b"<html><body><p>Not a test report</p></body></html>"
    resp = client.post(
        "/parse",
        files={"file": ("page.html", fake_html, "text/html")},
    )
    assert resp.status_code == 415


# ─── Analyze: no API key → 503 ────────────────────────────

def test_analyze_no_api_key(client, monkeypatch):
    monkeypatch.setattr("app.main.settings.llm_api_key", "")
    with open(FAIL_REPORT, "rb") as f:
        resp = client.post("/analyze", files={"file": ("report.html", f, "text/html")})

    assert resp.status_code == 503
    assert "API key" in resp.json()["detail"]


# ─── Parse: traceback extracted ────────────────────────────

def test_parse_extracts_traceback(client):
    with open(FAIL_REPORT, "rb") as f:
        resp = client.post("/parse", files={"file": ("report.html", f, "text/html")})

    tc = resp.json()["test_cases"][0]
    assert tc["traceback"] is not None
    assert "TestStepFail" in tc["traceback"]


# ─── Parse: steps have correct structure ──────────────────

def test_parse_step_structure(client):
    with open(FAIL_REPORT, "rb") as f:
        resp = client.post("/parse", files={"file": ("report.html", f, "text/html")})

    steps = resp.json()["test_cases"][0]["steps"]
    for step in steps:
        assert "step_name" in step
        assert "description" in step
        assert step["result"] in ("PASS", "FAIL", "NOT_PERFORMED", "UNKNOWN")

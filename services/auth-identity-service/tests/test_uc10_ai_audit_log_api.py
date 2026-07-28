"""Integration test UC-10 qua HTTP API, dùng SQLite in-memory (không cần Postgres)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _record(trace_id, username="canbo1", model="gpt-oss-120b", prompt="hỏi gì đó", response="trả lời", **extra):
    payload = {
        "trace_id": trace_id,
        "username": username,
        "model": model,
        "prompt": prompt,
        "response": response,
        **extra,
    }
    return client.post("/ai-audit-logs", json=payload)


def test_list_ai_audit_logs_empty_returns_empty_list():
    resp = client.get("/ai-audit-logs")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_record_and_list_ai_audit_log():
    resp = _record(
        "trace-uc10-001",
        username="canbo1",
        sources=["bao_cao.pdf"],
        permission_snapshot={"sensitivity_level": "INTERNAL"},
        prompt_version="v3",
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["trace_id"] == "trace-uc10-001"
    assert body["sources"] == ["bao_cao.pdf"]
    assert body["permission_snapshot"] == {"sensitivity_level": "INTERNAL"}
    assert body["created_at"] is not None

    listed = client.get("/ai-audit-logs")
    assert listed.status_code == 200
    trace_ids = [e["trace_id"] for e in listed.json()]
    assert "trace-uc10-001" in trace_ids


def test_record_missing_prompt_returns_422():
    resp = client.post(
        "/ai-audit-logs",
        json={"trace_id": "trace-x", "username": "canbo1", "model": "m", "prompt": "", "response": ""},
    )
    assert resp.status_code == 422


def test_filter_ai_audit_logs_by_user_id():
    _record("trace-uc10-002", username="kiemtoan1")
    resp = client.get("/ai-audit-logs", params={"user_id": "kiemtoan1"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) >= 1
    assert all(e["username"] == "kiemtoan1" for e in body)


def test_filter_ai_audit_logs_invalid_time_range_returns_422():
    resp = client.get(
        "/ai-audit-logs", params={"time_from": "2026-12-31", "time_to": "2026-01-01"}
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_AI_AUDIT_LOG_FILTER"


def test_get_ai_audit_log_by_trace_id():
    _record("trace-uc10-003", username="canbo1", prompt="Câu hỏi chi tiết", response="Câu trả lời chi tiết")
    resp = client.get("/ai-audit-logs/trace-uc10-003")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["prompt"] == "Câu hỏi chi tiết"
    assert body["response"] == "Câu trả lời chi tiết"


def test_get_ai_audit_log_by_trace_id_not_found_returns_404():
    resp = client.get("/ai-audit-logs/khong-ton-tai")
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "AI_AUDIT_LOG_NOT_FOUND"


def test_export_periodic_report_week_returns_pdf():
    _record("trace-uc10-004")
    resp = client.get("/ai-audit-logs/export", params={"period": "WEEK"})
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_export_periodic_report_invalid_period_returns_422():
    resp = client.get("/ai-audit-logs/export", params={"period": "YEAR"})
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_AI_AUDIT_LOG_FILTER"
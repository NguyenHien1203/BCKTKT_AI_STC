"""Integration test UC-09 qua HTTP API, dùng SQLite in-memory (không cần Postgres)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _record(username="admin", action="CREATE", resource_type="USER", **extra):
    payload = {"username": username, "action": action, "resource_type": resource_type, **extra}
    return client.post("/audit-logs", json=payload)


def test_list_audit_logs_empty_returns_empty_list():
    resp = client.get("/audit-logs")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_record_and_list_audit_log():
    resp = _record(username="admin", action="CREATE", resource_type="ORG_UNIT", resource_id="1")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["username"] == "admin"
    assert body["action"] == "CREATE"
    assert body["resource_type"] == "ORG_UNIT"
    assert body["status"] == "SUCCESS"
    assert body["created_at"] is not None

    listed = client.get("/audit-logs")
    assert listed.status_code == 200
    usernames = [e["username"] for e in listed.json()]
    assert "admin" in usernames


def test_record_missing_username_returns_422():
    resp = client.post("/audit-logs", json={"username": "", "action": "CREATE", "resource_type": "USER"})
    assert resp.status_code == 422


def test_filter_audit_logs_by_account():
    _record(username="kiemtoan1", action="VIEW", resource_type="AUDIT_LOG")
    resp = client.get("/audit-logs", params={"account": "kiemtoan1"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) >= 1
    assert all(e["username"] == "kiemtoan1" for e in body)


def test_filter_audit_logs_by_time_range_excludes_future_only_window():
    _record(username="admin", action="CREATE", resource_type="USER")
    resp = client.get("/audit-logs", params={"time_from": "2999-01-01T00:00:00+00:00"})
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_filter_audit_logs_invalid_time_range_returns_422():
    resp = client.get(
        "/audit-logs", params={"time_from": "2026-12-31", "time_to": "2026-01-01"}
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_AUDIT_LOG_FILTER"


def test_export_security_report_returns_pdf():
    _record(username="admin", action="CREATE", resource_type="USER")
    resp = client.get("/audit-logs/export")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_export_security_report_invalid_time_range_returns_422():
    resp = client.get(
        "/audit-logs/export", params={"time_from": "2026-12-31", "time_to": "2026-01-01"}
    )
    assert resp.status_code == 422, resp.text
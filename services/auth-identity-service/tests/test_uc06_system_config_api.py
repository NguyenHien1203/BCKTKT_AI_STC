"""Integration test UC-06 qua HTTP API, dùng SQLite in-memory (không cần Postgres)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_get_system_config_returns_defaults_first_time():
    resp = client.get("/system-config")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["request_timeout_seconds"] == 30
    assert body["max_upload_size_mb"] == 50
    assert body["default_language"] == "vi"


def test_update_system_config_applies_immediately():
    resp = client.patch(
        "/system-config",
        json={
            "request_timeout_seconds": 90,
            "max_upload_size_mb": 300,
            "default_language": "en",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["request_timeout_seconds"] == 90
    assert body["max_upload_size_mb"] == 300
    assert body["default_language"] == "en"

    reread = client.get("/system-config")
    assert reread.status_code == 200
    assert reread.json()["default_language"] == "en"


def test_update_system_config_invalid_language_returns_422():
    resp = client.patch(
        "/system-config",
        json={
            "request_timeout_seconds": 30,
            "max_upload_size_mb": 50,
            "default_language": "fr",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_SYSTEM_CONFIG"


def test_update_system_config_out_of_range_timeout_returns_422_schema_validation():
    resp = client.patch(
        "/system-config",
        json={
            "request_timeout_seconds": 0,
            "max_upload_size_mb": 50,
            "default_language": "vi",
        },
    )
    # Vi phạm ràng buộc Pydantic (ge=1) -> FastAPI trả 422 mặc định.
    assert resp.status_code == 422
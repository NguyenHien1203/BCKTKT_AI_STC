"""Integration test UC-017 qua HTTP API, dùng SQLite in-memory."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from datetime import datetime, timedelta, timezone  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_data_source(code="UC17-SRC-01"):
    resp = client.post(
        "/data-sources",
        json={
            "code": code,
            "name": "Nguồn dữ liệu test UC-17",
            "source_system": "TABMIS",
            "provider": "Bộ Tài chính",
            "owner": "Cục CNTT",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _iso_days_from_now(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


# ---------- UC-017 phần 1: cấu hình + kiểm thử kết nối ----------


def test_configure_connection_encrypts_credentials_and_hides_them_in_response():
    data_source_id = _create_data_source("UC17-SRC-CFG")
    resp = client.post(
        "/source-connections",
        json={
            "data_source_id": data_source_id,
            "connection_type": "API",
            "config": {"base_url": "https://api.example.gov.vn"},
            "credentials": {"api_key": "super-secret-key-123"},
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["connection_type"] == "API"
    assert body["config"]["base_url"] == "https://api.example.gov.vn"
    assert body["last_test_status"] == "UNTESTED"
    # Không bao giờ trả về thông tin xác thực (đã mã hoá hay bản rõ) qua API.
    assert "credentials" not in body
    assert "encrypted_credentials" not in body
    assert "api_key" not in str(body)


def test_configure_connection_invalid_data_source_returns_404():
    resp = client.post(
        "/source-connections",
        json={
            "data_source_id": 999999,
            "connection_type": "API",
            "config": {"base_url": "https://x"},
            "credentials": {"api_key": "k"},
        },
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_NOT_FOUND"


def test_configure_connection_invalid_type_returns_422():
    data_source_id = _create_data_source("UC17-SRC-BADTYPE")
    resp = client.post(
        "/source-connections",
        json={
            "data_source_id": data_source_id,
            "connection_type": "FTP",
            "config": {},
            "credentials": {},
        },
    )
    assert resp.status_code == 422


def test_test_connection_success_when_required_fields_present():
    data_source_id = _create_data_source("UC17-SRC-DB")
    create = client.post(
        "/source-connections",
        json={
            "data_source_id": data_source_id,
            "connection_type": "DB",
            "config": {"host": "10.0.0.5", "database": "tabmis"},
            "credentials": {"username": "svc_user", "password": "s3cr3t"},
        },
    ).json()

    resp = client.post(f"/source-connections/{create['id']}/test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["last_test_status"] == "SUCCESS"
    assert body["last_tested_at"] is not None


def test_test_connection_fails_when_missing_credentials():
    data_source_id = _create_data_source("UC17-SRC-DB-NOCRED")
    create = client.post(
        "/source-connections",
        json={
            "data_source_id": data_source_id,
            "connection_type": "DB",
            "config": {"host": "10.0.0.5", "database": "tabmis"},
            "credentials": {},
        },
    ).json()

    resp = client.post(f"/source-connections/{create['id']}/test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["last_test_status"] == "FAILED"
    assert "xác thực" in body["last_test_message"]


def test_test_connection_not_found_returns_404():
    resp = client.post("/source-connections/999999/test")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "SOURCE_CONNECTION_NOT_FOUND"


def test_list_and_filter_connections_by_type():
    data_source_id = _create_data_source("UC17-SRC-FILE")
    client.post(
        "/source-connections",
        json={
            "data_source_id": data_source_id,
            "connection_type": "FILE",
            "config": {"path": "/mnt/sftp/tabmis"},
            "credentials": {},
        },
    )
    resp = client.get("/source-connections", params={"connection_type": "FILE"})
    assert resp.status_code == 200
    assert all(c["connection_type"] == "FILE" for c in resp.json())


def test_update_connection_config_and_credentials():
    data_source_id = _create_data_source("UC17-SRC-UPD")
    create = client.post(
        "/source-connections",
        json={
            "data_source_id": data_source_id,
            "connection_type": "API",
            "config": {"base_url": "https://old.example.com"},
            "credentials": {"api_key": "old-key"},
        },
    ).json()

    resp = client.patch(
        f"/source-connections/{create['id']}",
        json={"config": {"base_url": "https://new.example.com"}, "credentials": {"api_key": "new-key"}},
    )
    assert resp.status_code == 200
    assert resp.json()["config"]["base_url"] == "https://new.example.com"

    # Kiểm thử sau khi cập nhật phải dùng credentials mới (vẫn PASS vì có api_key).
    test_resp = client.post(f"/source-connections/{create['id']}/test")
    assert test_resp.json()["last_test_status"] == "SUCCESS"


def test_deactivate_and_activate_connection():
    data_source_id = _create_data_source("UC17-SRC-DEACT")
    create = client.post(
        "/source-connections",
        json={
            "data_source_id": data_source_id,
            "connection_type": "FILE",
            "config": {"path": "/tmp"},
            "credentials": {},
        },
    ).json()

    resp = client.post(f"/source-connections/{create['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    resp2 = client.post(f"/source-connections/{create['id']}/activate")
    assert resp2.status_code == 200
    assert resp2.json()["is_active"] is True


# ---------- UC-017 phần 2: certificate/API key + lịch luân chuyển + cảnh báo ----------


def _create_connection(code="UC17-SRC-CRED"):
    data_source_id = _create_data_source(code)
    return client.post(
        "/source-connections",
        json={
            "data_source_id": data_source_id,
            "connection_type": "API",
            "config": {"base_url": "https://api.example.com"},
            "credentials": {"api_key": "k"},
        },
    ).json()["id"]


def test_register_credential_asset_hides_secret_value():
    connection_id = _create_connection("UC17-CRED-REG")
    resp = client.post(
        "/credential-assets",
        json={
            "connection_id": connection_id,
            "asset_type": "API_KEY",
            "secret_value": "top-secret-api-key",
            "expires_at": _iso_days_from_now(60),
            "rotation_period_days": 90,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["asset_type"] == "API_KEY"
    assert body["rotation_count"] == 0
    assert body["rotation_history"] == []
    assert "encrypted_value" not in body
    assert "top-secret-api-key" not in str(body)


def test_register_credential_asset_connection_not_found_returns_404():
    resp = client.post(
        "/credential-assets",
        json={
            "connection_id": 999999,
            "asset_type": "CERTIFICATE",
            "secret_value": "-----BEGIN CERTIFICATE-----abc-----END CERTIFICATE-----",
            "expires_at": _iso_days_from_now(30),
        },
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "SOURCE_CONNECTION_NOT_FOUND"


def test_rotate_credential_asset_records_rotation_history():
    connection_id = _create_connection("UC17-CRED-ROT")
    create = client.post(
        "/credential-assets",
        json={
            "connection_id": connection_id,
            "asset_type": "CERTIFICATE",
            "secret_value": "cert-v1",
            "expires_at": _iso_days_from_now(10),
        },
    ).json()
    assert create["rotation_count"] == 0

    resp = client.post(
        f"/credential-assets/{create['id']}/rotate",
        json={"secret_value": "cert-v2", "expires_at": _iso_days_from_now(400)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rotation_count"] == 1
    assert len(body["rotation_history"]) == 1
    assert body["rotated_at"] is not None

    resp2 = client.post(
        f"/credential-assets/{create['id']}/rotate",
        json={"secret_value": "cert-v3", "expires_at": _iso_days_from_now(800)},
    )
    assert resp2.json()["rotation_count"] == 2
    assert len(resp2.json()["rotation_history"]) == 2


def test_rotate_credential_asset_not_found_returns_404():
    resp = client.post(
        "/credential-assets/999999/rotate",
        json={"secret_value": "x", "expires_at": _iso_days_from_now(10)},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "CREDENTIAL_ASSET_NOT_FOUND"


def test_check_expiring_sends_alert_for_credentials_expiring_soon():
    connection_id = _create_connection("UC17-CRED-EXPIRING")
    soon_expiring = client.post(
        "/credential-assets",
        json={
            "connection_id": connection_id,
            "asset_type": "API_KEY",
            "secret_value": "expiring-soon-key",
            "expires_at": _iso_days_from_now(5),
        },
    ).json()
    far_future = client.post(
        "/credential-assets",
        json={
            "connection_id": connection_id,
            "asset_type": "CERTIFICATE",
            "secret_value": "far-future-cert",
            "expires_at": _iso_days_from_now(365),
        },
    ).json()

    resp = client.post("/credential-assets/check-expiring", params={"days_ahead": 30})
    assert resp.status_code == 200
    alerts = resp.json()
    alerted_ids = [a["asset_id"] for a in alerts]
    assert soon_expiring["id"] in alerted_ids
    assert far_future["id"] not in alerted_ids
    alert = next(a for a in alerts if a["asset_id"] == soon_expiring["id"])
    assert alert["alert_sent"] is True
    assert alert["days_remaining"] <= 5


def test_deactivated_credential_asset_excluded_from_expiring_check():
    connection_id = _create_connection("UC17-CRED-DEACT-EXPIRE")
    asset = client.post(
        "/credential-assets",
        json={
            "connection_id": connection_id,
            "asset_type": "API_KEY",
            "secret_value": "about-to-expire",
            "expires_at": _iso_days_from_now(1),
        },
    ).json()
    client.post(f"/credential-assets/{asset['id']}/deactivate")

    resp = client.post("/credential-assets/check-expiring", params={"days_ahead": 30})
    alerted_ids = [a["asset_id"] for a in resp.json()]
    assert asset["id"] not in alerted_ids


def test_list_credential_assets_filter_by_connection():
    connection_id = _create_connection("UC17-CRED-LIST")
    client.post(
        "/credential-assets",
        json={
            "connection_id": connection_id,
            "asset_type": "API_KEY",
            "secret_value": "abc",
            "expires_at": _iso_days_from_now(90),
        },
    )
    resp = client.get("/credential-assets", params={"connection_id": connection_id})
    assert resp.status_code == 200
    assert all(a["connection_id"] == connection_id for a in resp.json())
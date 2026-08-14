import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.db.models import Base  # noqa: E402
from app.infrastructure.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)


def _create(consumer_code="DVKT-01", scope="SEARCH,QA"):
    return client.post(
        "/api-keys",
        json={
            "consumer_name": "Sở Tài chính Hưng Yên",
            "consumer_code": consumer_code,
            "description": "Khoá khai thác API Search + QA",
            "scope": scope,
        },
    )


def test_create_api_key_generates_key_and_scope():
    resp = _create()
    assert resp.status_code == 201
    body = resp.json()
    assert body["consumer_code"] == "DVKT-01"
    assert body["scope"] == "SEARCH,QA"
    assert body["status"] == "ACTIVE"
    # Raw key chỉ trả về đúng 1 lần lúc tạo.
    assert body["raw_key"].startswith("gw_")
    assert body["key_prefix"] == body["raw_key"][:11]
    assert body["created_at"] is not None


def test_create_api_key_response_never_leaks_hash():
    resp = _create(consumer_code="DVKT-NOHASH")
    body = resp.json()
    assert "key_hash" not in body


def test_create_api_key_empty_scope_invalid():
    resp = client.post(
        "/api-keys",
        json={
            "consumer_name": "Đơn vị test",
            "consumer_code": "DVKT-BADSCOPE",
            "description": "",
            "scope": "   ",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_API_KEY"


def test_list_api_keys_and_filter_by_consumer_code():
    _create(consumer_code="DVKT-LIST-01")
    _create(consumer_code="DVKT-LIST-02")

    resp_all = client.get("/api-keys")
    assert resp_all.status_code == 200
    codes = {item["consumer_code"] for item in resp_all.json()}
    assert "DVKT-LIST-01" in codes
    assert "DVKT-LIST-02" in codes
    # list không lộ raw_key.
    assert all("raw_key" not in item for item in resp_all.json())

    resp_filtered = client.get("/api-keys", params={"consumer_code": "DVKT-LIST-01"})
    assert resp_filtered.status_code == 200
    assert all(item["consumer_code"] == "DVKT-LIST-01" for item in resp_filtered.json())


def test_get_api_key_not_found():
    resp = client.get("/api-keys/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "API_KEY_NOT_FOUND"


def test_revoke_api_key_success():
    created = _create(consumer_code="DVKT-REVOKE-01").json()
    key_id = created["id"]

    resp = client.post(f"/api-keys/{key_id}/revoke")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "REVOKED"
    assert body["revoked_at"] is not None

    resp_get = client.get(f"/api-keys/{key_id}")
    assert resp_get.json()["status"] == "REVOKED"


def test_revoke_api_key_twice_conflict():
    created = _create(consumer_code="DVKT-REVOKE-02").json()
    key_id = created["id"]
    client.post(f"/api-keys/{key_id}/revoke")

    resp = client.post(f"/api-keys/{key_id}/revoke")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "API_KEY_ALREADY_REVOKED"


def test_revoke_api_key_not_found():
    resp = client.post("/api-keys/999999/revoke")
    assert resp.status_code == 404


def test_rotate_api_key_creates_new_key_with_grace_period():
    created = _create(consumer_code="DVKT-ROTATE-01").json()
    key_id = created["id"]
    old_raw_key = created["raw_key"]

    resp = client.post(
        f"/api-keys/{key_id}/rotate",
        json={"grace_period_days": 5, "rotation_mode": "MANUAL"},
    )
    assert resp.status_code == 200
    body = resp.json()

    old_key = body["old_key"]
    new_key = body["new_key"]

    assert old_key["status"] == "ROTATED"
    assert old_key["rotated_at"] is not None
    assert old_key["grace_expires_at"] is not None
    assert old_key["rotated_to_id"] == new_key["id"]

    assert new_key["status"] == "ACTIVE"
    assert new_key["previous_key_id"] == key_id
    assert new_key["scope"] == created["scope"]
    assert new_key["consumer_code"] == "DVKT-ROTATE-01"
    # Khoá mới phải khác khoá cũ.
    assert new_key["raw_key"] != old_raw_key
    assert new_key["raw_key"].startswith("gw_")


def test_rotate_api_key_default_grace_period_used_when_not_specified():
    created = _create(consumer_code="DVKT-ROTATE-DEFAULT").json()
    key_id = created["id"]

    resp = client.post(f"/api-keys/{key_id}/rotate", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["old_key"]["grace_expires_at"] is not None


def test_rotate_api_key_not_found():
    resp = client.post("/api-keys/999999/rotate", json={})
    assert resp.status_code == 404


def test_rotate_api_key_already_revoked_conflict():
    created = _create(consumer_code="DVKT-ROTATE-REVOKED").json()
    key_id = created["id"]
    client.post(f"/api-keys/{key_id}/revoke")

    resp = client.post(f"/api-keys/{key_id}/rotate", json={})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "API_KEY_NOT_ACTIVE"


def test_rotate_api_key_twice_second_rotate_conflict():
    created = _create(consumer_code="DVKT-ROTATE-TWICE").json()
    key_id = created["id"]
    client.post(f"/api-keys/{key_id}/rotate", json={})

    resp = client.post(f"/api-keys/{key_id}/rotate", json={})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "API_KEY_NOT_ACTIVE"


def test_rotate_api_key_invalid_rotation_mode():
    created = _create(consumer_code="DVKT-ROTATE-BADMODE").json()
    key_id = created["id"]

    resp = client.post(
        f"/api-keys/{key_id}/rotate",
        json={"rotation_mode": "WRONG"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_API_KEY_ROTATION"


def test_rotate_api_key_auto_records_usage_log():
    created = _create(consumer_code="DVKT-ROTATE-AUTO").json()
    key_id = created["id"]

    client.post(
        f"/api-keys/{key_id}/rotate",
        json={"grace_period_days": 3, "rotation_mode": "AUTO"},
    )

    resp_logs = client.get(f"/api-keys/{key_id}/usage-logs")
    assert resp_logs.status_code == 200
    logs = resp_logs.json()
    assert len(logs) == 1
    assert "AUTO" in logs[0]["note"]


def test_log_api_key_usage_success():
    created = _create(consumer_code="DVKT-LOG-01").json()
    key_id = created["id"]

    resp = client.post(
        f"/api-keys/{key_id}/usage-logs",
        json={
            "endpoint_path": "/v1/search/documents",
            "method": "GET",
            "status_code": 200,
            "consumer_ip": "10.0.0.5",
            "note": "Truy vấn tra cứu văn bản",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["api_key_id"] == key_id
    assert body["endpoint_path"] == "/v1/search/documents"
    assert body["status_code"] == 200
    assert body["called_at"] is not None


def test_log_api_key_usage_not_found():
    resp = client.post(
        "/api-keys/999999/usage-logs",
        json={"endpoint_path": "/v1/x"},
    )
    assert resp.status_code == 404


def test_list_api_key_usage_logs_most_recent_first():
    created = _create(consumer_code="DVKT-LOG-LIST-01").json()
    key_id = created["id"]

    client.post(
        f"/api-keys/{key_id}/usage-logs",
        json={"endpoint_path": "/v1/a", "status_code": 200},
    )
    client.post(
        f"/api-keys/{key_id}/usage-logs",
        json={"endpoint_path": "/v1/b", "status_code": 403},
    )

    resp = client.get(f"/api-keys/{key_id}/usage-logs")
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) == 2
    assert logs[0]["endpoint_path"] == "/v1/b"
    assert logs[1]["endpoint_path"] == "/v1/a"
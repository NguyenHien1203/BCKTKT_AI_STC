"""Test UC-064 — Cung cấp Data API cho IOC.

Flow: IOC gọi Data API tổng hợp -> Hệ thống trả dữ liệu qua Lớp ngữ nghĩa;
Cổng API kiểm tra khoá API + phạm vi + giới hạn tần suất -> Hệ thống thực
thi; Ghi nhật ký lời gọi API -> Hệ thống ghi vào audit.audit_log.

Dùng chung 1 DB SQLite in-memory với các test khác trong service (thứ tự
khai báo trong file có ý nghĩa, cùng khuôn mẫu test_uc58/59/60/...).
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.db.models import Base  # noqa: E402
from app.infrastructure.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)


def _create_api_key(scope="DATA", consumer_code="IOC-01", service_tier_code=None):
    resp = client.post(
        "/api-keys",
        json={
            "consumer_name": "IOC tỉnh",
            "consumer_code": consumer_code,
            "description": "Khoá dùng cho test UC-064",
            "scope": scope,
            "service_tier_code": service_tier_code,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Bước 2 — Cổng API kiểm tra khoá API + phạm vi.
# ---------------------------------------------------------------------------


def test_call_data_api_missing_key_denied_and_audit_logged():
    resp = client.post(
        "/data-api/query",
        json={"dataset_code": "NGAN_SACH_TONG_HOP", "filters": {}},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "DATA_API_KEY_MISSING"

    logs = client.get("/data-api/audit-logs", params={"status": "DENIED"}).json()
    assert any(l["reason"].startswith("Thiếu khoá API") for l in logs)
    assert any(l["consumer_code"] == "UNKNOWN" for l in logs)


def test_call_data_api_invalid_key_denied():
    resp = client.post(
        "/data-api/query",
        json={"dataset_code": "NGAN_SACH_TONG_HOP", "filters": {}},
        headers={"X-API-Key": "gw_khong-ton-tai"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "DATA_API_KEY_INVALID"


def test_call_data_api_valid_key_missing_scope_denied():
    created = _create_api_key(scope="SEARCH,QA", consumer_code="IOC-02")
    resp = client.post(
        "/data-api/query",
        json={"dataset_code": "NGAN_SACH_TONG_HOP", "filters": {}},
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "DATA_API_SCOPE_DENIED"

    logs = client.get(
        "/data-api/audit-logs", params={"consumer_code": "IOC-02"}
    ).json()
    assert len(logs) == 1
    assert logs[0]["status"] == "DENIED"
    assert logs[0]["api_key_id"] == created["id"]


def test_call_data_api_revoked_key_denied():
    created = _create_api_key(scope="DATA", consumer_code="IOC-03")
    revoke_resp = client.post(f"/api-keys/{created['id']}/revoke")
    assert revoke_resp.status_code == 200

    resp = client.post(
        "/data-api/query",
        json={"dataset_code": "NGAN_SACH_TONG_HOP", "filters": {}},
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "DATA_API_KEY_INVALID"


# ---------------------------------------------------------------------------
# Bước 1 + "Hệ thống thực thi" — thành công qua Lớp ngữ nghĩa.
# ---------------------------------------------------------------------------


def test_call_data_api_success_returns_deterministic_rows_and_logs():
    created = _create_api_key(scope="DATA", consumer_code="IOC-04")
    resp = client.post(
        "/data-api/query",
        json={
            "dataset_code": "NGAN_SACH_TONG_HOP",
            "filters": {"nam": 2026},
        },
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dataset_code"] == "NGAN_SACH_TONG_HOP"
    assert body["row_count"] == len(body["rows"]) > 0

    # Gọi lại đúng tham số -> dữ liệu XÁC ĐỊNH giống hệt (deterministic).
    resp2 = client.post(
        "/data-api/query",
        json={
            "dataset_code": "NGAN_SACH_TONG_HOP",
            "filters": {"nam": 2026},
        },
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp2.json()["rows"] == body["rows"]

    # Ghi nhật ký sử dụng khoá (UC-059, tái dùng nguyên vẹn).
    usage_logs = client.get(f"/api-keys/{created['id']}/usage-logs").json()
    assert len(usage_logs) >= 2
    assert usage_logs[0]["endpoint_path"] == "/data-api/query"

    # Ghi vào audit.audit_log (UC-064 bước 3).
    audit_logs = client.get(
        "/data-api/audit-logs", params={"consumer_code": "IOC-04"}
    ).json()
    assert len(audit_logs) == 2
    assert all(l["status"] == "SUCCESS" for l in audit_logs)
    assert audit_logs[0]["row_count"] == body["row_count"]


def test_call_data_api_more_filters_narrows_row_count():
    created = _create_api_key(scope="DATA", consumer_code="IOC-05")
    resp_broad = client.post(
        "/data-api/query",
        json={"dataset_code": "DM_GIA", "filters": {}},
        headers={"X-API-Key": created["raw_key"]},
    )
    resp_narrow = client.post(
        "/data-api/query",
        json={
            "dataset_code": "DM_GIA",
            "filters": {"mat_hang": "Gạo ST25", "dia_ban": "Hà Nội"},
        },
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp_narrow.json()["row_count"] < resp_broad.json()["row_count"]


def test_call_data_api_empty_dataset_code_invalid():
    created = _create_api_key(scope="DATA", consumer_code="IOC-06")
    resp = client.post(
        "/data-api/query",
        json={"dataset_code": "", "filters": {}},
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Bước 2 — Cổng API kiểm tra giới hạn tần suất.
# ---------------------------------------------------------------------------


def test_call_data_api_no_tier_configured_allows_unlimited():
    # Gói "STANDARD" tồn tại (do UC-060 test tạo trước đó) nhưng CHƯA có
    # RateLimitPolicy (UC-060 chỉ cấu hình burst policy cho STANDARD) ->
    # không áp giới hạn tần suất.
    created = _create_api_key(
        scope="DATA", consumer_code="IOC-07", service_tier_code="STANDARD"
    )
    for _ in range(3):
        resp = client.post(
            "/data-api/query",
            json={"dataset_code": "DM_NGAN_SACH", "filters": {}},
            headers={"X-API-Key": created["raw_key"]},
        )
        assert resp.status_code == 200


def test_call_data_api_rate_limit_exceeded_denied():
    tier_resp = client.get("/service-tiers", params={"is_active": True})
    free_tier = next(t for t in tier_resp.json() if t["code"] == "FREE")
    tier_id = free_tier["id"]

    rate_resp = client.put(
        f"/service-tiers/{tier_id}/rate-limit",
        json={"requests_per_second": 1, "requests_per_day": 1000},
    )
    assert rate_resp.status_code == 200

    created = _create_api_key(
        scope="DATA", consumer_code="IOC-08", service_tier_code="FREE"
    )
    resp1 = client.post(
        "/data-api/query",
        json={"dataset_code": "DM_GIA", "filters": {}},
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp1.status_code == 200

    resp2 = client.post(
        "/data-api/query",
        json={"dataset_code": "DM_GIA", "filters": {}},
        headers={"X-API-Key": created["raw_key"]},
    )
    assert resp2.status_code == 429
    assert resp2.json()["detail"]["code"] == "DATA_API_RATE_LIMIT_EXCEEDED"

    audit_logs = client.get(
        "/data-api/audit-logs", params={"consumer_code": "IOC-08"}
    ).json()
    assert audit_logs[0]["status"] == "DENIED"
    assert "req/giây" in audit_logs[0]["reason"]


# ---------------------------------------------------------------------------
# Tra cứu audit.audit_log.
# ---------------------------------------------------------------------------


def test_list_audit_logs_filter_by_api_type_and_status():
    resp = client.get(
        "/data-api/audit-logs", params={"api_type": "DATA", "status": "SUCCESS"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert all(l["api_type"] == "DATA" and l["status"] == "SUCCESS" for l in body)
    assert len(body) > 0
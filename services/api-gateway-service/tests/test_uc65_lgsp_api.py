"""Test UC-065 — Cung cấp API qua LGSP.

Flow: Cổng LGSP chuyển tiếp yêu cầu -> Hệ thống nhận; Cổng API kiểm tra
chứng thư mTLS -> Hệ thống thực thi; Trả phản hồi theo chuẩn LGSP -> Hệ
thống response.

Dùng chung 1 DB SQLite in-memory với các test khác trong service (thứ tự
khai báo trong file có ý nghĩa, cùng khuôn mẫu test_uc58/59/../64). Tái
dùng endpoint đăng ký/thu hồi chứng thư mTLS của UC-062 để chuẩn bị dữ
liệu chứng thư cho các kịch bản kiểm tra mTLS của UC-065.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.db.models import Base  # noqa: E402
from app.infrastructure.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)


_SAMPLE_PEM = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...(mẫu demo LGSP)...\n"
    "-----END CERTIFICATE-----\n"
)


def _register_certificate(
    consumer_code="LGSP-01",
    serial_number="SN-LGSP-0001",
    not_before="2026-01-01T00:00:00Z",
    not_after="2027-01-01T00:00:00Z",
):
    resp = client.post(
        "/mtls-certificates",
        json={
            "consumer_code": consumer_code,
            "consumer_name": "Nền tảng LGSP tỉnh",
            "common_name": "lgsp.tinh.gov.vn",
            "serial_number": serial_number,
            "pem_certificate": _SAMPLE_PEM,
            "not_before": not_before,
            "not_after": not_after,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _call_lgsp(
    request_id="REQ-0001",
    service_code="NGAN_SACH_TONG_HOP",
    payload=None,
    cert_serial="SN-LGSP-0001",
):
    headers = {}
    if cert_serial is not None:
        headers["X-Client-Cert-Serial"] = cert_serial
    return client.post(
        "/lgsp/request",
        json={"request_id": request_id, "service_code": service_code, "payload": payload or {}},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Bước 1 — Cổng LGSP chuyển tiếp yêu cầu -> Hệ thống nhận (validate tối
# thiểu, LUÔN trả HTTP 200 kèm phong bì response_code khác "00").
# ---------------------------------------------------------------------------
def test_missing_service_code_rejected_by_schema_validation():
    resp = client.post(
        "/lgsp/request",
        json={"request_id": "REQ-EMPTY", "service_code": "", "payload": {}},
        headers={"X-Client-Cert-Serial": "SN-LGSP-0001"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Bước 2 — Cổng API kiểm tra chứng thư mTLS.
# ---------------------------------------------------------------------------
def test_missing_client_cert_header_denied_e01():
    resp = _call_lgsp(request_id="REQ-NOCERT", cert_serial=None)
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_code"] == "E01"
    assert body["data"] is None

    logs = client.get("/lgsp/audit-logs", params={"status": "DENIED"}).json()
    assert any(l["consumer_code"] == "UNKNOWN" and "Thiếu số hiệu" in l["reason"] for l in logs)


def test_unknown_cert_serial_denied_e02():
    resp = _call_lgsp(request_id="REQ-UNKNOWNCERT", cert_serial="SN-KHONG-TON-TAI")
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_code"] == "E02"
    assert "Không tìm thấy" in body["response_message"]


def test_expired_cert_denied_e02():
    _register_certificate(
        consumer_code="LGSP-EXPIRED",
        serial_number="SN-LGSP-EXPIRED",
        not_before="2020-01-01T00:00:00Z",
        not_after="2021-01-01T00:00:00Z",
    )
    resp = _call_lgsp(request_id="REQ-EXPIRED", cert_serial="SN-LGSP-EXPIRED")
    body = resp.json()
    assert body["response_code"] == "E02"


def test_revoked_cert_denied_e03():
    created = _register_certificate(consumer_code="LGSP-REVOKED", serial_number="SN-LGSP-REVOKED")
    revoke_resp = client.post(
        f"/mtls-certificates/{created['id']}/revoke", json={"reason": "Nghi ngờ lộ khoá riêng"}
    )
    assert revoke_resp.status_code == 200, revoke_resp.text

    resp = _call_lgsp(request_id="REQ-REVOKED", cert_serial="SN-LGSP-REVOKED")
    body = resp.json()
    assert body["response_code"] == "E03"
    assert "thu hồi" in body["response_message"]

    logs = client.get("/lgsp/audit-logs", params={"consumer_code": "LGSP-REVOKED"}).json()
    assert any(l["status"] == "DENIED" for l in logs)


# ---------------------------------------------------------------------------
# Bước 2b+3 — Hệ thống thực thi + Trả phản hồi theo chuẩn LGSP thành công.
# ---------------------------------------------------------------------------
def test_valid_cert_success_response_and_audit_logged():
    _register_certificate(consumer_code="LGSP-OK", serial_number="SN-LGSP-OK")

    resp = _call_lgsp(
        request_id="REQ-OK-001",
        service_code="NGAN_SACH_TONG_HOP",
        payload={"nam": 2026},
        cert_serial="SN-LGSP-OK",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_code"] == "00"
    assert body["response_message"] == "Thành công"
    assert body["request_id"] == "REQ-OK-001"
    assert body["processed_at"] is not None
    assert body["data"]["service_code"] == "NGAN_SACH_TONG_HOP"
    assert body["data"]["row_count"] == len(body["data"]["rows"])
    assert body["data"]["row_count"] > 0

    logs = client.get("/lgsp/audit-logs", params={"consumer_code": "LGSP-OK", "status": "SUCCESS"}).json()
    assert len(logs) == 1
    assert logs[0]["endpoint_path"] == "/lgsp/request"
    assert logs[0]["row_count"] == body["data"]["row_count"]


def test_success_response_is_deterministic_for_same_params():
    _register_certificate(consumer_code="LGSP-DET", serial_number="SN-LGSP-DET")

    resp1 = _call_lgsp(
        request_id="REQ-DET-1", service_code="NGAN_SACH_TONG_HOP", payload={"nam": 2026}, cert_serial="SN-LGSP-DET"
    )
    resp2 = _call_lgsp(
        request_id="REQ-DET-2", service_code="NGAN_SACH_TONG_HOP", payload={"nam": 2026}, cert_serial="SN-LGSP-DET"
    )
    assert resp1.json()["data"]["rows"] == resp2.json()["data"]["rows"]


def test_more_specific_filters_return_fewer_rows():
    _register_certificate(consumer_code="LGSP-FILTER", serial_number="SN-LGSP-FILTER")

    broad = _call_lgsp(
        request_id="REQ-BROAD", service_code="NGAN_SACH_TONG_HOP", payload={}, cert_serial="SN-LGSP-FILTER"
    ).json()
    narrow = _call_lgsp(
        request_id="REQ-NARROW",
        service_code="NGAN_SACH_TONG_HOP",
        payload={"nam": 2026, "don_vi": "Sở Tài chính"},
        cert_serial="SN-LGSP-FILTER",
    ).json()
    assert narrow["data"]["row_count"] <= broad["data"]["row_count"]


# ---------------------------------------------------------------------------
# Tra cứu audit.audit_log dành riêng cho LGSP (api_type=LGSP, không lẫn
# nhật ký của UC-064 Data API dù dùng chung 1 bảng).
# ---------------------------------------------------------------------------
def test_lgsp_audit_logs_do_not_leak_other_api_types():
    _register_certificate(consumer_code="LGSP-ISOLATE", serial_number="SN-LGSP-ISOLATE")
    _call_lgsp(request_id="REQ-ISOLATE", cert_serial="SN-LGSP-ISOLATE")

    logs = client.get("/lgsp/audit-logs").json()
    assert all(l["endpoint_path"] == "/lgsp/request" for l in logs)
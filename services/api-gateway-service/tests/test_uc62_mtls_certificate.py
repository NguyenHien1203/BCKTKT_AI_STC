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
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...(mẫu demo)...\n"
    "-----END CERTIFICATE-----\n"
)


def _register(
    consumer_code="DVKT-01",
    serial_number="SN-0001",
    common_name="dvkt01.taichinh.gov.vn",
    pem_certificate=None,
    not_before="2026-01-01T00:00:00Z",
    not_after="2027-01-01T00:00:00Z",
):
    return client.post(
        "/mtls-certificates",
        json={
            "consumer_code": consumer_code,
            "consumer_name": "Sở Tài chính Hưng Yên",
            "common_name": common_name,
            "serial_number": serial_number,
            "pem_certificate": pem_certificate or _SAMPLE_PEM,
            "not_before": not_before,
            "not_after": not_after,
        },
    )


# ---------------------------------------------------------------------------
# Bước 1 — Đăng ký chứng thư -> hệ thống lưu vào kho tin cậy.
# ---------------------------------------------------------------------------
def test_register_certificate_saved_to_trust_store():
    resp = _register()
    assert resp.status_code == 201
    body = resp.json()
    assert body["consumer_code"] == "DVKT-01"
    assert body["serial_number"] == "SN-0001"
    assert body["status"] == "ACTIVE"
    assert body["registered_at"] is not None
    assert len(body["fingerprint_sha256"]) == 64  # SHA-256 hex


def test_register_certificate_duplicate_serial_conflict():
    _register(serial_number="SN-DUP")
    resp = _register(serial_number="SN-DUP")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "MTLS_CERTIFICATE_SERIAL_ALREADY_EXISTS"


def test_register_certificate_invalid_pem_rejected():
    resp = _register(serial_number="SN-BAD-PEM", pem_certificate="not a pem")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_MTLS_CERTIFICATE"


def test_register_certificate_not_after_before_not_before_rejected():
    resp = _register(
        serial_number="SN-BAD-DATE",
        not_before="2027-01-01T00:00:00Z",
        not_after="2026-01-01T00:00:00Z",
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_MTLS_CERTIFICATE"


def test_list_certificates_filter_by_consumer_and_status():
    _register(consumer_code="DVKT-LIST", serial_number="SN-LIST-1")
    _register(consumer_code="DVKT-LIST", serial_number="SN-LIST-2")
    _register(consumer_code="DVKT-OTHER", serial_number="SN-LIST-3")

    resp = client.get("/mtls-certificates", params={"consumer_code": "DVKT-LIST"})
    assert resp.status_code == 200
    codes = {c["consumer_code"] for c in resp.json()}
    assert codes == {"DVKT-LIST"}
    assert len(resp.json()) == 2

    resp2 = client.get("/mtls-certificates", params={"status": "ACTIVE"})
    assert resp2.status_code == 200
    assert all(c["status"] == "ACTIVE" for c in resp2.json())


def test_get_certificate_not_found_404():
    resp = client.get("/mtls-certificates/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "MTLS_CERTIFICATE_NOT_FOUND"


# ---------------------------------------------------------------------------
# Bước 2 — Luân chuyển chứng thư -> hệ thống cập nhật.
# ---------------------------------------------------------------------------
def test_rotate_certificate_creates_new_and_marks_old_rotated():
    created = _register(consumer_code="DVKT-ROT", serial_number="SN-ROT-OLD").json()
    cert_id = created["id"]

    resp = client.post(
        f"/mtls-certificates/{cert_id}/rotate",
        json={
            "common_name": "dvkt-rot.taichinh.gov.vn",
            "serial_number": "SN-ROT-NEW",
            "pem_certificate": _SAMPLE_PEM,
            "not_before": "2026-06-01T00:00:00Z",
            "not_after": "2027-06-01T00:00:00Z",
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    old_cert = body["old_certificate"]
    new_cert = body["new_certificate"]

    assert old_cert["id"] == cert_id
    assert old_cert["status"] == "ROTATED"
    assert old_cert["rotated_at"] is not None
    assert old_cert["rotated_to_id"] == new_cert["id"]

    assert new_cert["status"] == "ACTIVE"
    assert new_cert["serial_number"] == "SN-ROT-NEW"
    assert new_cert["consumer_code"] == "DVKT-ROT"  # kế thừa từ chứng thư cũ

    # Kiểm tra lại qua GET.
    get_old = client.get(f"/mtls-certificates/{cert_id}").json()
    assert get_old["status"] == "ROTATED"
    get_new = client.get(f"/mtls-certificates/{new_cert['id']}").json()
    assert get_new["status"] == "ACTIVE"


def test_rotate_certificate_not_found_404():
    resp = client.post(
        "/mtls-certificates/999999/rotate",
        json={
            "common_name": "x",
            "serial_number": "SN-ROT-404",
            "pem_certificate": _SAMPLE_PEM,
            "not_before": "2026-01-01T00:00:00Z",
            "not_after": "2027-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "MTLS_CERTIFICATE_NOT_FOUND"


def test_rotate_certificate_duplicate_serial_conflict():
    created = _register(consumer_code="DVKT-ROT2", serial_number="SN-ROT2-OLD").json()
    _register(consumer_code="DVKT-ROT2-OTHER", serial_number="SN-ROT2-TAKEN")

    resp = client.post(
        f"/mtls-certificates/{created['id']}/rotate",
        json={
            "common_name": "x",
            "serial_number": "SN-ROT2-TAKEN",
            "pem_certificate": _SAMPLE_PEM,
            "not_before": "2026-01-01T00:00:00Z",
            "not_after": "2027-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "MTLS_CERTIFICATE_SERIAL_ALREADY_EXISTS"


def test_rotate_already_rotated_certificate_conflict():
    created = _register(consumer_code="DVKT-ROT3", serial_number="SN-ROT3-OLD").json()
    cert_id = created["id"]
    client.post(
        f"/mtls-certificates/{cert_id}/rotate",
        json={
            "common_name": "x",
            "serial_number": "SN-ROT3-NEW1",
            "pem_certificate": _SAMPLE_PEM,
            "not_before": "2026-01-01T00:00:00Z",
            "not_after": "2027-01-01T00:00:00Z",
        },
    )
    # Luân chuyển lần 2 trên chứng thư đã ROTATED -> lỗi.
    resp = client.post(
        f"/mtls-certificates/{cert_id}/rotate",
        json={
            "common_name": "x",
            "serial_number": "SN-ROT3-NEW2",
            "pem_certificate": _SAMPLE_PEM,
            "not_before": "2026-01-01T00:00:00Z",
            "not_after": "2027-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "MTLS_CERTIFICATE_NOT_ACTIVE"


# ---------------------------------------------------------------------------
# Bước 3 — Thu hồi chứng thư -> hệ thống thêm vào CRL.
# ---------------------------------------------------------------------------
def test_revoke_certificate_added_to_crl():
    created = _register(consumer_code="DVKT-REV", serial_number="SN-REV-1").json()
    cert_id = created["id"]

    resp = client.post(
        f"/mtls-certificates/{cert_id}/revoke",
        json={"reason": "Nghi ngờ rò rỉ khoá riêng"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "REVOKED"
    assert body["revoked_at"] is not None
    assert body["revocation_reason"] == "Nghi ngờ rò rỉ khoá riêng"

    crl_resp = client.get("/mtls-certificates/crl")
    assert crl_resp.status_code == 200
    serials = {e["serial_number"] for e in crl_resp.json()}
    assert "SN-REV-1" in serials

    check_resp = client.get("/mtls-certificates/crl/SN-REV-1/check")
    assert check_resp.status_code == 200
    assert check_resp.json()["is_revoked"] is True


def test_revoke_certificate_twice_conflict():
    created = _register(consumer_code="DVKT-REV2", serial_number="SN-REV-2").json()
    cert_id = created["id"]
    client.post(f"/mtls-certificates/{cert_id}/revoke", json={"reason": "lần 1"})
    resp = client.post(f"/mtls-certificates/{cert_id}/revoke", json={"reason": "lần 2"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "MTLS_CERTIFICATE_ALREADY_REVOKED"


def test_revoke_certificate_not_found_404():
    resp = client.post("/mtls-certificates/999999/revoke", json={"reason": "x"})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "MTLS_CERTIFICATE_NOT_FOUND"


def test_check_revoked_serial_not_in_crl_returns_false():
    resp = client.get("/mtls-certificates/crl/SN-CHUA-THU-HOI/check")
    assert resp.status_code == 200
    body = resp.json()
    assert body["serial_number"] == "SN-CHUA-THU-HOI"
    assert body["is_revoked"] is False


def test_crl_filter_by_consumer_code():
    c1 = _register(consumer_code="DVKT-CRL-A", serial_number="SN-CRL-A").json()
    c2 = _register(consumer_code="DVKT-CRL-B", serial_number="SN-CRL-B").json()
    client.post(f"/mtls-certificates/{c1['id']}/revoke", json={"reason": "a"})
    client.post(f"/mtls-certificates/{c2['id']}/revoke", json={"reason": "b"})

    resp = client.get("/mtls-certificates/crl", params={"consumer_code": "DVKT-CRL-A"})
    assert resp.status_code == 200
    serials = {e["serial_number"] for e in resp.json()}
    assert serials == {"SN-CRL-A"}
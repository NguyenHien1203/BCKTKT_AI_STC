"""Integration test UC-024: Tiếp nhận thủ công văn bản từ QLVBĐH (upload
định kỳ), qua HTTP API (SQLite in-memory).

Luồng nghiệp vụ (docs/use_cases.json id=24):
1. Nhập siêu dữ liệu văn bản -> hệ thống lưu vào staging.stg_van_ban.
2. Tải tệp PDF/bản quét đính kèm -> hệ thống lưu vào MinIO (raw-documents).
3. Khử trùng lặp theo so_ky_hieu -> hệ thống bỏ qua bản trùng.
4. Kích hoạt sự kiện ocr.requested -> hệ thống đẩy sự kiện.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.infrastructure.event_publisher import LoggingEventPublisher  # noqa: E402

client = TestClient(app)


def _create_data_source(code, source_system="QLVBDH"):
    resp = client.post(
        "/data-sources",
        json={
            "code": code,
            "name": "Nguồn dữ liệu test UC-24",
            "source_system": source_system,
            "provider": "Văn phòng Bộ",
            "owner": "Cục CNTT",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _submit(
    data_source_id,
    so_ky_hieu="123/QĐ-BTC",
    loai_van_ban="Quyết định",
    trich_yeu="Về việc ban hành quy chế",
    ngay_ban_hanh="2026-07-01",
    don_vi_ban_hanh="Bộ Tài chính",
    uploaded_by="canbo01",
    file_name="van-ban.pdf",
    content=b"%PDF-1.4 fake content",
):
    return client.post(
        "/qlvbdh-intake/documents",
        data={
            "data_source_id": data_source_id,
            "so_ky_hieu": so_ky_hieu,
            "loai_van_ban": loai_van_ban,
            "trich_yeu": trich_yeu,
            "ngay_ban_hanh": ngay_ban_hanh,
            "don_vi_ban_hanh": don_vi_ban_hanh,
            "uploaded_by": uploaded_by,
        },
        files={"file": (file_name, content, "application/pdf")},
    )


def test_submit_document_success_publishes_ocr_event():
    data_source_id = _create_data_source("UC24A-SRC")
    LoggingEventPublisher.published.clear()

    resp = _submit(data_source_id, so_ky_hieu="UC24A-001")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "RECEIVED"
    assert body["ocr_event_published"] is True
    assert body["so_ky_hieu"] == "UC24A-001"
    assert body["raw_object_key"]

    events = [e for e in LoggingEventPublisher.published if e["event_name"] == "ocr.requested"]
    assert len(events) == 1
    assert events[0]["payload"]["van_ban_intake_id"] == body["id"]
    assert events[0]["payload"]["so_ky_hieu"] == "UC24A-001"


def test_submit_duplicate_so_ky_hieu_is_skipped_no_new_event():
    data_source_id = _create_data_source("UC24B-SRC")
    first = _submit(data_source_id, so_ky_hieu="UC24B-DUP").json()

    LoggingEventPublisher.published.clear()
    second = _submit(
        data_source_id, so_ky_hieu="UC24B-DUP", trich_yeu="Trích yếu khác (bản trùng)"
    )
    assert second.status_code == 201, second.text
    body = second.json()
    assert body["id"] == first["id"]  # cùng 1 bản ghi, không tạo mới
    assert body["status"] == "DUPLICATE_SKIPPED"
    assert first["status"] == "RECEIVED"

    # Bản ghi gốc trong staging.stg_van_ban vẫn giữ nguyên status="RECEIVED".
    stored = client.get(f"/qlvbdh-intake/documents/{first['id']}").json()
    assert stored["status"] == "RECEIVED"

    # Không có sự kiện ocr.requested mới nào được phát cho bản trùng.
    assert LoggingEventPublisher.published == []


def test_submit_with_data_source_not_qlvbdh_returns_422():
    data_source_id = _create_data_source("UC24C-SRC", source_system="TABMIS")
    resp = _submit(data_source_id, so_ky_hieu="UC24C-001")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_SYSTEM_MISMATCH"


def test_submit_with_data_source_not_found_returns_404():
    resp = _submit(999999, so_ky_hieu="UC24D-001")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_NOT_FOUND"


def test_submit_missing_metadata_returns_422():
    data_source_id = _create_data_source("UC24E-SRC")
    resp = _submit(data_source_id, so_ky_hieu="   ")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_VAN_BAN_INTAKE_UPLOAD"


def test_submit_non_pdf_file_returns_422():
    data_source_id = _create_data_source("UC24F-SRC")
    resp = _submit(data_source_id, so_ky_hieu="UC24F-001", file_name="van-ban.docx")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_VAN_BAN_INTAKE_UPLOAD"


def test_list_and_get_documents():
    data_source_id = _create_data_source("UC24G-SRC")
    created = _submit(data_source_id, so_ky_hieu="UC24G-001").json()

    list_resp = client.get(f"/qlvbdh-intake/documents?data_source_id={data_source_id}")
    assert list_resp.status_code == 200
    assert any(d["id"] == created["id"] for d in list_resp.json())

    get_resp = client.get(f"/qlvbdh-intake/documents/{created['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["so_ky_hieu"] == "UC24G-001"


def test_get_document_not_found_returns_404():
    resp = client.get("/qlvbdh-intake/documents/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "VAN_BAN_INTAKE_NOT_FOUND"
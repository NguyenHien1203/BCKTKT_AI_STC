"""Integration test UC-030: Phân tích PDF/bản quét + OCR, qua HTTP API (SQLite in-memory)."""
import json
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.event_publisher import LoggingEventPublisher  # noqa: E402
from app.infrastructure.file_storage import get_document_file_storage  # noqa: E402
from app.infrastructure.ocr_engine import _FIXTURE_PREFIX  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _store_document(key: str, content: bytes) -> None:
    """Mô phỏng việc ingestion-service (UC-024) đã lưu tệp PDF/bản quét vào
    MinIO bucket `raw-documents` trước khi phát sự kiện `ocr.requested` —
    test ghi thẳng vào cùng storage backend (đĩa cục bộ khi chạy test) rồi
    mới gọi API như đang nhận sự kiện."""
    get_document_file_storage().upload(key, content, "application/pdf")


def _fixture_content(pages_processed=2, text="Nội dung văn bản", tables=None):
    payload = {"pages_processed": pages_processed, "text": text, "tables": tables or []}
    return _FIXTURE_PREFIX + json.dumps(payload).encode("utf-8")


def setup_function(_):
    LoggingEventPublisher.published.clear()


# ---------- Bước 1-6: happy path ----------


def test_ocr_happy_path_with_fixture_text_and_table():
    key = "van-ban-intake/1/uc30-happy.pdf"
    content = _fixture_content(
        pages_processed=3,
        text="Quyết định số 123/QD-STC về việc phê duyệt dự toán",
        tables=[{"page": 2, "rows": [["Mã", "Số tiền"], ["DV001", "1000000"]]}],
    )
    _store_document(key, content)

    resp = client.post(
        "/ocr-jobs",
        json={
            "raw_object_key": key,
            "van_ban_intake_id": 1,
            "data_source_id": 5,
            "so_ky_hieu": "123/QD-STC",
            "engine": "PADDLEOCR",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["pages_processed"] == 3
    assert body["engine_used"] == "PADDLEOCR"
    assert "Quyết định" in body["extracted_text"]
    assert body["table_count"] == 1
    assert body["ocr_completed_published"] is True
    assert body["parsing_requested_published"] is True

    # Sự kiện ocr.completed + parsing.requested đã được đẩy đúng thứ tự.
    published = LoggingEventPublisher.published
    event_names = [e["event_name"] for e in published]
    assert event_names == ["ocr.completed", "parsing.requested"]
    assert published[0]["payload"]["ocr_job_id"] == body["id"]
    assert published[0]["payload"]["so_ky_hieu"] == "123/QD-STC"
    assert published[1]["payload"]["table_count"] == 1

    # Xem lại bảng trích xuất (bước 3-4).
    tables_resp = client.get(f"/ocr-jobs/{body['id']}/tables")
    assert tables_resp.status_code == 200
    tables = tables_resp.json()
    assert len(tables) == 1
    assert tables[0]["page_number"] == 2
    assert tables[0]["rows"] == [["Mã", "Số tiền"], ["DV001", "1000000"]]


def test_ocr_best_effort_extraction_without_fixture():
    key = "van-ban-intake/1/uc30-plain.pdf"
    content = b"%PDF-1.4 some binary noise \x00\x01 Trich yeu van ban ABC"
    _store_document(key, content)

    resp = client.post("/ocr-jobs", json={"raw_object_key": key})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["engine_requested"] == "PADDLEOCR"
    assert "Trich" in body["extracted_text"]
    assert body["table_count"] == 0


def test_ocr_default_engine_is_paddleocr_when_not_specified():
    key = "van-ban-intake/1/uc30-default-engine.pdf"
    _store_document(key, _fixture_content(text="abc"))
    resp = client.post("/ocr-jobs", json={"raw_object_key": key})
    assert resp.status_code == 201
    assert resp.json()["engine_requested"] == "PADDLEOCR"


def test_ocr_olmocr_engine_requested():
    key = "van-ban-intake/1/uc30-olmocr.pdf"
    _store_document(key, _fixture_content(text="văn bản olmocr"))
    resp = client.post("/ocr-jobs", json={"raw_object_key": key, "engine": "OLMOCR"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["engine_requested"] == "OLMOCR"
    assert body["engine_used"] == "OLMOCR"


# ---------- Trường hợp lỗi ----------


def test_ocr_invalid_engine_returns_422():
    resp = client.post(
        "/ocr-jobs", json={"raw_object_key": "van-ban-intake/1/x.pdf", "engine": "TESSERACT"}
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_OCR_JOB"


def test_ocr_raw_object_not_found_returns_completed_job_with_failed_status():
    resp = client.post(
        "/ocr-jobs", json={"raw_object_key": "van-ban-intake/1/khong-ton-tai.pdf"}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert body["error_message"] is not None
    assert body["ocr_completed_published"] is False
    assert body["parsing_requested_published"] is False
    assert LoggingEventPublisher.published == []


def test_ocr_no_text_no_table_extracted_results_in_failed_and_no_event():
    key = "van-ban-intake/1/uc30-empty.pdf"
    _store_document(key, _fixture_content(text="   ", tables=[]))
    resp = client.post("/ocr-jobs", json={"raw_object_key": key})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert body["error_message"] == "OCR không trích được văn bản hoặc bảng nào"
    assert LoggingEventPublisher.published == []


def test_ocr_invalid_fixture_json_results_in_failed_job():
    key = "van-ban-intake/1/uc30-bad-fixture.pdf"
    _store_document(key, _FIXTURE_PREFIX + b"not-json")
    resp = client.post("/ocr-jobs", json={"raw_object_key": key})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert "OCR_ENGINE_ERROR" not in body  # error nằm ở error_message, không phải code HTTP
    assert body["error_message"]


def test_get_ocr_job_not_found_returns_404():
    resp = client.get("/ocr-jobs/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "OCR_JOB_NOT_FOUND"


def test_list_tables_not_found_returns_404():
    resp = client.get("/ocr-jobs/999999/tables")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "OCR_JOB_NOT_FOUND"


# ---------- Danh sách + lọc ----------


def test_list_ocr_jobs_filters_by_data_source_status_and_van_ban_intake():
    key1 = "van-ban-intake/1/uc30-list-1.pdf"
    key2 = "van-ban-intake/2/uc30-list-2.pdf"
    _store_document(key1, _fixture_content(text="văn bản 1"))
    _store_document(key2, _fixture_content(text="văn bản 2"))

    r1 = client.post(
        "/ocr-jobs",
        json={"raw_object_key": key1, "data_source_id": 10, "van_ban_intake_id": 100},
    )
    r2 = client.post(
        "/ocr-jobs",
        json={"raw_object_key": key2, "data_source_id": 20, "van_ban_intake_id": 200},
    )
    assert r1.status_code == 201 and r2.status_code == 201

    resp = client.get("/ocr-jobs", params={"data_source_id": 10})
    ids = [j["id"] for j in resp.json()]
    assert r1.json()["id"] in ids
    assert r2.json()["id"] not in ids

    resp = client.get("/ocr-jobs", params={"status": "COMPLETED"})
    assert all(j["status"] == "COMPLETED" for j in resp.json())

    resp = client.get("/ocr-jobs", params={"van_ban_intake_id": 200})
    ids = [j["id"] for j in resp.json()]
    assert ids == [r2.json()["id"]]


def test_ocr_job_log_entries_capture_pipeline_steps():
    key = "van-ban-intake/1/uc30-logs.pdf"
    _store_document(key, _fixture_content(text="nội dung log"))
    resp = client.post("/ocr-jobs", json={"raw_object_key": key})
    body = resp.json()
    messages = " ".join(entry["message"] for entry in body["log_entries"])
    assert "Nhận sự kiện ocr.requested" in messages
    assert "ocr.completed" in messages
    assert "parsing.requested" in messages
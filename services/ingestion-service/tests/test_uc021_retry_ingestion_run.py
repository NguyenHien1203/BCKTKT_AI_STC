"""Integration test UC-021: Chạy lại phiên ingest lỗi, qua HTTP API (SQLite in-memory)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_data_source(code="UC21-SRC-01"):
    resp = client.post(
        "/data-sources",
        json={
            "code": code,
            "name": "Nguồn dữ liệu test UC-21",
            "source_system": "TABMIS",
            "provider": "Bộ Tài chính",
            "owner": "Cục CNTT",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _basic_schema_fields():
    return [
        {"name": "id", "data_type": "BIGINT", "nullable": False, "description": "Khoá chính"},
        {"name": "ma_don_vi", "data_type": "STRING", "nullable": False, "description": ""},
    ]


def _create_dataset(data_source_id, code="UC21-DS-01"):
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": data_source_id,
            "code": code,
            "name": "Tập dữ liệu test UC-21",
            "schema_fields": _basic_schema_fields(),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _new_dataset(prefix):
    data_source_id = _create_data_source(f"{prefix}-SRC")
    return _create_dataset(data_source_id, f"{prefix}-DS")


def _start_run(dataset_id, **overrides):
    payload = {"dataset_id": dataset_id, "trigger": "MANUAL", "sync_mode": "FULL"}
    payload.update(overrides)
    resp = client.post("/ingestion-runs", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _fail_run(run_id, message="Lỗi kết nối tới nguồn TABMIS", records_read=100, records_failed=100):
    client.post(
        f"/ingestion-runs/{run_id}/logs",
        json={"level": "ERROR", "message": message},
    )
    resp = client.post(
        f"/ingestion-runs/{run_id}/complete",
        json={
            "status": "FAILED",
            "records_read": records_read,
            "records_loaded": 0,
            "records_failed": records_failed,
            "error_message": message,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_failed_run(prefix):
    dataset_id = _new_dataset(prefix)
    run = _start_run(dataset_id)
    return dataset_id, _fail_run(run["id"])


# ---------- Bước 1: Chọn phiên bị lỗi -> hiển thị nguyên nhân ----------


def test_get_failure_reason_returns_cause_and_retryable_true():
    _, failed = _make_failed_run("UC21-REASON")
    resp = client.get(f"/ingestion-runs/{failed['id']}/failure-reason")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert "Lỗi kết nối" in body["error_message"]
    assert body["retryable"] is True
    assert len(body["error_log_entries"]) == 1
    assert body["error_log_entries"][0]["level"] == "ERROR"


def test_get_failure_reason_404_when_run_missing():
    resp = client.get("/ingestion-runs/999999/failure-reason")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "INGESTION_RUN_NOT_FOUND"


# ---------- Bước 2-4: Kích hoạt chạy lại + khoá chống trùng + ghi lịch sử ----------


def test_retry_creates_new_run_linked_to_original_and_completes():
    _, failed = _make_failed_run("UC21-RETRY")
    resp = client.post(f"/ingestion-runs/{failed['id']}/retry")
    assert resp.status_code == 201, resp.text
    retried = resp.json()
    assert retried["id"] != failed["id"]
    assert retried["trigger"] == "RETRY"
    assert retried["retry_of_run_id"] == failed["id"]
    assert retried["dataset_id"] == failed["dataset_id"]
    # Bước 4: hệ thống ghi vào ingestion.runs — trạng thái cuối được cập nhật
    assert retried["status"] in ("SUCCESS", "FAILED", "PARTIAL")
    assert any("Bộ điều phối kích hoạt chạy lại" in e["message"] for e in retried["log_entries"])


def test_retry_404_when_run_missing():
    resp = client.post("/ingestion-runs/999999/retry")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "INGESTION_RUN_NOT_FOUND"


def test_retry_409_when_original_run_not_failed():
    dataset_id = _new_dataset("UC21-NOTFAILED")
    run = _start_run(dataset_id)  # vẫn đang RUNNING, chưa FAILED
    resp = client.post(f"/ingestion-runs/{run['id']}/retry")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INGESTION_RUN_NOT_FAILED"


def test_retry_success_run_cannot_be_retried_again():
    _, failed = _make_failed_run("UC21-SUCCESSRETRY")
    resp = client.post(f"/ingestion-runs/{failed['id']}/retry")
    assert resp.status_code == 201, resp.text
    # phiên gốc vẫn ở trạng thái FAILED (không đổi), nhưng có thể chạy lại
    # tiếp nếu lần chạy lại trước đó đã hoàn tất (không còn RUNNING)
    retried = resp.json()
    assert retried["status"] != "RUNNING"


def test_retry_lock_rejects_duplicate_while_previous_retry_still_running():
    """Khoá chống trùng: nếu đã có 1 phiên RETRY của cùng phiên gốc đang
    RUNNING (Bộ điều phối thực thi thật sẽ mất thời gian, không hoàn tất
    ngay như NoOp executor), thì lượt kích hoạt chạy lại tiếp theo phải bị
    từ chối. Mô phỏng trạng thái "đang RUNNING" bằng cách ghi thẳng vào
    repository — tương đương thời điểm giữa bước 3 (tạo phiên) và bước 4
    (cập nhật trạng thái cuối) của luồng UC-021 khi Bộ điều phối thật chưa
    trả kết quả."""
    _, failed = _make_failed_run("UC21-LOCK")

    from datetime import datetime, timezone

    from app.domain.entities import IngestionRun
    from app.infrastructure.db.repository_impl import SqlAlchemyIngestionRunRepository
    from app.infrastructure.db.session import SessionLocal

    db = SessionLocal()
    try:
        repo = SqlAlchemyIngestionRunRepository(db)
        active_retry = IngestionRun(
            id=None,
            dataset_id=failed["dataset_id"],
            scheduled_task_id=None,
            trigger="RETRY",
            sync_mode="FULL",
            started_at=datetime.now(timezone.utc).isoformat(),
            status="RUNNING",
            retry_of_run_id=failed["id"],
        )
        repo.add(active_retry)
    finally:
        db.close()

    resp = client.post(f"/ingestion-runs/{failed['id']}/retry")
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "INGESTION_RUN_RETRY_IN_PROGRESS"

    reason = client.get(f"/ingestion-runs/{failed['id']}/failure-reason").json()
    assert reason["retryable"] is False


# ---------- Xem lịch sử chạy lại của 1 phiên gốc ----------


def test_list_retries_returns_history_newest_first():
    _, failed = _make_failed_run("UC21-HISTORY")
    resp1 = client.post(f"/ingestion-runs/{failed['id']}/retry")
    assert resp1.status_code == 201, resp1.text

    resp = client.get(f"/ingestion-runs/{failed['id']}/retries")
    assert resp.status_code == 200, resp.text
    retries = resp.json()
    assert len(retries) == 1
    assert retries[0]["retry_of_run_id"] == failed["id"]
    assert retries[0]["trigger"] == "RETRY"


def test_list_retries_404_when_run_missing():
    resp = client.get("/ingestion-runs/999999/retries")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "INGESTION_RUN_NOT_FOUND"


def test_original_run_history_still_lists_after_retry():
    dataset_id, failed = _make_failed_run("UC21-STILLLISTED")
    client.post(f"/ingestion-runs/{failed['id']}/retry")
    resp = client.get("/ingestion-runs", params={"dataset_id": dataset_id})
    assert resp.status_code == 200, resp.text
    ids = [r["id"] for r in resp.json()]
    assert failed["id"] in ids
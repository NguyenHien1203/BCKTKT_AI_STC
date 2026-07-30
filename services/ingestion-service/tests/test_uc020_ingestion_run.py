"""Integration test UC-020 qua HTTP API, dùng SQLite in-memory."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_data_source(code="UC20-SRC-01"):
    resp = client.post(
        "/data-sources",
        json={
            "code": code,
            "name": "Nguồn dữ liệu test UC-20",
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


def _create_dataset(data_source_id, code="UC20-DS-01"):
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": data_source_id,
            "code": code,
            "name": "Tập dữ liệu test UC-20",
            "schema_fields": _basic_schema_fields(),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _new_dataset(prefix):
    data_source_id = _create_data_source(f"{prefix}-SRC")
    return _create_dataset(data_source_id, f"{prefix}-DS")


def _configure_task(dataset_id, code="UC20-TASK-01"):
    resp = client.post(
        "/scheduled-tasks",
        json={
            "dataset_id": dataset_id,
            "code": code,
            "name": "Đồng bộ tập dữ liệu test UC-20",
            "sync_mode": "FULL",
            "cron_expression": "0 2 * * *",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _start_run(dataset_id, **overrides):
    payload = {"dataset_id": dataset_id, "trigger": "MANUAL", "sync_mode": "FULL"}
    payload.update(overrides)
    resp = client.post("/ingestion-runs", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Ghi nhận vòng đời phiên (hạ tầng) ----------


def test_start_run_creates_running_status():
    dataset_id = _new_dataset("UC20-START")
    body = _start_run(dataset_id)
    assert body["status"] == "RUNNING"
    assert body["dataset_id"] == dataset_id
    assert body["trigger"] == "MANUAL"
    assert body["log_entries"] == []


def test_start_run_404_when_dataset_missing():
    resp = client.post("/ingestion-runs", json={"dataset_id": 999999, "trigger": "MANUAL"})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATASET_NOT_FOUND"


def test_start_run_with_scheduled_task():
    dataset_id = _new_dataset("UC20-TASKRUN")
    task_id = _configure_task(dataset_id, "UC20-TASKRUN-TASK")
    body = _start_run(dataset_id, trigger="SCHEDULED", scheduled_task_id=task_id)
    assert body["scheduled_task_id"] == task_id
    assert body["trigger"] == "SCHEDULED"


def test_append_log_accumulates_entries():
    dataset_id = _new_dataset("UC20-LOG")
    run = _start_run(dataset_id)
    resp1 = client.post(
        f"/ingestion-runs/{run['id']}/logs",
        json={"level": "INFO", "message": "Bắt đầu đọc dữ liệu nguồn"},
    )
    assert resp1.status_code == 200, resp1.text
    resp2 = client.post(
        f"/ingestion-runs/{run['id']}/logs",
        json={"level": "WARNING", "message": "Có 2 bản ghi thiếu trường bắt buộc"},
    )
    assert resp2.status_code == 200, resp2.text
    body = resp2.json()
    assert len(body["log_entries"]) == 2
    assert body["log_entries"][0]["level"] == "INFO"
    assert body["log_entries"][1]["level"] == "WARNING"


def test_append_log_404_when_run_missing():
    resp = client.post("/ingestion-runs/999999/logs", json={"level": "INFO", "message": "x"})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "INGESTION_RUN_NOT_FOUND"


def test_complete_run_success_with_control_totals():
    dataset_id = _new_dataset("UC20-COMPLETE-OK")
    run = _start_run(dataset_id)
    resp = client.post(
        f"/ingestion-runs/{run['id']}/complete",
        json={
            "status": "SUCCESS",
            "records_read": 1000,
            "records_loaded": 1000,
            "records_failed": 0,
            "control_totals": {"expected_records": 1000, "actual_records": 1000, "checksum_ok": True},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "SUCCESS"
    assert body["finished_at"] is not None
    assert body["control_totals"]["actual_records"] == 1000


def test_complete_run_failed_with_error_message():
    dataset_id = _new_dataset("UC20-COMPLETE-FAIL")
    run = _start_run(dataset_id)
    resp = client.post(
        f"/ingestion-runs/{run['id']}/complete",
        json={
            "status": "FAILED",
            "records_read": 100,
            "records_loaded": 0,
            "records_failed": 100,
            "control_totals": {},
            "error_message": "Mất kết nối tới nguồn TABMIS",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert body["error_message"] == "Mất kết nối tới nguồn TABMIS"


def test_complete_run_422_when_status_invalid():
    dataset_id = _new_dataset("UC20-COMPLETE-BAD")
    run = _start_run(dataset_id)
    resp = client.post(
        f"/ingestion-runs/{run['id']}/complete",
        json={"status": "RUNNING", "records_read": 0, "records_loaded": 0, "records_failed": 0},
    )
    assert resp.status_code == 422


# ---------- Bước 1: Xem lịch sử chạy ----------


def test_list_run_history_filters_by_dataset():
    dataset_id_1 = _new_dataset("UC20-HIST-A")
    dataset_id_2 = _new_dataset("UC20-HIST-B")
    _start_run(dataset_id_1)
    _start_run(dataset_id_1)
    _start_run(dataset_id_2)

    resp = client.get("/ingestion-runs", params={"dataset_id": dataset_id_1})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 2
    assert all(r["dataset_id"] == dataset_id_1 for r in body)


def test_list_run_history_filters_by_status():
    dataset_id = _new_dataset("UC20-HIST-STATUS")
    run1 = _start_run(dataset_id)
    run2 = _start_run(dataset_id)
    client.post(
        f"/ingestion-runs/{run1['id']}/complete",
        json={"status": "SUCCESS", "records_read": 10, "records_loaded": 10, "records_failed": 0},
    )
    client.post(
        f"/ingestion-runs/{run2['id']}/complete",
        json={"status": "FAILED", "records_read": 5, "records_loaded": 0, "records_failed": 5},
    )

    resp = client.get(
        "/ingestion-runs", params={"dataset_id": dataset_id, "status": "FAILED"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == run2["id"]


def test_list_run_history_filters_by_scheduled_task():
    dataset_id = _new_dataset("UC20-HIST-TASK")
    task_id = _configure_task(dataset_id, "UC20-HIST-TASK-CODE")
    _start_run(dataset_id, trigger="MANUAL")
    _start_run(dataset_id, trigger="SCHEDULED", scheduled_task_id=task_id)

    resp = client.get("/ingestion-runs", params={"scheduled_task_id": task_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["scheduled_task_id"] == task_id


def test_list_run_history_404_when_dataset_missing():
    resp = client.get("/ingestion-runs", params={"dataset_id": 999999})
    assert resp.status_code == 404


def test_list_run_history_newest_first():
    dataset_id = _new_dataset("UC20-HIST-ORDER")
    run1 = _start_run(dataset_id, started_at="2026-07-01T00:00:00+00:00")
    run2 = _start_run(dataset_id, started_at="2026-07-05T00:00:00+00:00")

    resp = client.get("/ingestion-runs", params={"dataset_id": dataset_id})
    body = resp.json()
    assert body[0]["id"] == run2["id"]
    assert body[1]["id"] == run1["id"]


# ---------- Bước 2: Xem lịch đầy đủ dữ liệu (heatmap) ----------


def test_data_calendar_marks_missing_days():
    dataset_id = _new_dataset("UC20-CAL-MISSING")
    run = _start_run(dataset_id, started_at="2026-07-10T08:00:00+00:00")
    client.post(
        f"/ingestion-runs/{run['id']}/complete",
        json={"status": "SUCCESS", "records_read": 10, "records_loaded": 10, "records_failed": 0},
    )

    resp = client.get(
        "/ingestion-runs/calendar",
        params={"dataset_id": dataset_id, "date_from": "2026-07-09", "date_to": "2026-07-11"},
    )
    assert resp.status_code == 200, resp.text
    body = {d["date"]: d for d in resp.json()}
    assert len(body) == 3
    assert body["2026-07-09"]["is_missing"] is True
    assert body["2026-07-09"]["run_count"] == 0
    assert body["2026-07-10"]["is_missing"] is False
    assert body["2026-07-10"]["success_count"] == 1
    assert body["2026-07-11"]["is_missing"] is True


def test_data_calendar_day_with_only_failed_run_is_missing():
    dataset_id = _new_dataset("UC20-CAL-FAILED")
    run = _start_run(dataset_id, started_at="2026-07-15T08:00:00+00:00")
    client.post(
        f"/ingestion-runs/{run['id']}/complete",
        json={"status": "FAILED", "records_read": 10, "records_loaded": 0, "records_failed": 10},
    )

    resp = client.get(
        "/ingestion-runs/calendar",
        params={"dataset_id": dataset_id, "date_from": "2026-07-15", "date_to": "2026-07-15"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()[0]
    assert body["is_missing"] is True
    assert body["failed_count"] == 1
    assert body["run_count"] == 1


def test_data_calendar_404_when_dataset_missing():
    resp = client.get(
        "/ingestion-runs/calendar",
        params={"dataset_id": 999999, "date_from": "2026-07-01", "date_to": "2026-07-02"},
    )
    assert resp.status_code == 404


def test_data_calendar_409_when_date_range_invalid():
    dataset_id = _new_dataset("UC20-CAL-BADRANGE")
    resp = client.get(
        "/ingestion-runs/calendar",
        params={"dataset_id": dataset_id, "date_from": "2026-07-10", "date_to": "2026-07-01"},
    )
    assert resp.status_code == 409


# ---------- Bước 3: Xem chi tiết phiên cụ thể ----------


def test_get_run_detail_shows_log_and_control_totals():
    dataset_id = _new_dataset("UC20-DETAIL")
    run = _start_run(dataset_id)
    client.post(
        f"/ingestion-runs/{run['id']}/logs",
        json={"level": "INFO", "message": "Đang tải dữ liệu"},
    )
    client.post(
        f"/ingestion-runs/{run['id']}/complete",
        json={
            "status": "SUCCESS",
            "records_read": 50,
            "records_loaded": 50,
            "records_failed": 0,
            "control_totals": {"expected_records": 50, "actual_records": 50},
        },
    )

    resp = client.get(f"/ingestion-runs/{run['id']}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["log_entries"]) == 1
    assert body["control_totals"]["actual_records"] == 50
    assert body["records_loaded"] == 50


def test_get_run_detail_404_when_missing():
    resp = client.get("/ingestion-runs/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "INGESTION_RUN_NOT_FOUND"
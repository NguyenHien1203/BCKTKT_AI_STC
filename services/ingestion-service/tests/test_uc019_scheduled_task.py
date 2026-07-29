"""Integration test UC-019 qua HTTP API, dùng SQLite in-memory."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_data_source(code="UC19-SRC-01"):
    resp = client.post(
        "/data-sources",
        json={
            "code": code,
            "name": "Nguồn dữ liệu test UC-19",
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


def _create_dataset(data_source_id, code="UC19-DS-01"):
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": data_source_id,
            "code": code,
            "name": "Tập dữ liệu test UC-19",
            "schema_fields": _basic_schema_fields(),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _new_dataset(prefix):
    data_source_id = _create_data_source(f"{prefix}-SRC")
    return _create_dataset(data_source_id, f"{prefix}-DS")


def _configure_task(dataset_id, code="UC19-TASK-01", **overrides):
    payload = {
        "dataset_id": dataset_id,
        "code": code,
        "name": "Đồng bộ tập dữ liệu test",
        "sync_mode": "FULL",
        "cron_expression": "0 2 * * *",
        "retry_max_attempts": 3,
        "retry_delay_seconds": 60,
        "retry_backoff": "FIXED",
    }
    payload.update(overrides)
    resp = client.post("/scheduled-tasks", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Cấu hình tác vụ điều phối ----------


def test_configure_scheduled_task_saves_config():
    dataset_id = _new_dataset("UC19-CONF")
    body = _configure_task(dataset_id, "UC19-TASK-CONF")
    assert body["dataset_id"] == dataset_id
    assert body["sync_mode"] == "FULL"
    assert body["cron_expression"] == "0 2 * * *"
    assert body["retry_max_attempts"] == 3
    assert body["retry_delay_seconds"] == 60
    assert body["retry_backoff"] == "FIXED"
    assert body["is_enabled"] is True
    assert body["status"] == "IDLE"


def test_configure_scheduled_task_incremental_mode():
    dataset_id = _new_dataset("UC19-INCR")
    body = _configure_task(
        dataset_id, "UC19-TASK-INCR", sync_mode="INCREMENTAL", retry_backoff="EXPONENTIAL"
    )
    assert body["sync_mode"] == "INCREMENTAL"
    assert body["retry_backoff"] == "EXPONENTIAL"


def test_configure_scheduled_task_invalid_dataset_returns_404():
    resp = client.post(
        "/scheduled-tasks",
        json={
            "dataset_id": 999999,
            "code": "UC19-TASK-BADDS",
            "name": "X",
            "cron_expression": "0 2 * * *",
        },
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATASET_NOT_FOUND"


def test_configure_scheduled_task_duplicate_code_returns_409():
    dataset_id = _new_dataset("UC19-DUP")
    _configure_task(dataset_id, "UC19-TASK-DUP")
    resp = client.post(
        "/scheduled-tasks",
        json={
            "dataset_id": dataset_id,
            "code": "UC19-TASK-DUP",
            "name": "Trùng mã",
            "cron_expression": "0 2 * * *",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "SCHEDULED_TASK_CODE_EXISTS"


def test_configure_scheduled_task_invalid_cron_returns_422():
    dataset_id = _new_dataset("UC19-CRON")
    resp = client.post(
        "/scheduled-tasks",
        json={
            "dataset_id": dataset_id,
            "code": "UC19-TASK-CRON",
            "name": "Cron sai",
            "cron_expression": "invalid cron",
        },
    )
    assert resp.status_code == 422


def test_get_scheduled_task_not_found_returns_404():
    resp = client.get("/scheduled-tasks/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "SCHEDULED_TASK_NOT_FOUND"


def test_list_scheduled_tasks_filters_by_dataset():
    dataset_id1 = _new_dataset("UC19-LIST1")
    dataset_id2 = _new_dataset("UC19-LIST2")
    _configure_task(dataset_id1, "UC19-TASK-LIST1")
    _configure_task(dataset_id2, "UC19-TASK-LIST2")

    resp = client.get("/scheduled-tasks", params={"dataset_id": dataset_id1})
    assert resp.status_code == 200
    codes = [t["code"] for t in resp.json()]
    assert "UC19-TASK-LIST1" in codes
    assert "UC19-TASK-LIST2" not in codes


def test_update_scheduled_task_config_saves_changes():
    dataset_id = _new_dataset("UC19-UPD")
    task = _configure_task(dataset_id, "UC19-TASK-UPD")

    resp = client.put(
        f"/scheduled-tasks/{task['id']}",
        json={
            "sync_mode": "INCREMENTAL",
            "cron_expression": "*/15 * * * *",
            "retry_max_attempts": 5,
            "retry_delay_seconds": 120,
            "retry_backoff": "EXPONENTIAL",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sync_mode"] == "INCREMENTAL"
    assert body["cron_expression"] == "*/15 * * * *"
    assert body["retry_max_attempts"] == 5
    assert body["retry_delay_seconds"] == 120
    assert body["retry_backoff"] == "EXPONENTIAL"


def test_update_scheduled_task_config_not_found_returns_404():
    resp = client.put(
        "/scheduled-tasks/999999",
        json={
            "sync_mode": "FULL",
            "cron_expression": "0 2 * * *",
            "retry_max_attempts": 3,
            "retry_delay_seconds": 60,
            "retry_backoff": "FIXED",
        },
    )
    assert resp.status_code == 404


# ---------- Bật / tắt tác vụ điều phối ----------


def test_disable_then_enable_scheduled_task():
    dataset_id = _new_dataset("UC19-TOGGLE")
    task = _configure_task(dataset_id, "UC19-TASK-TOGGLE")
    assert task["is_enabled"] is True

    resp = client.post(f"/scheduled-tasks/{task['id']}/disable")
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is False

    resp = client.post(f"/scheduled-tasks/{task['id']}/enable")
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is True


def test_disable_not_found_returns_404():
    resp = client.post("/scheduled-tasks/999999/disable")
    assert resp.status_code == 404


def test_only_enabled_filter():
    dataset_id = _new_dataset("UC19-ONLYEN")
    task = _configure_task(dataset_id, "UC19-TASK-ONLYEN")
    client.post(f"/scheduled-tasks/{task['id']}/disable")

    resp = client.get(
        "/scheduled-tasks", params={"dataset_id": dataset_id, "only_enabled": True}
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ---------- Hệ thống cập nhật trạng thái thực thi ----------


def test_record_run_status_updates_state():
    dataset_id = _new_dataset("UC19-STATUS")
    task = _configure_task(dataset_id, "UC19-TASK-STATUS")

    resp = client.post(
        f"/scheduled-tasks/{task['id']}/status",
        json={"status": "RUNNING", "message": "Đang chạy phiên đồng bộ"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "RUNNING"
    assert body["last_run_message"] == "Đang chạy phiên đồng bộ"
    assert body["last_run_at"] is not None

    resp = client.post(
        f"/scheduled-tasks/{task['id']}/status",
        json={"status": "SUCCESS", "message": "Hoàn tất"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"

    resp = client.post(
        f"/scheduled-tasks/{task['id']}/status",
        json={"status": "FAILED", "message": "Lỗi kết nối nguồn"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "FAILED"
    assert body["last_run_message"] == "Lỗi kết nối nguồn"


def test_record_run_status_not_found_returns_404():
    resp = client.post(
        "/scheduled-tasks/999999/status", json={"status": "SUCCESS", "message": ""}
    )
    assert resp.status_code == 404


def test_record_run_status_invalid_status_returns_422():
    dataset_id = _new_dataset("UC19-BADSTATUS")
    task = _configure_task(dataset_id, "UC19-TASK-BADSTATUS")
    resp = client.post(
        f"/scheduled-tasks/{task['id']}/status",
        json={"status": "UNKNOWN", "message": ""},
    )
    assert resp.status_code == 422
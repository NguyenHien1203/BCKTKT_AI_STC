"""Integration test UC-025: Đồng bộ tăng dần từ API/DB, qua HTTP API (SQLite in-memory)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("INCREMENTAL_SYNC_CONNECTOR", "simulated")

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.event_publisher import LoggingEventPublisher  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _create_data_source(code, source_system="MISA"):
    resp = client.post(
        "/data-sources",
        json={
            "code": code,
            "name": f"Nguồn dữ liệu test UC-25 ({source_system})",
            "source_system": source_system,
            "provider": "Đơn vị cung cấp phần mềm",
            "owner": "Cục CNTT",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _basic_schema_fields():
    return [
        {"name": "id", "data_type": "BIGINT", "nullable": False, "description": "Khoá chính"},
        {"name": "so_tien", "data_type": "DECIMAL", "nullable": False, "description": ""},
    ]


def _create_dataset(data_source_id, code):
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": data_source_id,
            "code": code,
            "name": "Tập dữ liệu test UC-25",
            "schema_fields": _basic_schema_fields(),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_connection(data_source_id, connection_type="API"):
    resp = client.post(
        "/source-connections",
        json={
            "data_source_id": data_source_id,
            "connection_type": connection_type,
            "config": {"base_url": "https://example-erp.local/api"},
            "credentials": {"api_key": "test-key"},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _new_ready_dataset(prefix, source_system="MISA", connection_type="API"):
    """Tạo sẵn 1 nguồn (MISA/QL_GIA/PMSTT) + 1 kết nối API/DB + 1 dataset —
    đủ điều kiện để chạy đồng bộ tăng dần."""
    data_source_id = _create_data_source(f"{prefix}-SRC", source_system=source_system)
    _create_connection(data_source_id, connection_type=connection_type)
    dataset_id = _create_dataset(data_source_id, f"{prefix}-DS")
    return data_source_id, dataset_id


# ---------- Bước 1: đọc điểm kiểm tra từ ingestion.runs ----------


def test_checkpoint_is_none_before_first_sync():
    _, dataset_id = _new_ready_dataset("UC25-CKPT")
    resp = client.get(f"/incremental-sync/{dataset_id}/checkpoint")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dataset_id"] == dataset_id
    assert body["checkpoint"] is None


def test_checkpoint_returns_none_when_dataset_missing_but_run_404s():
    # get_checkpoint chỉ đọc ingestion.runs (không kiểm tra dataset tồn tại)
    # -> trả về checkpoint=None thay vì lỗi, để endpoint xem checkpoint đơn
    # giản; việc kiểm tra dataset tồn tại thật sự nằm ở kích hoạt chạy.
    resp = client.get("/incremental-sync/999999/checkpoint")
    assert resp.status_code == 200
    assert resp.json()["checkpoint"] is None

    resp2 = client.post("/incremental-sync/999999/run", json={})
    assert resp2.status_code == 404
    assert resp2.json()["detail"]["code"] == "DATASET_NOT_FOUND"


# ---------- Bước 1-4: chạy 1 phiên đồng bộ tăng dần ----------


def test_run_sync_success_creates_incremental_run_and_advances_checkpoint():
    LoggingEventPublisher.published.clear()
    _, dataset_id = _new_ready_dataset("UC25-RUN")

    resp = client.post(f"/incremental-sync/{dataset_id}/run", json={})
    assert resp.status_code == 201, resp.text
    run = resp.json()

    assert run["dataset_id"] == dataset_id
    assert run["sync_mode"] == "INCREMENTAL"
    assert run["trigger"] == "SCHEDULED"
    assert run["status"] == "SUCCESS"
    assert run["records_read"] == 3  # SimulatedIncrementalConnector.batch_size mặc định
    assert run["records_loaded"] == 3
    assert run["control_totals"]["last_synced_updated_at"] is not None
    assert run["control_totals"]["checkpoint_before"] is None
    assert run["control_totals"]["raw_object_key"] is not None
    assert any("Bộ điều phối đọc điểm kiểm tra" in e["message"] for e in run["log_entries"])
    assert any("đã lưu raw vào MinIO" in e["message"] for e in run["log_entries"])

    # Điểm kiểm tra đã được cập nhật, tra cứu lại phải khớp.
    ckpt_resp = client.get(f"/incremental-sync/{dataset_id}/checkpoint")
    assert ckpt_resp.status_code == 200
    assert ckpt_resp.json()["checkpoint"] == run["control_totals"]["last_synced_updated_at"]

    # Bước 4: sự kiện parsing.requested đã được đẩy đi (LoggingEventPublisher
    # dùng chung buffer trong tiến trình test).
    published_events = [e for e in LoggingEventPublisher.published if e["event_name"] == "parsing.requested"]
    assert len(published_events) == 1
    assert published_events[0]["payload"]["dataset_id"] == dataset_id
    assert published_events[0]["payload"]["record_count"] == 3
    assert published_events[0]["payload"]["ingestion_run_id"] == run["id"]


def test_run_sync_twice_advances_checkpoint_further_each_time():
    _, dataset_id = _new_ready_dataset("UC25-TWICE")

    first = client.post(f"/incremental-sync/{dataset_id}/run", json={}).json()
    second = client.post(f"/incremental-sync/{dataset_id}/run", json={}).json()

    first_checkpoint = first["control_totals"]["last_synced_updated_at"]
    second_checkpoint = second["control_totals"]["last_synced_updated_at"]
    assert second["control_totals"]["checkpoint_before"] == first_checkpoint
    assert second_checkpoint > first_checkpoint
    assert second["records_read"] == 3


def test_run_sync_applies_to_ql_gia_and_pmstt():
    for source_system in ("QL_GIA", "PMSTT"):
        _, dataset_id = _new_ready_dataset(f"UC25-{source_system}", source_system=source_system)
        resp = client.post(f"/incremental-sync/{dataset_id}/run", json={})
        assert resp.status_code == 201, resp.text
        assert resp.json()["status"] == "SUCCESS"


def test_run_sync_404_when_dataset_missing():
    resp = client.post("/incremental-sync/999999/run", json={})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATASET_NOT_FOUND"


def test_run_sync_409_when_source_system_not_supported():
    """UC-025 chỉ áp dụng cho MISA/QL Giá/PMSTT — TABMIS/QLVBĐH bị từ chối."""
    data_source_id = _create_data_source("UC25-TABMIS-SRC", source_system="TABMIS")
    dataset_id = _create_dataset(data_source_id, "UC25-TABMIS-DS")

    resp = client.post(f"/incremental-sync/{dataset_id}/run", json={})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INCREMENTAL_SYNC_SOURCE_SYSTEM_NOT_SUPPORTED"


def test_run_sync_409_when_no_api_db_connection_configured():
    """Vd MISA khi nhà cung cấp CHƯA cho phép kết nối API -> chưa cấu hình
    source-connection API/DB nào -> không thể đồng bộ tăng dần."""
    data_source_id = _create_data_source("UC25-NOCONN-SRC", source_system="MISA")
    dataset_id = _create_dataset(data_source_id, "UC25-NOCONN-DS")

    resp = client.post(f"/incremental-sync/{dataset_id}/run", json={})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INCREMENTAL_SYNC_CONNECTION_NOT_CONFIGURED"


def test_run_sync_ignores_file_type_connection():
    """Kết nối kiểu FILE không tính là kết nối API/DB cho UC-025."""
    data_source_id = _create_data_source("UC25-FILECONN-SRC", source_system="QL_GIA")
    client.post(
        "/source-connections",
        json={
            "data_source_id": data_source_id,
            "connection_type": "FILE",
            "config": {"path": "/mnt/qlgia"},
            "credentials": {},
        },
    )
    dataset_id = _create_dataset(data_source_id, "UC25-FILECONN-DS")

    resp = client.post(f"/incremental-sync/{dataset_id}/run", json={})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INCREMENTAL_SYNC_CONNECTION_NOT_CONFIGURED"


def test_run_sync_409_when_already_running_incremental_for_same_dataset():
    """Khoá chống trùng: không cho 2 phiên INCREMENTAL cùng RUNNING cho
    cùng 1 dataset — mô phỏng bằng cách bắt đầu thẳng 1 phiên RUNNING qua
    endpoint UC-020 (giống cách test_uc021 mô phỏng khoá chống trùng)."""
    _, dataset_id = _new_ready_dataset("UC25-LOCK")
    start_resp = client.post(
        "/ingestion-runs",
        json={"dataset_id": dataset_id, "trigger": "SCHEDULED", "sync_mode": "INCREMENTAL"},
    )
    assert start_resp.status_code == 201, start_resp.text

    resp = client.post(f"/incremental-sync/{dataset_id}/run", json={})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INCREMENTAL_SYNC_ALREADY_RUNNING"


def test_run_sync_manual_trigger_and_scheduled_task_id():
    data_source_id, dataset_id = _new_ready_dataset("UC25-MANUAL")
    task_resp = client.post(
        "/scheduled-tasks",
        json={
            "dataset_id": dataset_id,
            "code": "UC25-MANUAL-TASK",
            "name": "Tác vụ đồng bộ tăng dần test UC-25",
            "sync_mode": "INCREMENTAL",
            "cron_expression": "*/5 * * * *",
        },
    )
    assert task_resp.status_code == 201, task_resp.text
    task_id = task_resp.json()["id"]

    resp = client.post(
        f"/incremental-sync/{dataset_id}/run",
        json={"scheduled_task_id": task_id, "trigger": "MANUAL"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["trigger"] == "MANUAL"
    assert body["scheduled_task_id"] == task_id


def test_run_sync_no_event_published_when_connector_returns_no_changes(monkeypatch):
    """Khi bộ kết nối không có dữ liệu mới: vẫn ghi phiên SUCCESS + giữ
    nguyên checkpoint, nhưng KHÔNG lưu tệp raw + KHÔNG phát sự kiện."""
    from app.infrastructure import incremental_connector as connector_module

    _, dataset_id = _new_ready_dataset("UC25-NOCHANGE")
    monkeypatch.setenv("INCREMENTAL_SYNC_CONNECTOR", "noop")
    try:
        LoggingEventPublisher.published.clear()
        resp = client.post(f"/incremental-sync/{dataset_id}/run", json={})
        assert resp.status_code == 201, resp.text
        run = resp.json()
        assert run["status"] == "SUCCESS"
        assert run["records_read"] == 0
        assert run["control_totals"]["raw_object_key"] is None
        assert run["control_totals"]["last_synced_updated_at"] is None
        assert not [e for e in LoggingEventPublisher.published if e["event_name"] == "parsing.requested"]
    finally:
        monkeypatch.setenv("INCREMENTAL_SYNC_CONNECTOR", "simulated")
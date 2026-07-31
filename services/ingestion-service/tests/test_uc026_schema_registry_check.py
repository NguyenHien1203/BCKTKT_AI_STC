"""Integration test UC-026: Kiểm tra Schema Registry, qua HTTP API (SQLite in-memory)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.event_publisher import LoggingEventPublisher  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _create_data_source(code):
    resp = client.post(
        "/data-sources",
        json={
            "code": code,
            "name": "Nguồn dữ liệu test UC-26",
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
        {"name": "so_tien", "data_type": "DECIMAL", "nullable": True, "description": ""},
    ]


def _define_dataset(data_source_id, code):
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": data_source_id,
            "code": code,
            "name": "Tập dữ liệu test UC-26",
            "schema_fields": _basic_schema_fields(),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _register_schema_version(dataset_id):
    resp = client.post(
        f"/datasets/{dataset_id}/partitioning",
        json={"primary_key": ["id"], "partition_strategy": "NONE"},
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/datasets/{dataset_id}/schema-versions")
    assert resp.status_code == 201, resp.text
    return resp.json()["version"]


def _new_registered_dataset(prefix):
    """Tạo sẵn 1 dataset đã đăng ký lược đồ v1 vào Schema Registry (UC-018
    bước 4) — điều kiện cần để UC-026 có gì đối chiếu."""
    data_source_id = _create_data_source(f"{prefix}-SRC")
    dataset = _define_dataset(data_source_id, f"{prefix}-DS")
    version = _register_schema_version(dataset["id"])
    return dataset["id"], version


# ---------- Bước 1: chưa từng đăng ký lược đồ ----------


def test_check_returns_409_when_no_schema_registered():
    data_source_id = _create_data_source("UC26-NOREG-SRC")
    dataset = _define_dataset(data_source_id, "UC26-NOREG-DS")
    resp = client.post(
        f"/schema-registry/{dataset['id']}/check",
        json={"schema_fields": _basic_schema_fields()},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "SCHEMA_NOT_REGISTERED_FOR_CHECK"


def test_check_dataset_not_found_returns_404():
    resp = client.post(
        "/schema-registry/999999/check",
        json={"schema_fields": _basic_schema_fields()},
    )
    assert resp.status_code == 404


def test_check_empty_incoming_fields_returns_422():
    dataset_id, _ = _new_registered_dataset("UC26-EMPTY")
    resp = client.post(f"/schema-registry/{dataset_id}/check", json={"schema_fields": []})
    assert resp.status_code == 422


# ---------- Bước 2-3: lược đồ tương thích (chỉ bổ sung trường mới) ----------


def test_check_compatible_when_only_fields_added():
    dataset_id, version = _new_registered_dataset("UC26-COMPAT")
    incoming = _basic_schema_fields() + [
        {"name": "ghi_chu", "data_type": "STRING", "nullable": True, "description": ""}
    ]
    resp = client.post(
        f"/schema-registry/{dataset_id}/check", json={"schema_fields": incoming}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "COMPATIBLE"
    assert body["allowed"] is True
    assert body["registered_version"] == version
    assert body["added_fields"] == ["ghi_chu"]
    assert body["removed_fields"] == []
    assert body["changed_type_fields"] == []


def test_check_compatible_when_identical_schema():
    dataset_id, _ = _new_registered_dataset("UC26-SAME")
    resp = client.post(
        f"/schema-registry/{dataset_id}/check",
        json={"schema_fields": _basic_schema_fields()},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "COMPATIBLE"
    assert body["allowed"] is True
    assert body["added_fields"] == []


def test_check_compatible_does_not_publish_alert_event():
    dataset_id, _ = _new_registered_dataset("UC26-NOALERT")
    before = len(LoggingEventPublisher.published)
    resp = client.post(
        f"/schema-registry/{dataset_id}/check",
        json={"schema_fields": _basic_schema_fields()},
    )
    assert resp.status_code == 201
    assert len(LoggingEventPublisher.published) == before


# ---------- Bước 2: lược đồ phá vỡ tương thích ----------


def test_check_breaking_when_field_removed():
    dataset_id, version = _new_registered_dataset("UC26-REMOVED")
    incoming = [f for f in _basic_schema_fields() if f["name"] != "so_tien"]
    resp = client.post(
        f"/schema-registry/{dataset_id}/check", json={"schema_fields": incoming}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "BREAKING"
    assert body["allowed"] is False
    assert body["registered_version"] == version
    assert body["removed_fields"] == ["so_tien"]


def test_check_breaking_when_field_type_changed():
    dataset_id, _ = _new_registered_dataset("UC26-RETYPE")
    incoming = [
        {**f, "data_type": "STRING"} if f["name"] == "so_tien" else f
        for f in _basic_schema_fields()
    ]
    resp = client.post(
        f"/schema-registry/{dataset_id}/check", json={"schema_fields": incoming}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "BREAKING"
    assert body["allowed"] is False
    assert body["changed_type_fields"] == [
        {"name": "so_tien", "old_type": "DECIMAL", "new_type": "STRING"}
    ]


def test_check_breaking_publishes_alert_event_for_integration_admin():
    dataset_id, _ = _new_registered_dataset("UC26-ALERT")
    incoming = [f for f in _basic_schema_fields() if f["name"] != "ma_don_vi"]
    before = len(LoggingEventPublisher.published)
    resp = client.post(
        f"/schema-registry/{dataset_id}/check", json={"schema_fields": incoming}
    )
    assert resp.status_code == 201
    check_id = resp.json()["id"]
    published = LoggingEventPublisher.published[before:]
    assert len(published) == 1
    event = published[0]
    assert event["event_name"] == "schema_registry.compatibility_broken"
    assert event["payload"]["dataset_id"] == dataset_id
    assert event["payload"]["schema_registry_check_id"] == check_id
    assert event["payload"]["removed_fields"] == ["ma_don_vi"]


# ---------- Xem lịch sử kiểm tra ----------


def test_list_checks_history_newest_first_and_filter_by_status():
    dataset_id, _ = _new_registered_dataset("UC26-HIST")
    client.post(
        f"/schema-registry/{dataset_id}/check", json={"schema_fields": _basic_schema_fields()}
    )
    incoming_breaking = [f for f in _basic_schema_fields() if f["name"] != "so_tien"]
    client.post(
        f"/schema-registry/{dataset_id}/check", json={"schema_fields": incoming_breaking}
    )

    resp = client.get(f"/schema-registry/{dataset_id}/checks")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["status"] == "BREAKING"  # mới nhất trước
    assert body[1]["status"] == "COMPATIBLE"

    resp_filtered = client.get(
        f"/schema-registry/{dataset_id}/checks", params={"status": "BREAKING"}
    )
    assert resp_filtered.status_code == 200
    filtered_body = resp_filtered.json()
    assert len(filtered_body) == 1
    assert filtered_body[0]["status"] == "BREAKING"


def test_list_checks_dataset_not_found_returns_404():
    resp = client.get("/schema-registry/999999/checks")
    assert resp.status_code == 404


def test_get_check_detail_and_not_found():
    dataset_id, _ = _new_registered_dataset("UC26-DETAIL")
    resp = client.post(
        f"/schema-registry/{dataset_id}/check", json={"schema_fields": _basic_schema_fields()}
    )
    check_id = resp.json()["id"]

    detail = client.get(f"/schema-registry/checks/{check_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == check_id

    not_found = client.get("/schema-registry/checks/999999")
    assert not_found.status_code == 404
    assert not_found.json()["detail"]["code"] == "SCHEMA_REGISTRY_CHECK_NOT_FOUND"


def test_check_records_ingestion_run_id_when_provided():
    dataset_id, _ = _new_registered_dataset("UC26-RUNID")
    resp = client.post(
        f"/schema-registry/{dataset_id}/check",
        json={"schema_fields": _basic_schema_fields(), "ingestion_run_id": 42},
    )
    assert resp.status_code == 201
    assert resp.json()["ingestion_run_id"] == 42
"""Integration test UC-018 qua HTTP API, dùng SQLite in-memory."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_data_source(code="UC18-SRC-01"):
    resp = client.post(
        "/data-sources",
        json={
            "code": code,
            "name": "Nguồn dữ liệu test UC-18",
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
        {"name": "ngay_ghi_so", "data_type": "DATE", "nullable": True, "description": ""},
    ]


def _define_dataset(data_source_id, code="UC18-DS-01"):
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": data_source_id,
            "code": code,
            "name": "Sổ cái ngân sách",
            "description": "Dữ liệu sổ cái ngân sách từ TABMIS",
            "schema_fields": _basic_schema_fields(),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Bước 1: Định nghĩa tập dữ liệu + lược đồ ----------


def test_define_dataset_saves_schema():
    data_source_id = _create_data_source("UC18-SRC-DEFINE")
    body = _define_dataset(data_source_id, "UC18-DS-DEFINE")
    assert body["code"] == "UC18-DS-DEFINE"
    assert len(body["schema_fields"]) == 4
    assert body["primary_key"] == []
    assert body["partition_strategy"] == "NONE"
    assert body["current_schema_version"] == 0
    assert body["is_active"] is True


def test_define_dataset_invalid_data_source_returns_404():
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": 999999,
            "code": "X",
            "name": "X",
            "schema_fields": _basic_schema_fields(),
        },
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_NOT_FOUND"


def test_define_dataset_duplicate_code_returns_409():
    data_source_id = _create_data_source("UC18-SRC-DUP")
    _define_dataset(data_source_id, "UC18-DS-DUP")
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": data_source_id,
            "code": "UC18-DS-DUP",
            "name": "Trùng mã",
            "schema_fields": _basic_schema_fields(),
        },
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "DATASET_CODE_EXISTS"


def test_define_dataset_invalid_data_type_returns_422():
    data_source_id = _create_data_source("UC18-SRC-BADTYPE")
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": data_source_id,
            "code": "UC18-DS-BADTYPE",
            "name": "Kiểu sai",
            "schema_fields": [{"name": "x", "data_type": "TEXT_KHONG_HOP_LE"}],
        },
    )
    assert resp.status_code == 422


def test_define_dataset_empty_schema_returns_422():
    data_source_id = _create_data_source("UC18-SRC-EMPTY")
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": data_source_id,
            "code": "UC18-DS-EMPTY",
            "name": "Rỗng",
            "schema_fields": [],
        },
    )
    assert resp.status_code == 422


def test_update_dataset_schema_resets_primary_key_if_field_removed():
    data_source_id = _create_data_source("UC18-SRC-RESCHEMA")
    dataset = _define_dataset(data_source_id, "UC18-DS-RESCHEMA")
    client.post(
        f"/datasets/{dataset['id']}/partitioning",
        json={"primary_key": ["id"], "partition_strategy": "NONE"},
    )
    # Định nghĩa lại lược đồ bỏ trường "id" -> khoá chính bị reset.
    resp = client.put(
        f"/datasets/{dataset['id']}/schema",
        json={
            "schema_fields": [
                {"name": "ma_don_vi", "data_type": "STRING", "nullable": False},
            ]
        },
    )
    assert resp.status_code == 200
    assert resp.json()["primary_key"] == []


def test_get_dataset_not_found_returns_404():
    resp = client.get("/datasets/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATASET_NOT_FOUND"


def test_list_and_filter_datasets_by_data_source():
    data_source_id = _create_data_source("UC18-SRC-LIST")
    _define_dataset(data_source_id, "UC18-DS-LIST")
    resp = client.get("/datasets", params={"data_source_id": data_source_id})
    assert resp.status_code == 200
    assert all(d["data_source_id"] == data_source_id for d in resp.json())


# ---------- Bước 2: Khoá chính + chiến lược phân mảnh ----------


def test_configure_partitioning_saves_primary_key_and_strategy():
    data_source_id = _create_data_source("UC18-SRC-PART")
    dataset = _define_dataset(data_source_id, "UC18-DS-PART")
    resp = client.post(
        f"/datasets/{dataset['id']}/partitioning",
        json={
            "primary_key": ["id"],
            "partition_strategy": "RANGE",
            "partition_column": "ngay_ghi_so",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["primary_key"] == ["id"]
    assert body["partition_strategy"] == "RANGE"
    assert body["partition_column"] == "ngay_ghi_so"


def test_configure_partitioning_unknown_primary_key_field_returns_409():
    data_source_id = _create_data_source("UC18-SRC-PART-BADPK")
    dataset = _define_dataset(data_source_id, "UC18-DS-PART-BADPK")
    resp = client.post(
        f"/datasets/{dataset['id']}/partitioning",
        json={"primary_key": ["truong_khong_ton_tai"], "partition_strategy": "NONE"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INVALID_DATASET"


def test_configure_partitioning_missing_partition_column_returns_409():
    data_source_id = _create_data_source("UC18-SRC-PART-NOCOL")
    dataset = _define_dataset(data_source_id, "UC18-DS-PART-NOCOL")
    resp = client.post(
        f"/datasets/{dataset['id']}/partitioning",
        json={"primary_key": ["id"], "partition_strategy": "HASH"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INVALID_DATASET"


def test_configure_partitioning_not_found_returns_404():
    resp = client.post(
        "/datasets/999999/partitioning",
        json={"primary_key": ["id"], "partition_strategy": "NONE"},
    )
    assert resp.status_code == 404


# ---------- Bước 3: Trường bắt buộc (NOT NULL) ----------


def test_declare_critical_fields_saves_and_lists():
    data_source_id = _create_data_source("UC18-SRC-CRIT")
    dataset = _define_dataset(data_source_id, "UC18-DS-CRIT")
    resp = client.post(
        f"/datasets/{dataset['id']}/critical-fields",
        json={"field_names": ["id", "ma_don_vi"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {f["field_name"] for f in body} == {"id", "ma_don_vi"}

    list_resp = client.get(f"/datasets/{dataset['id']}/critical-fields")
    assert list_resp.status_code == 200
    assert {f["field_name"] for f in list_resp.json()} == {"id", "ma_don_vi"}


def test_declare_critical_fields_is_idempotent_replace():
    data_source_id = _create_data_source("UC18-SRC-CRIT-REPL")
    dataset = _define_dataset(data_source_id, "UC18-DS-CRIT-REPL")
    client.post(
        f"/datasets/{dataset['id']}/critical-fields",
        json={"field_names": ["id", "ma_don_vi"]},
    )
    resp = client.post(
        f"/datasets/{dataset['id']}/critical-fields",
        json={"field_names": ["so_tien"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {f["field_name"] for f in body} == {"so_tien"}


def test_declare_critical_fields_unknown_field_returns_409():
    data_source_id = _create_data_source("UC18-SRC-CRIT-BAD")
    dataset = _define_dataset(data_source_id, "UC18-DS-CRIT-BAD")
    resp = client.post(
        f"/datasets/{dataset['id']}/critical-fields",
        json={"field_names": ["truong_khong_ton_tai"]},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INVALID_DATASET"


# ---------- Bước 4: Đăng ký Schema Registry ----------


def test_register_schema_requires_primary_key_declared_first():
    data_source_id = _create_data_source("UC18-SRC-REG-NOPK")
    dataset = _define_dataset(data_source_id, "UC18-DS-REG-NOPK")
    resp = client.post(f"/datasets/{dataset['id']}/schema-versions")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INVALID_DATASET"


def test_register_schema_creates_version_and_snapshot():
    data_source_id = _create_data_source("UC18-SRC-REG")
    dataset = _define_dataset(data_source_id, "UC18-DS-REG")
    client.post(
        f"/datasets/{dataset['id']}/partitioning",
        json={"primary_key": ["id"], "partition_strategy": "NONE"},
    )
    client.post(
        f"/datasets/{dataset['id']}/critical-fields",
        json={"field_names": ["id", "ma_don_vi"]},
    )

    resp = client.post(f"/datasets/{dataset['id']}/schema-versions")
    assert resp.status_code == 201
    body = resp.json()
    assert body["version"] == 1
    assert body["schema_snapshot"]["primary_key"] == ["id"]
    assert set(body["schema_snapshot"]["critical_fields"]) == {"id", "ma_don_vi"}
    assert len(body["schema_snapshot"]["schema_fields"]) == 4

    # Đăng ký lần 2 -> tăng phiên bản lên 2, dataset cập nhật current_schema_version.
    resp2 = client.post(f"/datasets/{dataset['id']}/schema-versions")
    assert resp2.status_code == 201
    assert resp2.json()["version"] == 2

    dataset_after = client.get(f"/datasets/{dataset['id']}").json()
    assert dataset_after["current_schema_version"] == 2


def test_list_and_get_schema_versions():
    data_source_id = _create_data_source("UC18-SRC-REG-LIST")
    dataset = _define_dataset(data_source_id, "UC18-DS-REG-LIST")
    client.post(
        f"/datasets/{dataset['id']}/partitioning",
        json={"primary_key": ["id"], "partition_strategy": "NONE"},
    )
    client.post(f"/datasets/{dataset['id']}/schema-versions")
    client.post(f"/datasets/{dataset['id']}/schema-versions")

    list_resp = client.get(f"/datasets/{dataset['id']}/schema-versions")
    assert list_resp.status_code == 200
    versions = [v["version"] for v in list_resp.json()]
    assert versions == [2, 1]  # mới nhất trước

    get_resp = client.get(f"/datasets/{dataset['id']}/schema-versions/1")
    assert get_resp.status_code == 200
    assert get_resp.json()["version"] == 1

    not_found = client.get(f"/datasets/{dataset['id']}/schema-versions/999")
    assert not_found.status_code == 404
    assert not_found.json()["detail"]["code"] == "SCHEMA_VERSION_NOT_FOUND"


# ---------- Vòng đời chung ----------


def test_deactivate_and_activate_dataset():
    data_source_id = _create_data_source("UC18-SRC-TOGGLE")
    dataset = _define_dataset(data_source_id, "UC18-DS-TOGGLE")

    resp = client.post(f"/datasets/{dataset['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    resp2 = client.post(f"/datasets/{dataset['id']}/activate")
    assert resp2.status_code == 200
    assert resp2.json()["is_active"] is True
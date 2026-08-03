"""Integration test UC-031: Ánh xạ trường sang dạng chuẩn, qua HTTP API (SQLite in-memory)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.file_storage import get_raw_data_storage  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _schema_fields():
    return [
        {"name": "ma_don_vi", "data_type": "STRING", "nullable": False},
        {"name": "loai_don_vi", "data_type": "STRING", "nullable": True},
        {"name": "so_tien", "data_type": "DECIMAL", "nullable": False},
        {"name": "ngay_ghi_so", "data_type": "DATE", "nullable": True},
    ]


def _store_raw(key: str, content: bytes) -> None:
    get_raw_data_storage().upload(key, content, "text/csv")


def _create_parsing_job(dataset_id: int, key: str, csv_content: str) -> dict:
    """Tạo 1 ParsingJob (UC-029) đã MAPPED, làm dữ liệu đầu vào cho UC-031."""
    _store_raw(key, csv_content.encode("utf-8"))
    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": dataset_id,
            "raw_object_key": key,
            "schema_fields": _schema_fields(),
            "source_format": "CSV",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_rule(**kwargs) -> dict:
    resp = client.post("/mapping-rules", json=kwargs)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Bước 1: Tra cứu quy tắc ánh xạ (có phiên bản) + tra cứu danh mục chuẩn ----------


def test_mapping_rule_catalog_lookup_applies_and_versioning():
    dataset_id = 101
    # v1 ánh xạ sai để kiểm tra hệ thống chọn version lớn nhất đang active.
    _create_rule(
        field_name="loai_don_vi",
        version=1,
        rule_type="CATALOG_LOOKUP",
        dataset_id=dataset_id,
        catalog_map={"SO": "SO_KHONG_DUNG"},
    )
    _create_rule(
        field_name="loai_don_vi",
        version=2,
        rule_type="CATALOG_LOOKUP",
        dataset_id=dataset_id,
        catalog_map={"SO": "Sở", "PHONG": "Phòng"},
    )

    key = "uc31/csv/catalog.csv"
    csv_content = (
        "ma_don_vi,loai_don_vi,so_tien,ngay_ghi_so\n"
        "DV001,so,1000000,2026-01-15\n"
    )
    parsing_job = _create_parsing_job(dataset_id, key, csv_content)

    resp = client.post("/mapping-jobs", json={"parsing_job_id": parsing_job["id"]})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["records_total"] == 1
    assert body["records_mapped"] == 1
    assert body["records_rejected"] == 0
    assert body["unmapped_values_count"] == 0

    records = client.get(f"/mapping-jobs/{body['id']}/standard-records").json()
    assert len(records) == 1
    assert records[0]["standardized_fields"]["loai_don_vi"] == "Sở"


def test_mapping_rule_direct_normalize_case():
    dataset_id = 102
    _create_rule(
        field_name="ma_don_vi",
        version=1,
        rule_type="DIRECT",
        dataset_id=dataset_id,
        normalize_case="UPPER",
    )

    key = "uc31/csv/direct.csv"
    csv_content = "ma_don_vi,loai_don_vi,so_tien,ngay_ghi_so\n dv002 ,Phong,500000,2026-02-01\n"
    parsing_job = _create_parsing_job(dataset_id, key, csv_content)

    resp = client.post("/mapping-jobs", json={"parsing_job_id": parsing_job["id"]})
    body = resp.json()
    records = client.get(f"/mapping-jobs/{body['id']}/standard-records").json()
    assert records[0]["standardized_fields"]["ma_don_vi"] == "DV002"


# ---------- Bước 2: Từ chối trường bắt buộc bị NULL ----------


def test_reject_row_when_required_field_null_after_normalization():
    dataset_id = 103
    # Quy tắc catalog lookup cho trường bắt buộc ma_don_vi -- giá trị
    # nguồn không khớp catalog_map -> chuẩn hoá ra None -> phải bị từ chối.
    _create_rule(
        field_name="ma_don_vi",
        version=1,
        rule_type="CATALOG_LOOKUP",
        dataset_id=dataset_id,
        catalog_map={"DV999": "DV999-CHUAN"},
    )

    key = "uc31/csv/reject.csv"
    csv_content = (
        "ma_don_vi,loai_don_vi,so_tien,ngay_ghi_so\n"
        "DV999,Phong,1000000,2026-01-01\n"
        "DV_KHONG_KHOP,Phong,2000000,2026-01-02\n"
    )
    parsing_job = _create_parsing_job(dataset_id, key, csv_content)

    resp = client.post("/mapping-jobs", json={"parsing_job_id": parsing_job["id"]})
    body = resp.json()
    assert body["records_total"] == 2
    assert body["records_mapped"] == 1
    assert body["records_rejected"] == 1
    assert body["unmapped_values_count"] == 1

    rejections = client.get(f"/mapping-jobs/{body['id']}/rejections").json()
    assert len(rejections) == 1
    assert rejections[0]["field_name"] == "ma_don_vi"
    assert rejections[0]["row_index"] == 1

    records = client.get(f"/mapping-jobs/{body['id']}/standard-records").json()
    assert len(records) == 1
    assert records[0]["standardized_fields"]["ma_don_vi"] == "DV999-CHUAN"


# ---------- Bước 3: Đẩy giá trị chưa ánh xạ vào hàng đợi ----------


def test_unmapped_value_pushed_to_queue_without_rejecting_row():
    dataset_id = 104
    # loai_don_vi không phải trường bắt buộc -> giá trị không khớp catalog
    # chỉ đẩy vào hàng đợi, KHÔNG làm từ chối cả dòng.
    _create_rule(
        field_name="loai_don_vi",
        version=1,
        rule_type="CATALOG_LOOKUP",
        dataset_id=dataset_id,
        catalog_map={"SO": "Sở"},
    )

    key = "uc31/csv/unmapped.csv"
    csv_content = (
        "ma_don_vi,loai_don_vi,so_tien,ngay_ghi_so\n"
        "DV010,Xa,1500000,2026-03-01\n"
    )
    parsing_job = _create_parsing_job(dataset_id, key, csv_content)

    resp = client.post("/mapping-jobs", json={"parsing_job_id": parsing_job["id"]})
    body = resp.json()
    assert body["records_mapped"] == 1
    assert body["records_rejected"] == 0
    assert body["unmapped_values_count"] == 1

    queue = client.get(f"/mapping-jobs/{body['id']}/unmapped-queue").json()
    assert len(queue) == 1
    assert queue[0]["field_name"] == "loai_don_vi"
    assert queue[0]["raw_value"].lower() == "xa"
    assert queue[0]["status"] == "PENDING"
    assert queue[0]["dataset_id"] == dataset_id

    records = client.get(f"/mapping-jobs/{body['id']}/standard-records").json()
    assert records[0]["standardized_fields"]["loai_don_vi"] is None


# ---------- Trường không có quy tắc: giữ nguyên giá trị (pass-through) ----------


def test_field_without_rule_is_passed_through_unchanged():
    dataset_id = 105
    key = "uc31/csv/passthrough.csv"
    csv_content = "ma_don_vi,loai_don_vi,so_tien,ngay_ghi_so\nDV020,Phong,999,2026-04-01\n"
    parsing_job = _create_parsing_job(dataset_id, key, csv_content)

    resp = client.post("/mapping-jobs", json={"parsing_job_id": parsing_job["id"]})
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["unmapped_values_count"] == 0

    records = client.get(f"/mapping-jobs/{body['id']}/standard-records").json()
    assert records[0]["standardized_fields"]["ma_don_vi"] == "DV020"
    assert records[0]["standardized_fields"]["so_tien"] == 999.0


# ---------- Danh sách + not found ----------


def test_list_mapping_jobs_filters_and_not_found():
    dataset_id = 106
    key = "uc31/csv/list.csv"
    csv_content = "ma_don_vi,loai_don_vi,so_tien,ngay_ghi_so\nDV030,Phong,111,2026-05-01\n"
    parsing_job = _create_parsing_job(dataset_id, key, csv_content)
    created = client.post("/mapping-jobs", json={"parsing_job_id": parsing_job["id"]}).json()

    listed = client.get("/mapping-jobs", params={"dataset_id": dataset_id}).json()
    assert any(j["id"] == created["id"] for j in listed)

    listed_by_parsing = client.get(
        "/mapping-jobs", params={"parsing_job_id": parsing_job["id"]}
    ).json()
    assert len(listed_by_parsing) == 1

    resp_404 = client.get("/mapping-jobs/999999")
    assert resp_404.status_code == 404

    resp_404_rejections = client.get("/mapping-jobs/999999/rejections")
    assert resp_404_rejections.status_code == 404


def test_mapping_requested_for_unknown_parsing_job_returns_404():
    resp = client.post("/mapping-jobs", json={"parsing_job_id": 999999})
    assert resp.status_code == 404


def test_mapping_requested_when_no_parsed_records_returns_failed_job():
    """parsing_job tồn tại nhưng KHÔNG có bản ghi hợp lệ nào (has_error=False)
    -- job phải FAILED thay vì raise lỗi HTTP."""
    dataset_id = 107
    key = "uc31/csv/all_failed.csv"
    # so_tien không ép kiểu được (không phải số) -> toàn bộ dòng lỗi ->
    # parsing_job FAILED, không có parsed record has_error=False nào.
    csv_content = "ma_don_vi,loai_don_vi,so_tien,ngay_ghi_so\nDV040,Phong,khong_phai_so,2026-06-01\n"
    _store_raw(key, csv_content.encode("utf-8"))
    parsing_resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": dataset_id,
            "raw_object_key": key,
            "schema_fields": _schema_fields(),
            "source_format": "CSV",
        },
    )
    parsing_job = parsing_resp.json()
    assert parsing_job["status"] == "FAILED"

    resp = client.post("/mapping-jobs", json={"parsing_job_id": parsing_job["id"]})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert body["records_total"] == 0


# ---------- Quản lý quy tắc ánh xạ ----------


def test_create_mapping_rule_validation_errors():
    # CATALOG_LOOKUP thiếu catalog_map -> lỗi 422.
    resp = client.post(
        "/mapping-rules",
        json={"field_name": "x", "version": 1, "rule_type": "CATALOG_LOOKUP", "catalog_map": {}},
    )
    assert resp.status_code == 422

    # rule_type không hợp lệ -> lỗi 422.
    resp = client.post(
        "/mapping-rules",
        json={"field_name": "x", "version": 1, "rule_type": "KHONG_HOP_LE"},
    )
    assert resp.status_code == 422


def test_list_mapping_rules_filters():
    _create_rule(field_name="field_a", version=1, rule_type="DIRECT", dataset_id=201)
    _create_rule(field_name="field_a", version=2, rule_type="DIRECT", dataset_id=201)
    rules = client.get("/mapping-rules", params={"dataset_id": 201, "field_name": "field_a"}).json()
    assert len(rules) == 2
    assert {r["version"] for r in rules} == {1, 2}
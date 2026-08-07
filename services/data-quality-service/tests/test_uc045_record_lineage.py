"""Integration test UC-045: Truy vết nguồn gốc bản ghi, qua HTTP API

(SQLite in-memory). Actor "Kiểm toán viên". Luồng:
1. Chọn bản ghi curated. Hệ thống hiển thị.
2. Xem nguồn gốc dữ liệu qua các bước (thô -> phân tích -> ánh xạ ->
   chất lượng -> công bố). Hệ thống hiển thị chuỗi.
3. Xem chi tiết từng bước. Hệ thống hiển thị dữ liệu vào/ra + phép
   biến đổi.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.file_storage import get_raw_data_storage  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _schema_fields():
    return [
        {"name": "ma_don_vi", "data_type": "STRING", "nullable": False},
        {"name": "ten_don_vi", "data_type": "STRING", "nullable": True},
        {"name": "so_tien", "data_type": "DECIMAL", "nullable": True},
    ]


def _store_raw(key: str, content: bytes) -> None:
    get_raw_data_storage().upload(key, content, "text/csv")


def _build_full_chain(dataset_id: int) -> dict:
    """Dựng trọn chuỗi thô -> phân tích -> ánh xạ -> chất lượng -> công

    bố cho 1 dòng dữ liệu duy nhất (row_index=0), trả về dict gồm id
    từng job + curated_dm_record."""
    key = f"uc45/csv/{dataset_id}.csv"
    csv_content = "ma_don_vi,ten_don_vi,so_tien\nDV001,Don vi A,1000000\n"
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
    parsing_job = resp.json()
    assert parsing_job["status"] == "MAPPED"

    resp = client.post("/mapping-jobs", json={"parsing_job_id": parsing_job["id"]})
    assert resp.status_code == 201, resp.text
    mapping_job = resp.json()
    assert mapping_job["status"] == "COMPLETED"

    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    quality_check_job = resp.json()
    assert quality_check_job["status"] == "PASSED"

    resp = client.post(
        "/curated-publish/jobs",
        json={"quality_check_job_id": quality_check_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    curated_publish_job = resp.json()
    assert curated_publish_job["status"] == "COMPLETED"

    resp = client.get(f"/curated-publish/jobs/{curated_publish_job['id']}/dm-records")
    assert resp.status_code == 200, resp.text
    dm_records = resp.json()
    assert len(dm_records) == 1
    curated_dm_record = dm_records[0]

    return {
        "parsing_job": parsing_job,
        "mapping_job": mapping_job,
        "quality_check_job": quality_check_job,
        "curated_publish_job": curated_publish_job,
        "curated_dm_record": curated_dm_record,
    }


# ---------- Bước 1: 'Chọn bản ghi curated' ----------


def test_chon_ban_ghi_curated_khong_ton_tai_thi_404():
    resp = client.get("/record-lineage/curated-records/999999")
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "CURATED_DM_RECORD_NOT_FOUND"


def test_chon_ban_ghi_curated_thanh_cong():
    chain = _build_full_chain(dataset_id=4501)
    dm_id = chain["curated_dm_record"]["id"]

    resp = client.get(f"/record-lineage/curated-records/{dm_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == dm_id
    assert body["dataset_id"] == 4501
    assert body["row_index"] == 0
    assert body["publish_status"] == "approved"


# ---------- Bước 2: 'Xem nguồn gốc dữ liệu qua các bước' ----------


def test_xem_chuoi_nguon_goc_du_lieu():
    chain = _build_full_chain(dataset_id=4502)
    dm_id = chain["curated_dm_record"]["id"]

    resp = client.get(f"/record-lineage/curated-records/{dm_id}/chain")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["curated_dm_record_id"] == dm_id
    assert body["dataset_id"] == 4502
    assert body["row_index"] == 0

    steps = body["steps"]
    assert [s["step"] for s in steps] == ["RAW", "PARSING", "MAPPING", "QUALITY", "PUBLISH"]
    for s in steps:
        assert s["available"] is True

    raw_step, parsing_step, mapping_step, quality_step, publish_step = steps
    assert raw_step["job_id"] == chain["parsing_job"]["id"]
    assert parsing_step["job_id"] == chain["parsing_job"]["id"]
    assert mapping_step["job_id"] == chain["mapping_job"]["id"]
    assert mapping_step["status"] == "OK"
    assert quality_step["job_id"] == chain["quality_check_job"]["id"]
    assert quality_step["status"] == "PASSED"
    assert publish_step["job_id"] == chain["curated_publish_job"]["id"]
    assert publish_step["status"] == "approved"


def test_xem_chuoi_nguon_goc_khong_ton_tai_thi_404():
    resp = client.get("/record-lineage/curated-records/999999/chain")
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "CURATED_DM_RECORD_NOT_FOUND"


# ---------- Bước 3: 'Xem chi tiết từng bước' ----------


def test_chi_tiet_buoc_raw():
    chain = _build_full_chain(dataset_id=4503)
    dm_id = chain["curated_dm_record"]["id"]

    resp = client.get(f"/record-lineage/curated-records/{dm_id}/steps/RAW")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["step"] == "RAW"
    assert body["available"] is True
    assert body["input"]["source_format"] == "CSV"
    assert body["output"]["ma_don_vi"] == "DV001"
    assert body["meta"]["parsing_job_id"] == chain["parsing_job"]["id"]


def test_chi_tiet_buoc_parsing():
    chain = _build_full_chain(dataset_id=4504)
    dm_id = chain["curated_dm_record"]["id"]

    resp = client.get(f"/record-lineage/curated-records/{dm_id}/steps/parsing")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["step"] == "PARSING"
    assert body["output"]["ma_don_vi"] == "DV001"
    assert body["output"]["so_tien"] == 1000000
    assert body["meta"]["has_error"] is False
    assert body["meta"]["row_errors"] == []


def test_chi_tiet_buoc_mapping():
    chain = _build_full_chain(dataset_id=4505)
    dm_id = chain["curated_dm_record"]["id"]

    resp = client.get(f"/record-lineage/curated-records/{dm_id}/steps/MAPPING")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["step"] == "MAPPING"
    assert body["available"] is True
    assert body["input"]["ma_don_vi"] == "DV001"
    assert body["output"]["ma_don_vi"] == "DV001"
    assert body["meta"]["mapping_job_id"] == chain["mapping_job"]["id"]
    assert body["meta"]["rejections"] == []


def test_chi_tiet_buoc_quality():
    chain = _build_full_chain(dataset_id=4506)
    dm_id = chain["curated_dm_record"]["id"]

    resp = client.get(f"/record-lineage/curated-records/{dm_id}/steps/QUALITY")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["step"] == "QUALITY"
    assert body["available"] is True
    assert body["meta"]["quality_check_job_id"] == chain["quality_check_job"]["id"]
    assert body["meta"]["overall_score"] == 100.0
    assert body["meta"]["outcome"] == "ĐẠT NGƯỠNG -- ĐÃ CÔNG BỐ"
    assert body["output"]["ma_don_vi"] == "DV001"


def test_chi_tiet_buoc_publish():
    chain = _build_full_chain(dataset_id=4507)
    dm_id = chain["curated_dm_record"]["id"]

    resp = client.get(f"/record-lineage/curated-records/{dm_id}/steps/PUBLISH")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["step"] == "PUBLISH"
    assert body["available"] is True
    assert body["output"]["publish_status"] == "approved"
    assert body["output"]["version"] == 1
    assert body["meta"]["curated_dm_record_id"] == dm_id
    assert body["meta"]["curated_publish_job_id"] == chain["curated_publish_job"]["id"]
    assert body["meta"]["batch_summary"] is not None
    assert body["meta"]["batch_summary"]["inserted_count"] == 1


def test_buoc_khong_hop_le_thi_422():
    chain = _build_full_chain(dataset_id=4508)
    dm_id = chain["curated_dm_record"]["id"]

    resp = client.get(f"/record-lineage/curated-records/{dm_id}/steps/UNKNOWN")
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_LINEAGE_STEP"


def test_chi_tiet_buoc_ban_ghi_curated_khong_ton_tai_thi_404():
    resp = client.get("/record-lineage/curated-records/999999/steps/RAW")
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "CURATED_DM_RECORD_NOT_FOUND"
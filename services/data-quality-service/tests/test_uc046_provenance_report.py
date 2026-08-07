"""Integration test UC-046: Xuất báo cáo nguồn gốc dữ liệu, qua HTTP API

(SQLite in-memory). Actor "Kiểm toán viên". Luồng:
1. Chọn phạm vi (tập dữ liệu / bản ghi / nguồn). Hệ thống hiển thị.
2. Sinh báo cáo nguồn gốc dữ liệu. Hệ thống kết xuất PDF.
3. Kết xuất PDF. Hệ thống trả file.

Tái sử dụng helper `_build_full_chain` theo đúng khuôn mẫu
`test_uc045_record_lineage.py`.
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


def _build_full_chain(dataset_id: int, data_source_id=None, row_count: int = 1) -> dict:
    """Dựng trọn chuỗi thô -> phân tích -> ánh xạ -> chất lượng -> công

    bố cho `row_count` dòng dữ liệu, trả về dict gồm id từng job + danh
    sách curated_dm_records."""
    key = f"uc46/csv/{dataset_id}.csv"
    lines = ["ma_don_vi,ten_don_vi,so_tien"]
    for i in range(row_count):
        lines.append(f"DV{i:03d},Don vi {i},{1000000 + i}")
    _store_raw(key, ("\n".join(lines) + "\n").encode("utf-8"))

    payload = {
        "dataset_id": dataset_id,
        "raw_object_key": key,
        "schema_fields": _schema_fields(),
        "source_format": "CSV",
    }
    if data_source_id is not None:
        payload["data_source_id"] = data_source_id

    resp = client.post("/parsing-jobs", json=payload)
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
    assert len(dm_records) == row_count

    return {
        "parsing_job": parsing_job,
        "mapping_job": mapping_job,
        "quality_check_job": quality_check_job,
        "curated_publish_job": curated_publish_job,
        "dm_records": dm_records,
    }


# ---------- Bước 1: 'Chọn phạm vi' -- lỗi đầu vào ----------


def test_scope_type_khong_hop_le_thi_422():
    resp = client.get(
        "/provenance-reports/preview", params={"scope_type": "FOO", "scope_value": "1"}
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_PROVENANCE_REPORT_SCOPE"


def test_scope_value_khong_phai_so_thi_422():
    resp = client.get(
        "/provenance-reports/preview",
        params={"scope_type": "DATASET", "scope_value": "khong-phai-so"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_PROVENANCE_REPORT_SCOPE"


def test_phamvi_record_khong_ton_tai_thi_404():
    resp = client.get(
        "/provenance-reports/preview",
        params={"scope_type": "RECORD", "scope_value": "999999"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "CURATED_DM_RECORD_NOT_FOUND"


def test_phamvi_dataset_khong_co_ban_ghi_thi_404():
    resp = client.get(
        "/provenance-reports/preview",
        params={"scope_type": "DATASET", "scope_value": "999998"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "PROVENANCE_REPORT_SCOPE_NOT_FOUND"


def test_phamvi_source_khong_co_ban_ghi_thi_404():
    resp = client.get(
        "/provenance-reports/preview",
        params={"scope_type": "SOURCE", "scope_value": "999997"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "PROVENANCE_REPORT_SCOPE_NOT_FOUND"


# ---------- Bước 1-2: phạm vi RECORD ----------


def test_xem_truoc_bao_cao_theo_pham_vi_ban_ghi():
    chain = _build_full_chain(dataset_id=4601)
    dm_id = chain["dm_records"][0]["id"]

    resp = client.get(
        "/provenance-reports/preview",
        params={"scope_type": "RECORD", "scope_value": str(dm_id)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scope_type"] == "RECORD"
    assert body["total_matched"] == 1
    assert body["returned_count"] == 1
    assert body["truncated"] is False
    assert body["fully_traced_count"] == 1

    record = body["records"][0]
    assert record["curated_dm_record_id"] == dm_id
    assert record["dataset_id"] == 4601
    # phạm vi RECORD mặc định có chi tiết đầy đủ từng bước (bước 3 UC-045)
    assert record["step_details"] is not None
    assert len(record["step_details"]) == 5
    assert [s["step"] for s in record["chain"]["steps"]] == [
        "RAW",
        "PARSING",
        "MAPPING",
        "QUALITY",
        "PUBLISH",
    ]
    for s in record["chain"]["steps"]:
        assert s["available"] is True


# ---------- Bước 1-2: phạm vi DATASET ----------


def test_xem_truoc_bao_cao_theo_pham_vi_tap_du_lieu():
    chain = _build_full_chain(dataset_id=4602, row_count=3)
    dm_ids = {r["id"] for r in chain["dm_records"]}

    resp = client.get(
        "/provenance-reports/preview",
        params={"scope_type": "DATASET", "scope_value": "4602"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scope_type"] == "DATASET"
    assert body["total_matched"] == 3
    assert body["returned_count"] == 3
    assert body["fully_traced_count"] == 3
    returned_ids = {r["curated_dm_record_id"] for r in body["records"]}
    assert returned_ids == dm_ids
    # phạm vi DATASET mặc định KHÔNG kèm chi tiết từng bước (để nhẹ báo cáo)
    for r in body["records"]:
        assert r["step_details"] is None


def test_bao_cao_tap_du_lieu_co_the_bat_chi_tiet_tung_buoc():
    _build_full_chain(dataset_id=4603, row_count=2)

    resp = client.get(
        "/provenance-reports/preview",
        params={
            "scope_type": "DATASET",
            "scope_value": "4603",
            "include_step_details": "true",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for r in body["records"]:
        assert r["step_details"] is not None
        assert len(r["step_details"]) == 5


def test_bao_cao_tap_du_lieu_gioi_han_so_ban_ghi_bang_limit():
    _build_full_chain(dataset_id=4604, row_count=5)

    resp = client.get(
        "/provenance-reports/preview",
        params={"scope_type": "DATASET", "scope_value": "4604", "limit": "2"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_matched"] == 5
    assert body["returned_count"] == 2
    assert body["truncated"] is True


# ---------- Bước 1-2: phạm vi SOURCE ----------


def test_xem_truoc_bao_cao_theo_pham_vi_nguon():
    _build_full_chain(dataset_id=4605, data_source_id=77)
    _build_full_chain(dataset_id=4606, data_source_id=77)
    # dataset khác, nguồn khác -- không được gộp vào
    _build_full_chain(dataset_id=4607, data_source_id=88)

    resp = client.get(
        "/provenance-reports/preview",
        params={"scope_type": "SOURCE", "scope_value": "77"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scope_type"] == "SOURCE"
    assert body["total_matched"] == 2
    dataset_ids = {r["dataset_id"] for r in body["records"]}
    assert dataset_ids == {4605, 4606}


# ---------- Bước 2-3: 'Sinh báo cáo' -> 'Kết xuất PDF' -> 'Hệ thống trả file' ----------


def test_ket_xuat_pdf_theo_pham_vi_ban_ghi():
    chain = _build_full_chain(dataset_id=4608)
    dm_id = chain["dm_records"][0]["id"]

    resp = client.get(
        "/provenance-reports/export",
        params={"scope_type": "RECORD", "scope_value": str(dm_id)},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content[:4] == b"%PDF"
    assert len(resp.content) > 500


def test_ket_xuat_pdf_theo_pham_vi_tap_du_lieu():
    _build_full_chain(dataset_id=4609, row_count=2)

    resp = client.get(
        "/provenance-reports/export",
        params={"scope_type": "DATASET", "scope_value": "4609"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_ket_xuat_pdf_khong_tim_thay_pham_vi_thi_404_khong_tra_pdf():
    resp = client.get(
        "/provenance-reports/export",
        params={"scope_type": "DATASET", "scope_value": "999996"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "PROVENANCE_REPORT_SCOPE_NOT_FOUND"
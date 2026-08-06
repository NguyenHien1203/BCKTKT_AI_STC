"""Integration test UC-041: Công bố vào kho chuẩn hoá + batch_summary,

qua HTTP API (SQLite in-memory). Actor "Hệ thống tự động (Curated
Service)". Luồng:
1. Chèn/Cập nhật vào dm_*. Hệ thống lưu.
2. Đặt publish_status=approved. Hệ thống cập nhật.
3. Tạo batch_summary + cập nhật độ mới dữ liệu. Hệ thống ghi metadata.
4. Kích hoạt sự kiện curated.published. Hệ thống phát sự kiện.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.event_publisher import LoggingEventPublisher  # noqa: E402
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


def _create_mapping_job(dataset_id: int, key: str, csv_content: str) -> dict:
    """Dựng sẵn 1 MappingJob COMPLETED (UC-031) với MappedStandardRecord

    làm dữ liệu đầu vào cho UC-039."""
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

    resp = client.post("/mapping-jobs", json={"parsing_job_id": parsing_job["id"]})
    assert resp.status_code == 201, resp.text
    mapping_job = resp.json()
    assert mapping_job["status"] == "COMPLETED"
    return mapping_job


def _run_passing_quality_check(dataset_id: int, rows: str) -> dict:
    """Không tạo quy tắc chất lượng nào -> UC-039 mặc định PASSED

    (overall_score=100) -> phát sự kiện curated.publish.requested cho
    UC-041 đọc tiếp."""
    key = f"uc41/csv/{dataset_id}.csv"
    csv_content = "ma_don_vi,ten_don_vi,so_tien\n" + rows
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)

    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    quality_check_job = resp.json()
    assert quality_check_job["status"] == "PASSED"
    return quality_check_job


# ---------- Bước 1: tra cứu quality_check_job_id không tồn tại ----------


def test_quality_check_job_id_khong_ton_tai_thi_404():
    resp = client.post("/curated-publish/jobs", json={"quality_check_job_id": 999999})
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "QUALITY_CHECK_JOB_NOT_FOUND"


def test_quality_check_job_chua_co_ban_ghi_cong_bo_thi_failed():
    # Tạo 1 QualityCheckJob thủ công không qua field mapping (dùng job
    # có mapping_job_id giả, records_checked=0) là khó vì router UC-039
    # luôn kèm bản ghi khi PASSED. Thay vào đó dùng job BELOW_THRESHOLD
    # (không có QualityPublishedRecord nào) để kiểm tra nhánh FAILED.
    dataset_id = 4101
    resp = client.post(
        "/quality-rules",
        json={
            "field_names": ["ten_don_vi"],
            "rule_type": "COMPLETENESS",
            "dataset_id": dataset_id,
        },
    )
    assert resp.status_code == 201, resp.text
    resp = client.put(
        "/quality-rules/score-configs",
        json={"dataset_id": dataset_id, "pass_threshold": 90, "rule_type_weights": {}},
    )
    assert resp.status_code == 200, resp.text

    key = f"uc41/csv/{dataset_id}.csv"
    csv_content = "ma_don_vi,ten_don_vi,so_tien\nDV001,,1000000\n"
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)
    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    quality_check_job = resp.json()
    assert quality_check_job["status"] == "BELOW_THRESHOLD"

    resp = client.post(
        "/curated-publish/jobs", json={"quality_check_job_id": quality_check_job["id"]}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert body["error_message"] is not None
    assert body["inserted_count"] == 0
    assert body["updated_count"] == 0


# ---------- Bước 1+2: chèn mới + đặt publish_status=approved ----------


def test_cong_bo_lan_dau_chen_moi_va_dat_approved():
    dataset_id = 4102
    quality_check_job = _run_passing_quality_check(
        dataset_id,
        "DV001,Sở Tài chính,1000000\nDV002,Sở Kế hoạch,2000000\n",
    )

    resp = client.post(
        "/curated-publish/jobs", json={"quality_check_job_id": quality_check_job["id"]}
    )
    assert resp.status_code == 201, resp.text
    job = resp.json()
    assert job["status"] == "COMPLETED"
    assert job["records_received"] == 2
    assert job["inserted_count"] == 2
    assert job["updated_count"] == 0
    assert job["published_event_published"] is True
    assert job["batch_summary_id"] is not None

    dm_records = client.get(f"/curated-publish/jobs/{job['id']}/dm-records").json()
    assert len(dm_records) == 2
    for r in dm_records:
        assert r["publish_status"] == "approved"
        assert r["version"] == 1
        assert r["dataset_id"] == dataset_id

    all_dm = client.get(
        "/curated-publish/dm-records", params={"dataset_id": dataset_id}
    ).json()
    assert len(all_dm) == 2

    approved_only = client.get(
        "/curated-publish/dm-records",
        params={"dataset_id": dataset_id, "publish_status": "approved"},
    ).json()
    assert len(approved_only) == 2


# ---------- Bước 1: công bố lại -> cập nhật tại chỗ (upsert) ----------


def test_cong_bo_lai_cung_dataset_row_index_thi_cap_nhat_khong_trung():
    dataset_id = 4103
    quality_check_job_1 = _run_passing_quality_check(
        dataset_id, "DV001,Sở Tài chính,1000000\n"
    )
    resp = client.post(
        "/curated-publish/jobs", json={"quality_check_job_id": quality_check_job_1["id"]}
    )
    assert resp.status_code == 201, resp.text
    job1 = resp.json()
    assert job1["inserted_count"] == 1
    assert job1["updated_count"] == 0

    # Lượt kiểm tra chất lượng thứ 2 của CÙNG dataset -- row_index=0 lại
    # xuất hiện (mỗi MappingJob đánh row_index từ 0) -> UC-041 phải CẬP
    # NHẬT bản ghi dm_* cũ, không được chèn trùng.
    quality_check_job_2 = _run_passing_quality_check(
        dataset_id, "DV001,Sở Tài chính (đã sửa tên),1000000\n"
    )
    resp = client.post(
        "/curated-publish/jobs", json={"quality_check_job_id": quality_check_job_2["id"]}
    )
    assert resp.status_code == 201, resp.text
    job2 = resp.json()
    assert job2["inserted_count"] == 0
    assert job2["updated_count"] == 1

    all_dm = client.get(
        "/curated-publish/dm-records", params={"dataset_id": dataset_id}
    ).json()
    assert len(all_dm) == 1
    assert all_dm[0]["version"] == 2
    assert all_dm[0]["standardized_fields"]["ten_don_vi"] == "Sở Tài chính (đã sửa tên)"
    assert all_dm[0]["publish_status"] == "approved"


# ---------- Bước 3: tạo batch_summary + cập nhật độ mới dữ liệu ----------


def test_tao_batch_summary_va_cap_nhat_do_moi_du_lieu():
    dataset_id = 4104
    quality_check_job = _run_passing_quality_check(
        dataset_id,
        "DV001,Sở Tài chính,1000000\nDV002,Sở Kế hoạch,2000000\nDV003,Sở Nội vụ,3000000\n",
    )
    resp = client.post(
        "/curated-publish/jobs", json={"quality_check_job_id": quality_check_job["id"]}
    )
    assert resp.status_code == 201, resp.text
    job = resp.json()

    summaries = client.get(
        "/curated-publish/batch-summaries", params={"dataset_id": dataset_id}
    ).json()
    assert len(summaries) == 1
    assert summaries[0]["id"] == job["batch_summary_id"]
    assert summaries[0]["records_received"] == 3
    assert summaries[0]["inserted_count"] == 3
    assert summaries[0]["updated_count"] == 0
    assert summaries[0]["quality_check_job_id"] == quality_check_job["id"]

    freshness = client.get(f"/curated-publish/dataset-freshness/{dataset_id}").json()
    assert freshness["dataset_id"] == dataset_id
    assert freshness["total_published_records"] == 3
    assert freshness["last_batch_summary_id"] == job["batch_summary_id"]

    # Công bố thêm 1 lượt nữa (dataset khác row) -> tổng số bản ghi phải CỘNG DỒN.
    quality_check_job_2 = _run_passing_quality_check(dataset_id, "DV004,Sở Y tế,4000000\n")
    resp = client.post(
        "/curated-publish/jobs", json={"quality_check_job_id": quality_check_job_2["id"]}
    )
    assert resp.status_code == 201, resp.text
    job2 = resp.json()

    freshness2 = client.get(f"/curated-publish/dataset-freshness/{dataset_id}").json()
    assert freshness2["total_published_records"] == 4
    assert freshness2["last_batch_summary_id"] == job2["batch_summary_id"]

    all_freshness = client.get("/curated-publish/dataset-freshness").json()
    assert any(f["dataset_id"] == dataset_id for f in all_freshness)


def test_dataset_chua_tung_cong_bo_thi_404_khi_xem_do_moi():
    resp = client.get("/curated-publish/dataset-freshness/999999")
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "CURATED_DATASET_FRESHNESS_NOT_FOUND"


# ---------- Bước 4: kích hoạt sự kiện curated.published ----------


def test_phat_dung_su_kien_curated_published():
    dataset_id = 4105
    quality_check_job = _run_passing_quality_check(
        dataset_id, "DV001,Sở Tài chính,1000000\n"
    )
    before = len(LoggingEventPublisher.published)
    resp = client.post(
        "/curated-publish/jobs", json={"quality_check_job_id": quality_check_job["id"]}
    )
    assert resp.status_code == 201, resp.text
    job = resp.json()

    new_events = LoggingEventPublisher.published[before:]
    published_events = [e for e in new_events if e["event_name"] == "curated.published"]
    assert len(published_events) == 1
    payload = published_events[0]["payload"]
    assert payload["curated_publish_job_id"] == job["id"]
    assert payload["quality_check_job_id"] == quality_check_job["id"]
    assert payload["dataset_id"] == dataset_id
    assert payload["record_count"] == 1
    assert payload["inserted_count"] == 1
    assert payload["updated_count"] == 0
    assert payload["batch_summary_id"] == job["batch_summary_id"]


# ---------- Tra cứu lại (list/get) ----------


def test_xem_lai_danh_sach_va_chi_tiet_lot_cong_bo():
    dataset_id = 4106
    quality_check_job = _run_passing_quality_check(
        dataset_id, "DV001,Sở Tài chính,1000000\n"
    )
    resp = client.post(
        "/curated-publish/jobs", json={"quality_check_job_id": quality_check_job["id"]}
    )
    job = resp.json()

    resp = client.get("/curated-publish/jobs", params={"dataset_id": dataset_id})
    assert resp.status_code == 200
    assert any(j["id"] == job["id"] for j in resp.json())

    resp = client.get(f"/curated-publish/jobs/{job['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job["id"]

    resp = client.get("/curated-publish/jobs/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "CURATED_PUBLISH_JOB_NOT_FOUND"

    resp = client.get("/curated-publish/jobs/999999/dm-records")
    assert resp.status_code == 404
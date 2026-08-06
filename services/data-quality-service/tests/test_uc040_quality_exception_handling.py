"""Integration test UC-040: Xử lý ngoại lệ chất lượng, qua HTTP API

(SQLite in-memory). Actor "Phụ trách Dữ liệu". Luồng:
1. Xem hàng đợi ngoại lệ. Hệ thống hiển thị.
2. Xử lý từng ngoại lệ (sửa / từ chối / yêu cầu nguồn). Hệ thống lưu
   quyết định.
3. Xử lý hàng loạt ngoại lệ cùng loại. Hệ thống áp dụng.
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


def _create_quality_rule(**kwargs) -> dict:
    payload = {
        "field_names": kwargs.pop("field_names", ["ten_don_vi"]),
        "rule_type": kwargs.pop("rule_type", "COMPLETENESS"),
        **kwargs,
    }
    resp = client.post("/quality-rules", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _save_score_config(**kwargs) -> dict:
    resp = client.put("/quality-rules/score-configs", json=kwargs)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _seed_exception_queue(dataset_id: int, rows: str, pass_threshold: float = 90) -> list:
    """Tạo quy tắc COMPLETENESS trên `ten_don_vi` + chạy UC-039 để sinh

    ra các dòng trong hàng đợi ngoại lệ chất lượng cho UC-040 xử lý."""
    _create_quality_rule(
        field_names=["ten_don_vi"], rule_type="COMPLETENESS", dataset_id=dataset_id
    )
    _save_score_config(dataset_id=dataset_id, pass_threshold=pass_threshold, rule_type_weights={})

    key = f"uc40/csv/{dataset_id}.csv"
    csv_content = "ma_don_vi,ten_don_vi,so_tien\n" + rows
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)

    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "BELOW_THRESHOLD"

    return client.get("/quality-exceptions", params={"dataset_id": dataset_id}).json()


# ---------- Bước 1: Xem hàng đợi ngoại lệ ----------


def test_xem_hang_doi_ngoai_le_mac_dinh_loc_pending():
    dataset_id = 4001
    items = _seed_exception_queue(
        dataset_id, "DV001,Sở Tài chính,1000000\nDV002,,2000000\n"
    )
    assert len(items) == 1
    assert items[0]["status"] == "PENDING"
    assert items[0]["failed_rules"][0]["rule_type"] == "COMPLETENESS"

    # Lọc theo dataset không khớp -> rỗng.
    empty = client.get("/quality-exceptions", params={"dataset_id": 999999}).json()
    assert empty == []


def test_lay_1_ngoai_le_khong_ton_tai_tra_ve_404():
    resp = client.get("/quality-exceptions/999999")
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "QUALITY_EXCEPTION_QUEUE_ITEM_NOT_FOUND"


# ---------- Bước 2: Xử lý từng ngoại lệ (sửa / từ chối / yêu cầu nguồn) ----------


def test_xu_ly_sua_fix_cong_bo_vao_kho_chuan_hoa():
    dataset_id = 4002
    items = _seed_exception_queue(
        dataset_id, "DV001,Sở Tài chính,1000000\nDV002,,2000000\n"
    )
    item = items[0]

    LoggingEventPublisher.published.clear()
    resp = client.post(
        f"/quality-exceptions/{item['id']}/resolve",
        json={"action": "FIX", "corrected_fields": {"ten_don_vi": "Phòng Kế hoạch"}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["item"]["status"] == "RESOLVED"
    assert body["item"]["resolution_action"] == "FIX"
    assert body["item"]["standardized_fields"]["ten_don_vi"] == "Phòng Kế hoạch"
    assert body["published_record"] is not None
    assert body["published_record"]["standardized_fields"]["ten_don_vi"] == "Phòng Kế hoạch"

    events = [
        e for e in LoggingEventPublisher.published if e["event_name"] == "curated.publish.requested"
    ]
    assert len(events) == 1
    assert events[0]["payload"]["source"] == "uc040_exception_fix"

    # Không còn PENDING nữa.
    remaining = client.get("/quality-exceptions", params={"dataset_id": dataset_id}).json()
    assert remaining == []


def test_xu_ly_fix_thieu_corrected_fields_bao_loi_422():
    dataset_id = 4003
    items = _seed_exception_queue(dataset_id, "DV001,,1000000\n")
    resp = client.post(
        f"/quality-exceptions/{items[0]['id']}/resolve",
        json={"action": "FIX"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_QUALITY_EXCEPTION_RESOLUTION"


def test_xu_ly_tu_choi_reject_khong_cong_bo():
    dataset_id = 4004
    items = _seed_exception_queue(dataset_id, "DV001,,1000000\n")

    LoggingEventPublisher.published.clear()
    resp = client.post(
        f"/quality-exceptions/{items[0]['id']}/resolve",
        json={"action": "REJECT", "reason": "Dữ liệu không thể khắc phục"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["item"]["status"] == "RESOLVED"
    assert body["item"]["resolution_action"] == "REJECT"
    assert body["item"]["resolution_reason"] == "Dữ liệu không thể khắc phục"
    assert body["published_record"] is None
    assert LoggingEventPublisher.published == []


def test_xu_ly_reject_thieu_reason_bao_loi_422():
    dataset_id = 4005
    items = _seed_exception_queue(dataset_id, "DV001,,1000000\n")
    resp = client.post(
        f"/quality-exceptions/{items[0]['id']}/resolve",
        json={"action": "REJECT"},
    )
    assert resp.status_code == 422, resp.text


def test_xu_ly_yeu_cau_nguon_request_source_phat_su_kien():
    dataset_id = 4006
    items = _seed_exception_queue(dataset_id, "DV001,,1000000\n")

    LoggingEventPublisher.published.clear()
    resp = client.post(
        f"/quality-exceptions/{items[0]['id']}/resolve",
        json={"action": "REQUEST_SOURCE", "reason": "Đề nghị đơn vị nguồn gửi lại dữ liệu"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["item"]["resolution_action"] == "REQUEST_SOURCE"
    assert body["published_record"] is None

    events = [
        e
        for e in LoggingEventPublisher.published
        if e["event_name"] == "quality.exception.source_requested"
    ]
    assert len(events) == 1
    assert events[0]["payload"]["dataset_id"] == dataset_id
    assert events[0]["payload"]["reason"] == "Đề nghị đơn vị nguồn gửi lại dữ liệu"


def test_xu_ly_ngoai_le_da_giai_quyet_bao_loi_422():
    dataset_id = 4007
    items = _seed_exception_queue(dataset_id, "DV001,,1000000\n")
    item_id = items[0]["id"]

    resp = client.post(
        f"/quality-exceptions/{item_id}/resolve",
        json={"action": "REJECT", "reason": "Lần 1"},
    )
    assert resp.status_code == 200, resp.text

    resp2 = client.post(
        f"/quality-exceptions/{item_id}/resolve",
        json={"action": "REJECT", "reason": "Lần 2"},
    )
    assert resp2.status_code == 422, resp2.text
    assert resp2.json()["detail"]["code"] == "INVALID_QUALITY_EXCEPTION_RESOLUTION"


# ---------- Bước 3: Xử lý hàng loạt ngoại lệ cùng loại ----------


def test_xu_ly_hang_loat_cung_loai_reject():
    dataset_id = 4008
    items = _seed_exception_queue(
        dataset_id,
        "DV001,,1000000\nDV002,,2000000\nDV003,,3000000\n",
    )
    assert len(items) == 3

    resp = client.post(
        "/quality-exceptions/batch-resolve",
        json={
            "dataset_id": dataset_id,
            "rule_type": "COMPLETENESS",
            "action": "REJECT",
            "reason": "Toàn bộ lô nguồn bị lỗi định dạng",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["resolved_count"] == 3
    assert all(i["status"] == "RESOLVED" for i in body["items"])
    assert all(i["resolution_action"] == "REJECT" for i in body["items"])
    assert body["published_records"] == []

    remaining = client.get("/quality-exceptions", params={"dataset_id": dataset_id}).json()
    assert remaining == []


def test_xu_ly_hang_loat_cung_loai_fix_cong_bo_dong_loat():
    dataset_id = 4009
    items = _seed_exception_queue(
        dataset_id,
        "DV001,,1000000\nDV002,,2000000\n",
    )
    assert len(items) == 2

    LoggingEventPublisher.published.clear()
    resp = client.post(
        "/quality-exceptions/batch-resolve",
        json={
            "dataset_id": dataset_id,
            "rule_type": "COMPLETENESS",
            "action": "FIX",
            "corrected_fields": {"ten_don_vi": "Chưa xác định"},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["resolved_count"] == 2
    assert len(body["published_records"]) == 2
    assert all(
        p["standardized_fields"]["ten_don_vi"] == "Chưa xác định" for p in body["published_records"]
    )

    events = [
        e for e in LoggingEventPublisher.published if e["event_name"] == "curated.publish.requested"
    ]
    assert len(events) == 1
    assert events[0]["payload"]["record_count"] == 2


def test_xu_ly_hang_loat_khong_khop_rule_type_bao_loi_422():
    dataset_id = 4010
    _seed_exception_queue(dataset_id, "DV001,,1000000\n")

    resp = client.post(
        "/quality-exceptions/batch-resolve",
        json={"dataset_id": dataset_id, "rule_type": "VALIDITY", "action": "REJECT", "reason": "x"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "NO_MATCHING_EXCEPTION_ITEMS_FOR_BATCH"


def test_xu_ly_hang_loat_khong_lam_anh_huong_dataset_khac():
    dataset_a = 4011
    dataset_b = 4012
    _seed_exception_queue(dataset_a, "DV001,,1000000\n")
    items_b = _seed_exception_queue(dataset_b, "DV001,,1000000\n")

    resp = client.post(
        "/quality-exceptions/batch-resolve",
        json={
            "dataset_id": dataset_a,
            "rule_type": "COMPLETENESS",
            "action": "REJECT",
            "reason": "Chỉ xử lý dataset A",
        },
    )
    assert resp.status_code == 200, resp.text

    remaining_b = client.get("/quality-exceptions", params={"dataset_id": dataset_b}).json()
    assert len(remaining_b) == 1
    assert remaining_b[0]["id"] == items_b[0]["id"]
    assert remaining_b[0]["status"] == "PENDING"
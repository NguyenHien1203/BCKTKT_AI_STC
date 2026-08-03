"""Integration test UC-032: Xử lý hàng đợi chưa ánh xạ, qua HTTP API
(SQLite in-memory). Actor "Phụ trách Dữ liệu". Luồng:
1. Xem hàng đợi chưa ánh xạ. Hệ thống hiển thị.
2. Xử lý giá trị (ánh xạ / tạo mục mới / từ chối). Hệ thống lưu mapping mới.
3. Ánh xạ hàng loạt các giá trị tương tự. Hệ thống áp dụng đồng loạt.
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
        {"name": "loai_don_vi", "data_type": "STRING", "nullable": True},
        {"name": "so_tien", "data_type": "DECIMAL", "nullable": False},
        {"name": "ngay_ghi_so", "data_type": "DATE", "nullable": True},
    ]


def _store_raw(key: str, content: bytes) -> None:
    get_raw_data_storage().upload(key, content, "text/csv")


def _create_rule(**kwargs) -> dict:
    resp = client.post("/mapping-rules", json=kwargs)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _run_mapping_pipeline(dataset_id: int, key: str, csv_content: str) -> dict:
    """Tạo 1 ParsingJob (UC-029) + chạy MappingJob (UC-031) -- sinh ra hàng
    đợi chưa ánh xạ để UC-032 xử lý."""
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
    assert parsing_resp.status_code == 201, parsing_resp.text
    parsing_job = parsing_resp.json()

    mapping_resp = client.post("/mapping-jobs", json={"parsing_job_id": parsing_job["id"]})
    assert mapping_resp.status_code == 201, mapping_resp.text
    return mapping_resp.json()


def _seed_unmapped_item(dataset_id: int, raw_value: str = "Xa") -> dict:
    """Tạo 1 mục hàng đợi chưa ánh xạ (trường loai_don_vi không khớp
    catalog_map) và trả về item PENDING đầu tiên qua API UC-032."""
    _create_rule(
        field_name="loai_don_vi",
        version=1,
        rule_type="CATALOG_LOOKUP",
        dataset_id=dataset_id,
        catalog_map={"SO": "Sở"},
    )
    key = f"uc32/csv/{dataset_id}.csv"
    csv_content = (
        "ma_don_vi,loai_don_vi,so_tien,ngay_ghi_so\n"
        f"DV001,{raw_value},1000000,2026-01-15\n"
    )
    mapping_job = _run_mapping_pipeline(dataset_id, key, csv_content)
    assert mapping_job["unmapped_values_count"] == 1

    queue = client.get("/unmapped-queue", params={"dataset_id": dataset_id}).json()
    assert len(queue) == 1
    return queue[0]


# ---------- Bước 1: Xem hàng đợi chưa ánh xạ ----------


def test_list_unmapped_queue_default_pending_filter():
    dataset_id = 301
    item = _seed_unmapped_item(dataset_id)
    assert item["status"] == "PENDING"
    assert item["field_name"] == "loai_don_vi"
    assert item["raw_value"].lower() == "xa"

    # Mặc định status=PENDING.
    queue = client.get("/unmapped-queue", params={"dataset_id": dataset_id}).json()
    assert len(queue) == 1

    # Lọc theo field_name không khớp -> rỗng.
    queue_wrong_field = client.get(
        "/unmapped-queue", params={"dataset_id": dataset_id, "field_name": "khong_ton_tai"}
    ).json()
    assert queue_wrong_field == []


def test_get_unmapped_queue_item_not_found_returns_404():
    resp = client.get("/unmapped-queue/999999")
    assert resp.status_code == 404


# ---------- Bước 2: Xử lý giá trị (ánh xạ / tạo mục mới / từ chối) ----------


def test_resolve_item_map_creates_new_mapping_rule_version():
    dataset_id = 302
    item = _seed_unmapped_item(dataset_id)

    resp = client.post(
        f"/unmapped-queue/{item['id']}/resolve",
        json={"action": "MAP", "standard_value": "Xã"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["item"]["status"] == "RESOLVED"
    assert body["item"]["resolution_action"] == "MAP"
    assert body["item"]["resolved_value"] == "Xã"
    assert body["updated_rule"] is not None
    assert body["updated_rule"]["rule_type"] == "CATALOG_LOOKUP"
    assert body["updated_rule"]["dataset_id"] == dataset_id
    assert body["updated_rule"]["version"] == 2  # nối tiếp version 1 đã có
    assert body["updated_rule"]["catalog_map"]["XA"] == "Xã"
    # Quy tắc cũ (khoá SO) vẫn được giữ nguyên trong catalog_map mới.
    assert body["updated_rule"]["catalog_map"]["SO"] == "Sở"

    # Mục đã RESOLVED -> không còn xuất hiện trong hàng đợi PENDING mặc định.
    queue = client.get("/unmapped-queue", params={"dataset_id": dataset_id}).json()
    assert queue == []


def test_resolve_item_create_new_entry():
    dataset_id = 303
    item = _seed_unmapped_item(dataset_id, raw_value="Thi Tran")

    resp = client.post(
        f"/unmapped-queue/{item['id']}/resolve",
        json={"action": "CREATE_NEW", "standard_value": "Thị trấn"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["item"]["resolution_action"] == "CREATE_NEW"
    assert body["updated_rule"]["catalog_map"]["THI TRAN"] == "Thị trấn"


def test_resolve_item_reject_requires_reason():
    dataset_id = 304
    item = _seed_unmapped_item(dataset_id)

    # Thiếu reason -> 422.
    resp_missing_reason = client.post(
        f"/unmapped-queue/{item['id']}/resolve", json={"action": "REJECT"}
    )
    assert resp_missing_reason.status_code == 422

    resp = client.post(
        f"/unmapped-queue/{item['id']}/resolve",
        json={"action": "REJECT", "reason": "Giá trị không thuộc danh mục nghiệp vụ hợp lệ"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["item"]["status"] == "RESOLVED"
    assert body["item"]["resolution_action"] == "REJECT"
    assert body["item"]["resolution_reason"]
    # Từ chối không tạo quy tắc ánh xạ mới.
    assert body["updated_rule"] is None


def test_resolve_map_missing_standard_value_returns_422():
    dataset_id = 305
    item = _seed_unmapped_item(dataset_id)
    resp = client.post(f"/unmapped-queue/{item['id']}/resolve", json={"action": "MAP"})
    assert resp.status_code == 422


def test_resolve_invalid_action_returns_422():
    dataset_id = 306
    item = _seed_unmapped_item(dataset_id)
    resp = client.post(
        f"/unmapped-queue/{item['id']}/resolve",
        json={"action": "KHONG_HOP_LE", "standard_value": "x"},
    )
    assert resp.status_code == 422


def test_resolve_unknown_item_returns_404():
    resp = client.post(
        "/unmapped-queue/999999/resolve", json={"action": "MAP", "standard_value": "x"}
    )
    assert resp.status_code == 404


def test_resolve_already_resolved_item_returns_422():
    dataset_id = 307
    item = _seed_unmapped_item(dataset_id)
    first = client.post(
        f"/unmapped-queue/{item['id']}/resolve", json={"action": "MAP", "standard_value": "Xã"}
    )
    assert first.status_code == 200

    second = client.post(
        f"/unmapped-queue/{item['id']}/resolve", json={"action": "MAP", "standard_value": "Xã"}
    )
    assert second.status_code == 422


# ---------- Bước 3: Ánh xạ hàng loạt các giá trị tương tự ----------


def test_resolve_with_apply_to_similar_applies_to_matching_pending_items():
    dataset_id = 308
    _create_rule(
        field_name="loai_don_vi",
        version=1,
        rule_type="CATALOG_LOOKUP",
        dataset_id=dataset_id,
        catalog_map={"SO": "Sở"},
    )
    key = "uc32/csv/batch.csv"
    # 2 dòng khác nhau nhưng cùng giá trị chưa ánh xạ "Xa"/"xa " (khác hoa
    # thường/khoảng trắng nhưng cùng khoá chuẩn hoá) ở trường loai_don_vi.
    csv_content = (
        "ma_don_vi,loai_don_vi,so_tien,ngay_ghi_so\n"
        "DV001,Xa,1000000,2026-01-01\n"
        "DV002, xa ,2000000,2026-01-02\n"
    )
    mapping_job = _run_mapping_pipeline(dataset_id, key, csv_content)
    assert mapping_job["unmapped_values_count"] == 2

    queue = client.get("/unmapped-queue", params={"dataset_id": dataset_id}).json()
    assert len(queue) == 2

    resp = client.post(
        f"/unmapped-queue/{queue[0]['id']}/resolve",
        json={"action": "MAP", "standard_value": "Xã", "apply_to_similar": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["affected_count"] == 1
    assert body["affected_items"][0]["status"] == "RESOLVED"
    assert body["affected_items"][0]["resolved_value"] == "Xã"

    # Cả 2 mục đều đã RESOLVED -> hàng đợi PENDING rỗng.
    remaining = client.get("/unmapped-queue", params={"dataset_id": dataset_id}).json()
    assert remaining == []

    # Chỉ 1 quy tắc mới được tạo (không nhân đôi theo số lượng mục tương tự).
    rules = client.get(
        "/mapping-rules", params={"dataset_id": dataset_id, "field_name": "loai_don_vi"}
    ).json()
    assert len(rules) == 2  # version 1 (ban đầu) + version 2 (mới tạo ở bước 2-3)


def test_apply_to_similar_does_not_affect_other_fields_or_datasets():
    dataset_id_a = 309
    dataset_id_b = 310
    item_a = _seed_unmapped_item(dataset_id_a, raw_value="Xa")
    item_b = _seed_unmapped_item(dataset_id_b, raw_value="Xa")

    resp = client.post(
        f"/unmapped-queue/{item_a['id']}/resolve",
        json={"action": "MAP", "standard_value": "Xã", "apply_to_similar": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Không ảnh hưởng dataset khác dù raw_value giống nhau.
    assert body["affected_count"] == 0

    queue_b = client.get("/unmapped-queue", params={"dataset_id": dataset_id_b}).json()
    assert len(queue_b) == 1
    assert queue_b[0]["id"] == item_b["id"]
    assert queue_b[0]["status"] == "PENDING"


# ---------- Vòng lặp khép kín: mapping mới áp dụng ngay cho lần chạy UC-031 sau ----------


def test_new_mapping_rule_applies_on_next_mapping_run():
    dataset_id = 311
    item = _seed_unmapped_item(dataset_id)
    resolve_resp = client.post(
        f"/unmapped-queue/{item['id']}/resolve",
        json={"action": "MAP", "standard_value": "Xã"},
    )
    assert resolve_resp.status_code == 200

    # Chạy 1 phiên phân tích + ánh xạ MỚI với cùng giá trị "Xa" -- lần
    # này phải ánh xạ được ngay, không rơi vào hàng đợi nữa.
    key = "uc32/csv/rerun.csv"
    csv_content = "ma_don_vi,loai_don_vi,so_tien,ngay_ghi_so\nDV099,Xa,500000,2026-02-01\n"
    mapping_job = _run_mapping_pipeline(dataset_id, key, csv_content)
    assert mapping_job["unmapped_values_count"] == 0
    assert mapping_job["records_mapped"] == 1

    records = client.get(f"/mapping-jobs/{mapping_job['id']}/standard-records").json()
    assert records[0]["standardized_fields"]["loai_don_vi"] == "Xã"
"""Integration test UC-039: Chạy kiểm tra chất lượng dữ liệu, qua HTTP

API (SQLite in-memory). Actor "Hệ thống tự động (Quality Service)".
Luồng:
1. Tra cứu quy tắc chất lượng. Hệ thống đọc metadata.quality_rules.
2. Chạy quy tắc. Hệ thống tính điểm.
3a. Đạt ngưỡng -> công bố. Hệ thống đẩy vào kho chuẩn hoá.
3b. Dưới ngưỡng -> hàng đợi ngoại lệ. Hệ thống đẩy vào hàng đợi cho
    Phụ trách Dữ liệu.
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


# ---------- Bước 1: Tra cứu quy tắc chất lượng ----------


def test_khong_co_ban_ghi_chuan_hoa_thi_bao_loi():
    resp = client.post("/quality-checks", json={"mapping_job_id": 999999})
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "NO_STANDARD_RECORDS_TO_CHECK"


def test_khong_co_quy_tac_nao_thi_mac_dinh_dat_va_cong_bo():
    dataset_id = 3901
    key = "uc39/csv/no_rules.csv"
    csv_content = "ma_don_vi,ten_don_vi,so_tien\nDV001,Sở Tài chính,1000000\n"
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)

    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "PASSED"
    assert body["overall_score"] == 100.0
    assert body["published_count"] == 1
    assert body["exception_count"] == 0


# ---------- Bước 2: Chạy quy tắc -- Hệ thống tính điểm ----------


def test_quy_tac_day_du_completeness_phat_hien_truong_rong():
    dataset_id = 3902
    _create_quality_rule(
        field_names=["ten_don_vi"], rule_type="COMPLETENESS", dataset_id=dataset_id
    )
    _save_score_config(dataset_id=dataset_id, pass_threshold=90, rule_type_weights={})

    key = "uc39/csv/completeness.csv"
    csv_content = (
        "ma_don_vi,ten_don_vi,so_tien\n"
        "DV001,Sở Tài chính,1000000\n"
        "DV002,,2000000\n"
    )
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)

    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    # 1/2 dòng rỗng trường bắt buộc -> pass_rate 50% < ngưỡng 90.
    assert body["status"] == "BELOW_THRESHOLD"
    assert body["overall_score"] == 50.0
    assert body["exception_count"] == 1

    rule_results = client.get(f"/quality-checks/{body['id']}/rule-results").json()
    assert len(rule_results) == 1
    assert rule_results[0]["rule_type"] == "COMPLETENESS"
    assert rule_results[0]["failed_count"] == 1
    assert rule_results[0]["total_checked"] == 2


def test_quy_tac_hop_le_validity_theo_regex():
    dataset_id = 3903
    _create_quality_rule(
        field_names=["ma_don_vi"],
        rule_type="VALIDITY",
        dataset_id=dataset_id,
        params={"regex": "^DV[0-9]{3}$"},
    )
    _save_score_config(dataset_id=dataset_id, pass_threshold=100, rule_type_weights={})

    key = "uc39/csv/validity.csv"
    csv_content = (
        "ma_don_vi,ten_don_vi,so_tien\n"
        "DV001,Sở Tài chính,1000000\n"
        "SAI,Phòng Kế hoạch,2000000\n"
    )
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)

    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "BELOW_THRESHOLD"
    assert body["overall_score"] == 50.0


def test_quy_tac_duy_nhat_uniqueness_phat_hien_trung_lap():
    dataset_id = 3904
    _create_quality_rule(
        field_names=["ma_don_vi"], rule_type="UNIQUENESS", dataset_id=dataset_id
    )
    _save_score_config(dataset_id=dataset_id, pass_threshold=100, rule_type_weights={})

    key = "uc39/csv/uniqueness.csv"
    csv_content = (
        "ma_don_vi,ten_don_vi,so_tien\n"
        "DV001,Sở Tài chính,1000000\n"
        "DV001,Sở Tài chính 2,2000000\n"
        "DV002,Phòng Kế hoạch,3000000\n"
    )
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)

    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "BELOW_THRESHOLD"
    # 2/3 dòng trùng mã đơn vị -> pass_rate ~33.33%.
    assert round(body["overall_score"], 2) == 33.33
    assert body["exception_count"] == 2


def test_quy_tac_nhat_quan_consistency_bieu_thuc():
    dataset_id = 3905
    _create_quality_rule(
        field_names=["so_tien"],
        rule_type="CONSISTENCY",
        dataset_id=dataset_id,
        params={"expression": "so_tien > 0"},
    )
    _save_score_config(dataset_id=dataset_id, pass_threshold=100, rule_type_weights={})

    key = "uc39/csv/consistency.csv"
    csv_content = (
        "ma_don_vi,ten_don_vi,so_tien\n"
        "DV001,Sở Tài chính,1000000\n"
        "DV002,Phòng Kế hoạch,-500\n"
    )
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)

    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "BELOW_THRESHOLD"
    assert body["overall_score"] == 50.0


# ---------- Bước 3a: Đạt ngưỡng -> công bố (đẩy vào kho chuẩn hoá) ----------


def test_dat_nguong_thi_cong_bo_vao_kho_chuan_hoa_va_phat_su_kien():
    dataset_id = 3906
    _create_quality_rule(
        field_names=["ten_don_vi"], rule_type="COMPLETENESS", dataset_id=dataset_id
    )
    _save_score_config(dataset_id=dataset_id, pass_threshold=90, rule_type_weights={})

    key = "uc39/csv/passed.csv"
    csv_content = (
        "ma_don_vi,ten_don_vi,so_tien\n"
        "DV001,Sở Tài chính,1000000\n"
        "DV002,Phòng Kế hoạch,2000000\n"
    )
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)

    LoggingEventPublisher.published.clear()
    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "PASSED"
    assert body["overall_score"] == 100.0
    assert body["published_count"] == 2
    assert body["exception_count"] == 0
    assert body["publish_event_published"] is True

    published = client.get(f"/quality-checks/{body['id']}/published-records").json()
    assert len(published) == 2
    assert {p["standardized_fields"]["ma_don_vi"] for p in published} == {"DV001", "DV002"}

    events = [e for e in LoggingEventPublisher.published if e["event_name"] == "curated.publish.requested"]
    assert len(events) == 1
    assert events[0]["payload"]["record_count"] == 2
    assert events[0]["payload"]["dataset_id"] == dataset_id


# ---------- Bước 3b: Dưới ngưỡng -> hàng đợi ngoại lệ (cho Phụ trách Dữ liệu) ----------


def test_duoi_nguong_thi_day_vao_hang_doi_ngoai_le_va_phat_su_kien():
    dataset_id = 3907
    _create_quality_rule(
        field_names=["ten_don_vi"], rule_type="COMPLETENESS", dataset_id=dataset_id
    )
    _save_score_config(dataset_id=dataset_id, pass_threshold=90, rule_type_weights={})

    key = "uc39/csv/below_threshold.csv"
    csv_content = (
        "ma_don_vi,ten_don_vi,so_tien\n"
        "DV001,Sở Tài chính,1000000\n"
        "DV002,,2000000\n"
        "DV003,,3000000\n"
    )
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)

    LoggingEventPublisher.published.clear()
    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "BELOW_THRESHOLD"
    assert body["published_count"] == 0
    assert body["exception_count"] == 2
    assert body["exception_event_published"] is True

    items = client.get(f"/quality-checks/{body['id']}/exception-items").json()
    assert len(items) == 2
    assert {i["standardized_fields"]["ma_don_vi"] for i in items} == {"DV002", "DV003"}
    assert all(i["failed_rules"] for i in items)
    assert all(i["status"] == "PENDING" for i in items)

    events = [
        e for e in LoggingEventPublisher.published if e["event_name"] == "quality.exception.queued"
    ]
    assert len(events) == 1
    assert events[0]["payload"]["exception_count"] == 2

    # Dòng KHÔNG vi phạm quy tắc nào (DV001) không bị đẩy vào hàng đợi.
    queue_ids = {i["standardized_fields"]["ma_don_vi"] for i in items}
    assert "DV001" not in queue_ids


def test_xem_hang_doi_ngoai_le_toan_bo_theo_dataset():
    dataset_id = 3908
    _create_quality_rule(
        field_names=["ten_don_vi"], rule_type="COMPLETENESS", dataset_id=dataset_id
    )
    _save_score_config(dataset_id=dataset_id, pass_threshold=90, rule_type_weights={})

    key = "uc39/csv/queue_view.csv"
    csv_content = "ma_don_vi,ten_don_vi,so_tien\nDV001,,1000000\n"
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)

    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text

    resp = client.get(
        "/quality-checks/exception-queue/list",
        params={"dataset_id": dataset_id, "status": "PENDING"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["dataset_id"] == dataset_id
    assert body[0]["status"] == "PENDING"


# ---------- Ưu tiên quy tắc riêng của dataset khi trùng với quy tắc chung ----------


def test_uu_tien_quy_tac_rieng_cua_dataset_khi_trung_voi_quy_tac_chung():
    dataset_id = 3909
    # Quy tắc chung: bắt buộc ten_don_vi (áp dụng mọi dataset).
    _create_quality_rule(field_names=["ten_don_vi"], rule_type="COMPLETENESS", dataset_id=None)
    # Quy tắc riêng CÙNG (rule_type, field_names) nhưng is_active=False --
    # dataset này coi như KHÔNG có quy tắc completeness (không dùng quy tắc chung).
    _create_quality_rule(
        field_names=["ten_don_vi"],
        rule_type="COMPLETENESS",
        dataset_id=dataset_id,
        is_active=False,
    )
    _save_score_config(dataset_id=dataset_id, pass_threshold=90, rule_type_weights={})

    key = "uc39/csv/override.csv"
    csv_content = "ma_don_vi,ten_don_vi,so_tien\nDV001,,1000000\n"
    mapping_job = _create_mapping_job(dataset_id, key, csv_content)

    resp = client.post(
        "/quality-checks",
        json={"mapping_job_id": mapping_job["id"], "dataset_id": dataset_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    # Không có quy tắc active nào áp dụng -> mặc định đạt tuyệt đối.
    assert body["status"] == "PASSED"
    assert body["overall_score"] == 100.0
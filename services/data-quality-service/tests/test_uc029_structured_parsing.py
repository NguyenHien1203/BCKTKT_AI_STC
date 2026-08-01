"""Integration test UC-029: Phân tích dữ liệu có cấu trúc, qua HTTP API (SQLite in-memory)."""
import json
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.event_publisher import LoggingEventPublisher  # noqa: E402
from app.infrastructure.file_storage import get_raw_data_storage  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _basic_schema_fields():
    return [
        {"name": "ma_don_vi", "data_type": "STRING", "nullable": False},
        {"name": "so_tien", "data_type": "DECIMAL", "nullable": False},
        {"name": "ngay_ghi_so", "data_type": "DATE", "nullable": True},
        {"name": "da_duyet", "data_type": "BOOLEAN", "nullable": True},
    ]


def _store_raw(key: str, content: bytes, content_type: str = "application/octet-stream") -> None:
    """Mô phỏng việc ingestion-service đã lưu dữ liệu thô vào MinIO trước khi
    phát sự kiện `parsing.requested` — test ghi thẳng vào cùng storage backend
    (đĩa cục bộ khi chạy test) rồi mới gọi API như đang nhận sự kiện."""
    get_raw_data_storage().upload(key, content, content_type)


def setup_function(_):
    LoggingEventPublisher.published.clear()


# ---------- Bước 1-6: happy path theo từng định dạng ----------


def test_parse_csv_happy_path():
    key = "uc29/csv/happy.csv"
    csv_content = (
        "ma_don_vi,so_tien,ngay_ghi_so,da_duyet\n"
        "DV001,1000000,2026-01-15,true\n"
        "DV002,2500000,2026-01-16,false\n"
    ).encode("utf-8")
    _store_raw(key, csv_content, "text/csv")

    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 1,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "MAPPED"
    assert body["records_read"] == 2
    assert body["records_parsed"] == 2
    assert body["records_failed"] == 0
    assert body["mapping_event_published"] is True

    published = [e for e in LoggingEventPublisher.published if e["event_name"] == "mapping.requested"]
    assert len(published) == 1
    assert published[0]["payload"]["parsing_job_id"] == body["id"]
    assert published[0]["payload"]["dataset_id"] == 1
    assert published[0]["payload"]["records_parsed"] == 2


def test_parse_json_happy_path():
    key = "uc29/json/happy.json"
    payload = [
        {"ma_don_vi": "DV010", "so_tien": "500000", "ngay_ghi_so": "2026-02-01", "da_duyet": "1"},
    ]
    _store_raw(key, json.dumps(payload).encode("utf-8"), "application/json")

    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 2,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "JSON",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "MAPPED"
    assert body["records_parsed"] == 1


def test_parse_json_object_with_records_key():
    key = "uc29/json/wrapped.json"
    payload = {"records": [{"ma_don_vi": "DV020", "so_tien": "10"}]}
    _store_raw(key, json.dumps(payload).encode("utf-8"), "application/json")

    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 2,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "JSON",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["records_parsed"] == 1


def test_parse_xml_happy_path():
    key = "uc29/xml/happy.xml"
    xml_content = (
        "<records>"
        "<record><ma_don_vi>DV030</ma_don_vi><so_tien>777</so_tien></record>"
        "</records>"
    ).encode("utf-8")
    _store_raw(key, xml_content, "application/xml")

    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 3,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "XML",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "MAPPED"
    assert body["records_parsed"] == 1


def test_parse_excel_happy_path():
    from io import BytesIO

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["ma_don_vi", "so_tien", "ngay_ghi_so", "da_duyet"])
    ws.append(["DV040", 999.5, "2026-03-01", "true"])
    buf = BytesIO()
    wb.save(buf)

    key = "uc29/excel/happy.xlsx"
    _store_raw(
        key, buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 4,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "EXCEL",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "MAPPED"
    assert body["records_parsed"] == 1


def test_source_format_auto_inferred_from_extension():
    key = "uc29/auto/data.csv"
    _store_raw(key, b"ma_don_vi,so_tien\nDV1,1\n", "text/csv")

    resp = client.post(
        "/parsing-jobs",
        json={"dataset_id": 5, "raw_object_key": key, "schema_fields": _basic_schema_fields()},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["source_format"] == "CSV"


def test_unsupported_source_format_without_recognizable_extension():
    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 6,
            "raw_object_key": "uc29/unknown/data.bin",
            "schema_fields": _basic_schema_fields(),
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "UNSUPPORTED_SOURCE_FORMAT"


# ---------- Ánh xạ tên trường ----------


def test_explicit_field_mapping_renames_source_columns():
    key = "uc29/mapping/explicit.csv"
    _store_raw(key, b"MaDonVi,SoTien\nDV100,555\n", "text/csv")

    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 7,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
            "field_mapping": {"MaDonVi": "ma_don_vi", "SoTien": "so_tien"},
        },
    )
    assert resp.status_code == 201, resp.text
    job_id = resp.json()["id"]

    records = client.get(f"/parsing-jobs/{job_id}/parsed-records")
    assert records.status_code == 200
    mapped = records.json()[0]["mapped_fields"]
    assert mapped["ma_don_vi"] == "DV100"
    assert mapped["so_tien"] == 555.0


def test_auto_field_mapping_matches_by_normalized_name():
    key = "uc29/mapping/auto.csv"
    # Cột nguồn có khoảng trắng thừa + hoa/thường khác — vẫn tự khớp được.
    _store_raw(key, "  Ma_Don_Vi ,so_tien\nDV200,321\n".encode("utf-8"), "text/csv")

    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 8,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
        },
    )
    assert resp.status_code == 201, resp.text
    job_id = resp.json()["id"]
    records = client.get(f"/parsing-jobs/{job_id}/parsed-records").json()
    assert records[0]["mapped_fields"]["ma_don_vi"] == "DV200"


def test_unmapped_extra_source_column_is_ignored():
    key = "uc29/mapping/extra_col.csv"
    _store_raw(key, b"ma_don_vi,so_tien,cot_thua\nDV300,1,gia_tri_khong_dung\n", "text/csv")

    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 9,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["records_parsed"] == 1


def test_missing_target_column_is_set_null_not_an_error():
    key = "uc29/mapping/missing_col.csv"
    _store_raw(key, b"ma_don_vi\nDV400\n", "text/csv")

    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 10,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["records_parsed"] == 1
    assert body["records_failed"] == 0
    job_id = body["id"]
    mapped = client.get(f"/parsing-jobs/{job_id}/parsed-records").json()[0]["mapped_fields"]
    assert mapped["so_tien"] is None


# ---------- Ép kiểu + lỗi từng dòng ----------


def test_row_with_invalid_cast_is_recorded_as_row_error_but_job_still_mapped():
    key = "uc29/casting/partial_fail.csv"
    _store_raw(
        key,
        b"ma_don_vi,so_tien\nDV500,khong_phai_so\nDV501,100\n",
        "text/csv",
    )

    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 11,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "MAPPED"
    assert body["records_read"] == 2
    assert body["records_parsed"] == 1
    assert body["records_failed"] == 1

    job_id = body["id"]
    errors = client.get(f"/parsing-jobs/{job_id}/row-errors").json()
    assert len(errors) == 1
    assert errors[0]["row_index"] == 0
    assert errors[0]["field_name"] == "so_tien"


def test_all_rows_fail_casting_job_status_failed_and_no_mapping_event():
    key = "uc29/casting/all_fail.csv"
    _store_raw(key, b"ma_don_vi,so_tien\nDV600,abc\n", "text/csv")

    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 12,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert body["records_parsed"] == 0
    assert body["mapping_event_published"] is False

    published = [e for e in LoggingEventPublisher.published if e["event_name"] == "mapping.requested"]
    assert not published


def test_boolean_and_date_casting_variants():
    key = "uc29/casting/types.csv"
    _store_raw(
        key,
        b"ma_don_vi,so_tien,ngay_ghi_so,da_duyet\nDV700,1,15/03/2026,yes\n",
        "text/csv",
    )
    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 13,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
        },
    )
    assert resp.status_code == 201, resp.text
    job_id = resp.json()["id"]
    mapped = client.get(f"/parsing-jobs/{job_id}/parsed-records").json()[0]["mapped_fields"]
    assert mapped["ngay_ghi_so"] == "2026-03-15"
    assert mapped["da_duyet"] is True


# ---------- Lỗi hạ tầng / dữ liệu vào ----------


def test_raw_object_not_found_marks_job_failed():
    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 14,
            "raw_object_key": "uc29/does-not-exist.csv",
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert "RAW_OBJECT_NOT_FOUND" in body["error_message"] or "thô" in body["error_message"]


def test_empty_schema_fields_returns_422():
    resp = client.post(
        "/parsing-jobs",
        json={"dataset_id": 15, "raw_object_key": "uc29/x.csv", "schema_fields": []},
    )
    assert resp.status_code == 422, resp.text


def test_invalid_data_type_in_schema_fields_returns_422():
    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 16,
            "raw_object_key": "uc29/x.csv",
            "schema_fields": [{"name": "f1", "data_type": "KHONG_HOP_LE"}],
            "source_format": "CSV",
        },
    )
    assert resp.status_code == 422, resp.text


def test_invalid_json_raw_content_marks_job_failed():
    key = "uc29/json/invalid.json"
    _store_raw(key, b"{not-valid-json", "application/json")
    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 17,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "JSON",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "FAILED"


# ---------- Danh sách / xem lại ----------


def test_list_jobs_filter_by_dataset_id_and_status():
    key = "uc29/list/a.csv"
    _store_raw(key, b"ma_don_vi,so_tien\nDV800,1\n", "text/csv")
    client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 900,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
        },
    )

    resp = client.get("/parsing-jobs", params={"dataset_id": 900})
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 1
    assert jobs[0]["dataset_id"] == 900

    resp2 = client.get("/parsing-jobs", params={"dataset_id": 900, "status": "FAILED"})
    assert resp2.json() == []


def test_get_job_detail_404_when_not_found():
    resp = client.get("/parsing-jobs/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "PARSING_JOB_NOT_FOUND"


def test_row_errors_404_when_job_not_found():
    resp = client.get("/parsing-jobs/999999/row-errors")
    assert resp.status_code == 404


def test_stg_rows_reflect_raw_data_read_in_step_2():
    key = "uc29/stg/check.csv"
    _store_raw(key, b"ma_don_vi,so_tien\nDV900,1\nDV901,2\n", "text/csv")
    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 20,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
        },
    )
    job_id = resp.json()["id"]
    stg_rows = client.get(f"/parsing-jobs/{job_id}/stg-rows").json()
    assert len(stg_rows) == 2
    assert stg_rows[0]["ma_don_vi"] == "DV900"


def test_ingestion_run_id_and_data_source_id_are_persisted():
    key = "uc29/run/linked.csv"
    _store_raw(key, b"ma_don_vi,so_tien\nDV1000,1\n", "text/csv")
    resp = client.post(
        "/parsing-jobs",
        json={
            "dataset_id": 21,
            "raw_object_key": key,
            "schema_fields": _basic_schema_fields(),
            "source_format": "CSV",
            "ingestion_run_id": 555,
            "data_source_id": 66,
        },
    )
    body = resp.json()
    assert body["ingestion_run_id"] == 555
    assert body["data_source_id"] == 66

    resp2 = client.get("/parsing-jobs", params={"ingestion_run_id": 555})
    assert len(resp2.json()) == 1
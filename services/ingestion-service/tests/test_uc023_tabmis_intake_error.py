"""Integration test UC-023: Xem trạng thái + sửa lỗi intake TABMIS, qua
HTTP API (SQLite in-memory).

Luồng nghiệp vụ (docs/use_cases.json id=23):
1. Xem trạng thái tiếp nhận -> hệ thống hiển thị máy trạng thái.
2. Xem chi tiết lỗi dòng -> hệ thống hiển thị các dòng sai.
3. Sửa và tải lại tệp đã chỉnh -> hệ thống kiểm tra lại.
"""
import io
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

_SCHEMA_COLUMNS = ["ma_don_vi", "ten_don_vi", "so_tien"]


def _create_data_source(code, source_system="TABMIS"):
    resp = client.post(
        "/data-sources",
        json={
            "code": code,
            "name": "Nguồn dữ liệu test UC-23",
            "source_system": source_system,
            "provider": "Bộ Tài chính",
            "owner": "Cục CNTT",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _schema_fields():
    return [
        {"name": "ma_don_vi", "data_type": "STRING", "nullable": False, "description": ""},
        {"name": "ten_don_vi", "data_type": "STRING", "nullable": False, "description": ""},
        {"name": "so_tien", "data_type": "DECIMAL", "nullable": False, "description": ""},
    ]


def _create_dataset(data_source_id, code, critical_fields=None):
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": data_source_id,
            "code": code,
            "name": "Tập dữ liệu test UC-23",
            "schema_fields": _schema_fields(),
        },
    )
    assert resp.status_code == 201, resp.text
    dataset_id = resp.json()["id"]
    if critical_fields:
        resp2 = client.post(
            f"/datasets/{dataset_id}/critical-fields",
            json={"field_names": critical_fields},
        )
        assert resp2.status_code == 200, resp2.text
    return dataset_id


def _new_tabmis_dataset(prefix, critical_fields=None):
    data_source_id = _create_data_source(f"{prefix}-SRC")
    return _create_dataset(data_source_id, f"{prefix}-DS", critical_fields=critical_fields)


def _build_xlsx(columns, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(columns)
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _upload(dataset_id, content, file_name="tabmis-data.xlsx", uploaded_by="canbo01"):
    return client.post(
        "/tabmis-intake/upload",
        data={"dataset_id": dataset_id, "uploaded_by": uploaded_by},
        files={
            "file": (
                file_name,
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )


def _reupload(session_id, content, file_name="tabmis-data-sua.xlsx", uploaded_by="canbo01"):
    return client.post(
        f"/tabmis-intake/{session_id}/reupload",
        data={"uploaded_by": uploaded_by},
        files={
            "file": (
                file_name,
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )


# ---------- Bước 1: Xem trạng thái tiếp nhận (máy trạng thái) ----------


def test_status_received_allows_only_reupload():
    dataset_id = _new_tabmis_dataset("UC23A")
    content = _build_xlsx(_SCHEMA_COLUMNS, [["DV01", "Đơn vị 1", "1000000"]])
    session = _upload(dataset_id, content).json()

    resp = client.get(f"/tabmis-intake/{session['id']}/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["session"]["status"] == "RECEIVED"
    assert body["allowed_actions"] == ["REUPLOAD"]
    assert body["row_error_count"] == 0


def test_status_template_invalid_allows_view_errors_and_reupload():
    dataset_id = _new_tabmis_dataset("UC23B")
    content = _build_xlsx(["ma_don_vi", "ten_don_vi"], [["DV01", "Đơn vị 1"]])  # thiếu so_tien
    session = _upload(dataset_id, content).json()
    assert session["status"] == "TEMPLATE_INVALID"

    resp = client.get(f"/tabmis-intake/{session['id']}/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session"]["status"] == "TEMPLATE_INVALID"
    assert set(body["allowed_actions"]) == {"VIEW_ROW_ERRORS", "REUPLOAD"}


def test_status_404_when_session_not_found():
    resp = client.get("/tabmis-intake/999999/status")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "TABMIS_INTAKE_SESSION_NOT_FOUND"


# ---------- Bước 2: Xem chi tiết lỗi dòng ----------


def test_upload_with_missing_critical_field_creates_row_errors_status():
    dataset_id = _new_tabmis_dataset("UC23C", critical_fields=["ma_don_vi", "so_tien"])
    content = _build_xlsx(
        _SCHEMA_COLUMNS,
        [
            ["DV01", "Đơn vị 1", "1000000"],  # dòng 1: hợp lệ
            ["", "Đơn vị 2", "2000000"],  # dòng 2: thiếu ma_don_vi (bắt buộc)
            ["DV03", "Đơn vị 3", "abc"],  # dòng 3: so_tien không phải số
        ],
    )
    resp = _upload(dataset_id, content)
    assert resp.status_code == 201, resp.text
    session = resp.json()
    assert session["status"] == "ROW_ERRORS"
    assert session["control_totals"]["row_error_count"] == 2
    assert session["error_message"] != ""

    run = client.get(f"/ingestion-runs/{session['ingestion_run_id']}").json()
    assert run["status"] == "PARTIAL"

    row_errors_resp = client.get(f"/tabmis-intake/{session['id']}/row-errors")
    assert row_errors_resp.status_code == 200
    row_errors = row_errors_resp.json()
    assert len(row_errors) == 2
    by_row = {e["row_number"]: e for e in row_errors}
    assert by_row[2]["field_name"] == "ma_don_vi"
    assert "bắt buộc" in by_row[2]["message"]
    assert by_row[3]["field_name"] == "so_tien"

    status_resp = client.get(f"/tabmis-intake/{session['id']}/status").json()
    assert status_resp["row_error_count"] == 2
    assert set(status_resp["allowed_actions"]) == {"VIEW_ROW_ERRORS", "REUPLOAD"}


def test_row_errors_empty_list_when_no_errors():
    dataset_id = _new_tabmis_dataset("UC23D", critical_fields=["ma_don_vi"])
    content = _build_xlsx(_SCHEMA_COLUMNS, [["DV01", "Đơn vị 1", "100"]])
    session = _upload(dataset_id, content).json()
    assert session["status"] == "RECEIVED"

    resp = client.get(f"/tabmis-intake/{session['id']}/row-errors")
    assert resp.status_code == 200
    assert resp.json() == []


def test_row_errors_404_when_session_not_found():
    resp = client.get("/tabmis-intake/999999/row-errors")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "TABMIS_INTAKE_SESSION_NOT_FOUND"


# ---------- Bước 3: Sửa và tải lại tệp đã chỉnh ----------


def test_reupload_corrected_file_moves_status_to_corrected():
    dataset_id = _new_tabmis_dataset("UC23E", critical_fields=["ma_don_vi", "so_tien"])
    bad_content = _build_xlsx(
        _SCHEMA_COLUMNS,
        [["", "Đơn vị 1", "1000000"]],  # thiếu ma_don_vi
    )
    session = _upload(dataset_id, bad_content).json()
    assert session["status"] == "ROW_ERRORS"
    original_run_id = session["ingestion_run_id"]

    fixed_content = _build_xlsx(_SCHEMA_COLUMNS, [["DV01", "Đơn vị 1", "1000000"]])
    resp = _reupload(session["id"], fixed_content)
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["id"] == session["id"]  # cùng 1 phiên, không tạo phiên mới
    assert updated["status"] == "CORRECTED"
    assert updated["error_message"] == ""
    assert updated["ingestion_run_id"] != original_run_id  # phiên ingest mới cho lần kiểm tra lại
    assert updated["file_name"] == "tabmis-data-sua.xlsx"

    new_run = client.get(f"/ingestion-runs/{updated['ingestion_run_id']}").json()
    assert new_run["status"] == "SUCCESS"

    row_errors = client.get(f"/tabmis-intake/{session['id']}/row-errors").json()
    assert row_errors == []  # lỗi dòng cũ đã bị xoá sau khi kiểm tra lại thành công

    status_resp = client.get(f"/tabmis-intake/{session['id']}/status").json()
    assert status_resp["session"]["status"] == "CORRECTED"
    assert status_resp["allowed_actions"] == ["REUPLOAD"]


def test_reupload_still_has_row_errors_keeps_row_errors_status():
    dataset_id = _new_tabmis_dataset("UC23F", critical_fields=["ma_don_vi"])
    bad_content = _build_xlsx(_SCHEMA_COLUMNS, [["", "Đơn vị 1", "100"]])
    session = _upload(dataset_id, bad_content).json()
    assert session["status"] == "ROW_ERRORS"

    still_bad_content = _build_xlsx(
        _SCHEMA_COLUMNS, [["", "Đơn vị 1 (đã sửa tên)", "200"]]
    )
    resp = _reupload(session["id"], still_bad_content)
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["status"] == "ROW_ERRORS"

    row_errors = client.get(f"/tabmis-intake/{session['id']}/row-errors").json()
    assert len(row_errors) == 1
    assert row_errors[0]["field_name"] == "ma_don_vi"


def test_reupload_still_template_invalid():
    dataset_id = _new_tabmis_dataset("UC23G")
    content = _build_xlsx(_SCHEMA_COLUMNS, [["DV01", "Đơn vị 1", "100"]])
    session = _upload(dataset_id, content).json()
    assert session["status"] == "RECEIVED"

    missing_col_content = _build_xlsx(["ma_don_vi", "ten_don_vi"], [["DV01", "Đơn vị 1"]])
    resp = _reupload(session["id"], missing_col_content)
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["status"] == "TEMPLATE_INVALID"
    assert "so_tien" in updated["control_totals"]["missing_columns"]


def test_reupload_404_when_session_not_found():
    content = _build_xlsx(_SCHEMA_COLUMNS, [])
    resp = client.post(
        "/tabmis-intake/999999/reupload",
        data={"uploaded_by": "canbo01"},
        files={
            "file": (
                "data.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "TABMIS_INTAKE_SESSION_NOT_FOUND"


def test_reupload_422_when_file_extension_invalid():
    dataset_id = _new_tabmis_dataset("UC23H")
    content = _build_xlsx(_SCHEMA_COLUMNS, [["DV01", "Đơn vị 1", "100"]])
    session = _upload(dataset_id, content).json()

    resp = client.post(
        f"/tabmis-intake/{session['id']}/reupload",
        data={"uploaded_by": "canbo01"},
        files={"file": ("data.csv", b"not-excel", "text/csv")},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_TABMIS_INTAKE_UPLOAD"
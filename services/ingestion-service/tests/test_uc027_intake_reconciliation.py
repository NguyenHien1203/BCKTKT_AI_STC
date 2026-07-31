"""Integration test UC-027: Đối soát phiên intake, qua HTTP API (SQLite
in-memory).

Luồng nghiệp vụ (docs/use_cases.json id=27):
1. Chọn phiên cần đối soát.
2. Hệ thống hiển thị tổng kiểm soát.
3. Đánh dấu phát hiện thiếu/sai.
4. Hệ thống lưu.
5. Đóng phiên đối soát đạt yêu cầu.
6. Hệ thống cập nhật trạng thái.
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
            "name": "Nguồn dữ liệu test UC-27",
            "source_system": source_system,
            "provider": "Bộ Tài chính",
            "owner": "Cục CNTT",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _schema_fields():
    return [
        {"name": col, "data_type": "STRING", "nullable": False, "description": ""}
        for col in _SCHEMA_COLUMNS
    ]


def _create_dataset(data_source_id, code):
    resp = client.post(
        "/datasets",
        json={
            "data_source_id": data_source_id,
            "code": code,
            "name": "Tập dữ liệu test UC-27",
            "schema_fields": _schema_fields(),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _build_xlsx(columns, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(columns)
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _new_intake_session(prefix, rows=None):
    """Tạo sẵn 1 phiên tiếp nhận TABMIS đã RECEIVED (điều kiện cần để
    UC-027 có gì đối soát)."""
    data_source_id = _create_data_source(f"{prefix}-SRC")
    dataset_id = _create_dataset(data_source_id, f"{prefix}-DS")
    content = _build_xlsx(
        _SCHEMA_COLUMNS,
        rows or [["DV01", "Đơn vị 1", "1000000"], ["DV02", "Đơn vị 2", "2000000"]],
    )
    resp = client.post(
        "/tabmis-intake/upload",
        data={"dataset_id": dataset_id, "uploaded_by": "canbo01"},
        files={
            "file": (
                "tabmis-data.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _open_reconciliation(session_id, reconciled_by="qtth01"):
    return client.post(
        "/intake-reconciliations",
        json={"session_id": session_id, "reconciled_by": reconciled_by},
    )


# ---------- Bước 1-2: Chọn phiên cần đối soát -> hiển thị tổng kiểm soát ----------


def test_open_reconciliation_returns_control_totals_snapshot():
    session_id = _new_intake_session("UC27A")
    resp = _open_reconciliation(session_id)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["session_id"] == session_id
    assert body["status"] == "OPEN"
    assert body["control_totals"]["records_read"] == 2
    assert body["findings"] == []
    assert body["reconciled_by"] == "qtth01"
    assert body["closed_at"] is None


def test_open_reconciliation_reuses_existing_open_session():
    session_id = _new_intake_session("UC27B")
    first = _open_reconciliation(session_id).json()
    second = _open_reconciliation(session_id, reconciled_by="qtth02").json()
    assert second["id"] == first["id"]
    # không tạo trùng: vẫn giữ nguyên người mở lượt đối soát đầu tiên
    assert second["reconciled_by"] == "qtth01"


def test_open_reconciliation_404_when_session_not_found():
    resp = _open_reconciliation(999999)
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "TABMIS_INTAKE_SESSION_NOT_FOUND"


def test_open_reconciliation_422_when_reconciled_by_blank():
    session_id = _new_intake_session("UC27C")
    resp = client.post(
        "/intake-reconciliations", json={"session_id": session_id, "reconciled_by": "   "}
    )
    assert resp.status_code == 422


# ---------- Bước 3-4: Đánh dấu phát hiện thiếu/sai -> hệ thống lưu ----------


def test_mark_finding_missing_and_incorrect_are_saved():
    session_id = _new_intake_session("UC27D")
    reconciliation_id = _open_reconciliation(session_id).json()["id"]

    resp = client.post(
        f"/intake-reconciliations/{reconciliation_id}/findings",
        json={
            "finding_type": "MISSING",
            "field_name": "DV03",
            "description": "Thiếu bản ghi đơn vị DV03 so với tổng kiểm soát nguồn",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["findings"]) == 1
    assert body["findings"][0]["finding_type"] == "MISSING"
    assert body["findings"][0]["status"] == "OPEN"

    resp = client.post(
        f"/intake-reconciliations/{reconciliation_id}/findings",
        json={
            "finding_type": "INCORRECT",
            "field_name": "so_tien",
            "description": "Số tiền DV01 lệch so với tổng kiểm soát nguồn",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["findings"]) == 2
    assert body["findings"][1]["finding_type"] == "INCORRECT"

    # Truy xuất lại vẫn còn đủ 2 phát hiện (đã được lưu).
    get_resp = client.get(f"/intake-reconciliations/{reconciliation_id}")
    assert get_resp.status_code == 200
    assert len(get_resp.json()["findings"]) == 2


def test_mark_finding_404_when_reconciliation_not_found():
    resp = client.post(
        "/intake-reconciliations/999999/findings",
        json={"finding_type": "MISSING", "field_name": "x", "description": "y"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "INTAKE_RECONCILIATION_NOT_FOUND"


def test_mark_finding_422_when_finding_type_invalid():
    session_id = _new_intake_session("UC27E")
    reconciliation_id = _open_reconciliation(session_id).json()["id"]
    resp = client.post(
        f"/intake-reconciliations/{reconciliation_id}/findings",
        json={"finding_type": "OTHER", "field_name": "x", "description": "y"},
    )
    assert resp.status_code == 422


def test_mark_finding_422_when_reconciliation_already_closed():
    session_id = _new_intake_session("UC27F")
    reconciliation_id = _open_reconciliation(session_id).json()["id"]
    close_resp = client.post(
        f"/intake-reconciliations/{reconciliation_id}/close",
        json={"closed_by": "qtth01", "close_note": "Đạt yêu cầu, không phát hiện sai lệch"},
    )
    assert close_resp.status_code == 200, close_resp.text

    resp = client.post(
        f"/intake-reconciliations/{reconciliation_id}/findings",
        json={"finding_type": "MISSING", "field_name": "x", "description": "y"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INTAKE_RECONCILIATION_ALREADY_CLOSED"


# ---------- Bước 5-6: Đóng phiên đối soát đạt yêu cầu -> cập nhật trạng thái ----------


def test_close_reconciliation_succeeds_when_no_findings():
    session_id = _new_intake_session("UC27G")
    reconciliation_id = _open_reconciliation(session_id).json()["id"]

    resp = client.post(
        f"/intake-reconciliations/{reconciliation_id}/close",
        json={"closed_by": "qtth01", "close_note": "Đối soát đạt yêu cầu"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "CLOSED"
    assert body["closed_by"] == "qtth01"
    assert body["closed_at"] is not None
    assert body["close_note"] == "Đối soát đạt yêu cầu"


def test_close_reconciliation_rejected_when_unresolved_findings_remain():
    session_id = _new_intake_session("UC27H")
    reconciliation_id = _open_reconciliation(session_id).json()["id"]
    client.post(
        f"/intake-reconciliations/{reconciliation_id}/findings",
        json={"finding_type": "MISSING", "field_name": "DV03", "description": "Thiếu DV03"},
    )

    resp = client.post(
        f"/intake-reconciliations/{reconciliation_id}/close",
        json={"closed_by": "qtth01", "close_note": ""},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INTAKE_RECONCILIATION_HAS_UNRESOLVED_FINDINGS"


def test_close_reconciliation_succeeds_after_resolving_all_findings():
    session_id = _new_intake_session("UC27I")
    reconciliation_id = _open_reconciliation(session_id).json()["id"]
    client.post(
        f"/intake-reconciliations/{reconciliation_id}/findings",
        json={"finding_type": "MISSING", "field_name": "DV03", "description": "Thiếu DV03"},
    )

    resolve_resp = client.post(
        f"/intake-reconciliations/{reconciliation_id}/findings/0/resolve"
    )
    assert resolve_resp.status_code == 200, resolve_resp.text
    assert resolve_resp.json()["findings"][0]["status"] == "RESOLVED"

    close_resp = client.post(
        f"/intake-reconciliations/{reconciliation_id}/close",
        json={"closed_by": "qtth01", "close_note": "Đã bổ sung DV03, đạt yêu cầu"},
    )
    assert close_resp.status_code == 200, close_resp.text
    assert close_resp.json()["status"] == "CLOSED"


def test_resolve_finding_404_when_index_out_of_range():
    session_id = _new_intake_session("UC27J")
    reconciliation_id = _open_reconciliation(session_id).json()["id"]
    resp = client.post(f"/intake-reconciliations/{reconciliation_id}/findings/0/resolve")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "INTAKE_RECONCILIATION_FINDING_NOT_FOUND"


def test_close_reconciliation_422_when_already_closed():
    session_id = _new_intake_session("UC27K")
    reconciliation_id = _open_reconciliation(session_id).json()["id"]
    first_close = client.post(
        f"/intake-reconciliations/{reconciliation_id}/close",
        json={"closed_by": "qtth01", "close_note": ""},
    )
    assert first_close.status_code == 200

    second_close = client.post(
        f"/intake-reconciliations/{reconciliation_id}/close",
        json={"closed_by": "qtth01", "close_note": ""},
    )
    assert second_close.status_code == 422
    assert second_close.json()["detail"]["code"] == "INTAKE_RECONCILIATION_ALREADY_CLOSED"


def test_close_reconciliation_404_when_not_found():
    resp = client.post(
        "/intake-reconciliations/999999/close",
        json={"closed_by": "qtth01", "close_note": ""},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "INTAKE_RECONCILIATION_NOT_FOUND"


# ---------- Danh sách phiên đối soát ----------


def test_list_reconciliations_filters_by_session_and_status():
    session_id = _new_intake_session("UC27L")
    reconciliation_id = _open_reconciliation(session_id).json()["id"]

    all_resp = client.get("/intake-reconciliations", params={"session_id": session_id})
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 1

    open_resp = client.get(
        "/intake-reconciliations", params={"session_id": session_id, "status": "OPEN"}
    )
    assert len(open_resp.json()) == 1

    client.post(
        f"/intake-reconciliations/{reconciliation_id}/close",
        json={"closed_by": "qtth01", "close_note": ""},
    )
    closed_resp = client.get(
        "/intake-reconciliations", params={"session_id": session_id, "status": "CLOSED"}
    )
    assert len(closed_resp.json()) == 1
    open_resp_after = client.get(
        "/intake-reconciliations", params={"session_id": session_id, "status": "OPEN"}
    )
    assert len(open_resp_after.json()) == 0
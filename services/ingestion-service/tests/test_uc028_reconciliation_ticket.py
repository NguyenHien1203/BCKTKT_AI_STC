"""Integration test UC-028: Xử lý ticket đối soát với chủ quản nguồn, qua
HTTP API (SQLite in-memory).

Luồng nghiệp vụ (docs/use_cases.json id=28):
1. Mở ticket xử lý với chủ quản nguồn.
2. Hệ thống lưu ticket + thông báo.
3. Cập nhật tiến độ xử lý ticket.
4. Hệ thống lưu lịch sử.
5. Đóng ticket khi resolved.
6. Hệ thống cập nhật + ghi nhật ký.
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
            "name": "Nguồn dữ liệu test UC-28",
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
            "name": "Tập dữ liệu test UC-28",
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


def _open_reconciliation(prefix, reconciled_by="qtth01"):
    session_id = _new_intake_session(prefix)
    resp = client.post(
        "/intake-reconciliations",
        json={"session_id": session_id, "reconciled_by": reconciled_by},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _open_ticket(reconciliation_id, source_owner="Cục CNTT - TABMIS", opened_by="qtth01"):
    return client.post(
        "/reconciliation-tickets",
        json={
            "reconciliation_id": reconciliation_id,
            "source_owner": source_owner,
            "title": "Đề nghị xác nhận thiếu bản ghi DV03",
            "description": "So với tổng kiểm soát nguồn thì thiếu 1 dòng đơn vị",
            "opened_by": opened_by,
        },
    )


# ---------- Bước 1: Mở ticket xử lý với chủ quản nguồn -> hệ thống lưu + thông báo ----------


def test_open_ticket_saves_and_notifies():
    reconciliation_id = _open_reconciliation("UC28A")
    resp = _open_ticket(reconciliation_id)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["reconciliation_id"] == reconciliation_id
    assert body["status"] == "OPEN"
    assert body["source_owner"] == "Cục CNTT - TABMIS"
    assert body["notified"] is True
    assert body["history"] == []
    assert body["closed_at"] is None


def test_open_ticket_404_when_reconciliation_not_found():
    resp = client.post(
        "/reconciliation-tickets",
        json={
            "reconciliation_id": 999999,
            "source_owner": "Cục CNTT",
            "title": "Ticket test",
        },
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "INTAKE_RECONCILIATION_NOT_FOUND"


def test_open_ticket_422_when_source_owner_blank():
    reconciliation_id = _open_reconciliation("UC28B")
    resp = client.post(
        "/reconciliation-tickets",
        json={
            "reconciliation_id": reconciliation_id,
            "source_owner": "   ",
            "title": "Ticket test",
        },
    )
    assert resp.status_code == 422


def test_open_ticket_422_when_title_blank():
    reconciliation_id = _open_reconciliation("UC28C")
    resp = client.post(
        "/reconciliation-tickets",
        json={
            "reconciliation_id": reconciliation_id,
            "source_owner": "Cục CNTT",
            "title": "",
        },
    )
    assert resp.status_code == 422


# ---------- Bước 2-3: Cập nhật tiến độ xử lý ticket -> hệ thống lưu lịch sử ----------


def test_add_progress_is_saved_to_history():
    reconciliation_id = _open_reconciliation("UC28D")
    ticket_id = _open_ticket(reconciliation_id).json()["id"]

    resp = client.post(
        f"/reconciliation-tickets/{ticket_id}/progress",
        json={
            "note": "Đã liên hệ chủ quản nguồn, đang chờ xác nhận",
            "updated_by": "qtth01",
            "status": "IN_PROGRESS",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "IN_PROGRESS"
    assert len(body["history"]) == 1
    assert body["history"][0]["note"] == "Đã liên hệ chủ quản nguồn, đang chờ xác nhận"
    assert body["history"][0]["status"] == "IN_PROGRESS"

    resp = client.post(
        f"/reconciliation-tickets/{ticket_id}/progress",
        json={
            "note": "Chủ quản nguồn xác nhận đã bổ sung dữ liệu",
            "updated_by": "qtth01",
            "status": "RESOLVED",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "RESOLVED"
    assert len(body["history"]) == 2

    get_resp = client.get(f"/reconciliation-tickets/{ticket_id}")
    assert get_resp.status_code == 200
    assert len(get_resp.json()["history"]) == 2


def test_add_progress_404_when_ticket_not_found():
    resp = client.post(
        "/reconciliation-tickets/999999/progress",
        json={"note": "x", "updated_by": "qtth01"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "RECONCILIATION_TICKET_NOT_FOUND"


def test_add_progress_422_when_note_blank():
    reconciliation_id = _open_reconciliation("UC28E")
    ticket_id = _open_ticket(reconciliation_id).json()["id"]
    resp = client.post(
        f"/reconciliation-tickets/{ticket_id}/progress",
        json={"note": "   ", "updated_by": "qtth01"},
    )
    assert resp.status_code == 422


def test_add_progress_422_when_ticket_already_closed():
    reconciliation_id = _open_reconciliation("UC28F")
    ticket_id = _open_ticket(reconciliation_id).json()["id"]
    client.post(
        f"/reconciliation-tickets/{ticket_id}/progress",
        json={"note": "Đã xử lý xong", "updated_by": "qtth01", "status": "RESOLVED"},
    )
    close_resp = client.post(
        f"/reconciliation-tickets/{ticket_id}/close",
        json={"closed_by": "qtth01", "close_note": "Đã xử lý xong với chủ quản nguồn"},
    )
    assert close_resp.status_code == 200, close_resp.text

    resp = client.post(
        f"/reconciliation-tickets/{ticket_id}/progress",
        json={"note": "cập nhật thêm", "updated_by": "qtth01"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "RECONCILIATION_TICKET_ALREADY_CLOSED"


# ---------- Bước 4-5: Đóng ticket khi resolved -> hệ thống cập nhật + ghi nhật ký ----------


def test_close_ticket_succeeds_when_resolved():
    reconciliation_id = _open_reconciliation("UC28G")
    ticket_id = _open_ticket(reconciliation_id).json()["id"]
    client.post(
        f"/reconciliation-tickets/{ticket_id}/progress",
        json={"note": "Đã xử lý xong", "updated_by": "qtth01", "status": "RESOLVED"},
    )

    resp = client.post(
        f"/reconciliation-tickets/{ticket_id}/close",
        json={"closed_by": "qtth01", "close_note": "Đã xử lý xong với chủ quản nguồn"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "CLOSED"
    assert body["closed_by"] == "qtth01"
    assert body["closed_at"] is not None
    assert body["close_note"] == "Đã xử lý xong với chủ quản nguồn"
    # ghi nhật ký: 1 mốc RESOLVED + 1 mốc CLOSED
    assert len(body["history"]) == 2
    assert body["history"][-1]["status"] == "CLOSED"


def test_close_ticket_422_when_not_resolved():
    reconciliation_id = _open_reconciliation("UC28H")
    ticket_id = _open_ticket(reconciliation_id).json()["id"]

    resp = client.post(
        f"/reconciliation-tickets/{ticket_id}/close",
        json={"closed_by": "qtth01", "close_note": ""},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "RECONCILIATION_TICKET_NOT_RESOLVED"


def test_close_ticket_422_when_already_closed():
    reconciliation_id = _open_reconciliation("UC28I")
    ticket_id = _open_ticket(reconciliation_id).json()["id"]
    client.post(
        f"/reconciliation-tickets/{ticket_id}/progress",
        json={"note": "Đã xử lý xong", "updated_by": "qtth01", "status": "RESOLVED"},
    )
    first_close = client.post(
        f"/reconciliation-tickets/{ticket_id}/close",
        json={"closed_by": "qtth01", "close_note": ""},
    )
    assert first_close.status_code == 200

    second_close = client.post(
        f"/reconciliation-tickets/{ticket_id}/close",
        json={"closed_by": "qtth01", "close_note": ""},
    )
    assert second_close.status_code == 422
    assert second_close.json()["detail"]["code"] == "RECONCILIATION_TICKET_ALREADY_CLOSED"


def test_close_ticket_404_when_not_found():
    resp = client.post(
        "/reconciliation-tickets/999999/close",
        json={"closed_by": "qtth01", "close_note": ""},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "RECONCILIATION_TICKET_NOT_FOUND"


# ---------- Danh sách ticket ----------


def test_list_tickets_filters_by_reconciliation_and_status():
    reconciliation_id = _open_reconciliation("UC28J")
    ticket_id = _open_ticket(reconciliation_id).json()["id"]

    all_resp = client.get(
        "/reconciliation-tickets", params={"reconciliation_id": reconciliation_id}
    )
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 1

    open_resp = client.get(
        "/reconciliation-tickets",
        params={"reconciliation_id": reconciliation_id, "status": "OPEN"},
    )
    assert len(open_resp.json()) == 1

    client.post(
        f"/reconciliation-tickets/{ticket_id}/progress",
        json={"note": "Đã xử lý xong", "updated_by": "qtth01", "status": "RESOLVED"},
    )
    client.post(
        f"/reconciliation-tickets/{ticket_id}/close",
        json={"closed_by": "qtth01", "close_note": ""},
    )

    closed_resp = client.get(
        "/reconciliation-tickets",
        params={"reconciliation_id": reconciliation_id, "status": "CLOSED"},
    )
    assert len(closed_resp.json()) == 1
    open_resp_after = client.get(
        "/reconciliation-tickets",
        params={"reconciliation_id": reconciliation_id, "status": "OPEN"},
    )
    assert len(open_resp_after.json()) == 0
"""Integration test UC-037: Phê duyệt thay đổi danh mục nhạy cảm, qua HTTP

API (SQLite in-memory). Actor "Lãnh đạo Phòng nghiệp vụ Sở Tài chính".
Luồng:
1. Xem các yêu cầu chờ duyệt.
2. Hệ thống hiển thị diff.
3. Phê duyệt / từ chối.
4. Hệ thống cập nhật và áp dụng thay đổi.
5. Ghi lý do phê duyệt -- Hệ thống lưu vào nhật ký.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_sensitive_entry(code="NM01", name="Xi măng PC40", **kwargs) -> dict:
    payload = {
        "catalog_type": "ITEM",
        "code": code,
        "name": name,
        "unit": "Tấn",
        "is_sensitive": True,
        **kwargs,
    }
    resp = client.post("/catalog-entries", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _propose_change(entry_id, **kwargs) -> dict:
    payload = {
        "requested_by": "Nguyễn Văn A",
        "reason": "Cập nhật theo báo giá mới",
        **kwargs,
    }
    resp = client.post(f"/catalog-entries/{entry_id}/change-requests", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Bước 1: Xem các yêu cầu chờ duyệt ----------


def test_list_pending_change_requests_hien_thi_yeu_cau_cho_duyet():
    entry = _create_sensitive_entry(code="UC37-P1", name="Mục nhạy cảm 1")
    request = _propose_change(entry["id"], proposed_name="Tên mới đề nghị")

    resp = client.get("/catalog-change-approvals/pending")
    assert resp.status_code == 200, resp.text
    ids = [r["id"] for r in resp.json()]
    assert request["id"] in ids


def test_list_pending_change_requests_loc_theo_catalog_type():
    resp_item = client.post(
        "/catalog-entries",
        json={
            "catalog_type": "DOCUMENT_TYPE",
            "code": "UC37-DT1",
            "name": "Công văn mật",
            "is_sensitive": True,
        },
    )
    entry = resp_item.json()
    _propose_change(entry["id"], proposed_name="Công văn mật (đã đổi tên)")

    resp = client.get(
        "/catalog-change-approvals/pending", params={"catalog_type": "DOCUMENT_TYPE"}
    )
    assert resp.status_code == 200, resp.text
    for r in resp.json():
        assert r["catalog_type"] == "DOCUMENT_TYPE"


def test_list_pending_khong_gom_yeu_cau_da_xu_ly():
    entry = _create_sensitive_entry(code="UC37-P2", name="Mục nhạy cảm 2")
    request = _propose_change(entry["id"], proposed_name="Tên mới 2")
    client.post(
        f"/catalog-change-approvals/{request['id']}/approve",
        json={"decided_by": "Trưởng phòng B", "reason": "Đồng ý theo đề xuất"},
    )

    resp = client.get("/catalog-change-approvals/pending")
    ids = [r["id"] for r in resp.json()]
    assert request["id"] not in ids


# ---------- Bước 2: Hệ thống hiển thị diff ----------


def test_get_diff_hien_thi_dung_cac_truong_thay_doi():
    entry = _create_sensitive_entry(
        code="UC37-D1", name="Tên cũ", unit="Tấn", description="Mô tả cũ"
    )
    request = _propose_change(
        entry["id"],
        proposed_name="Tên mới",
        proposed_description="Mô tả mới",
    )

    resp = client.get(f"/catalog-change-approvals/{request['id']}/diff")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["entry"]["code"] == "UC37-D1"
    fields = {c["field"]: c for c in data["changes"]}
    assert set(fields.keys()) == {"name", "description"}
    assert fields["name"]["old_value"] == "Tên cũ"
    assert fields["name"]["new_value"] == "Tên mới"
    assert fields["name"]["changed"] is True
    # unit không được đề nghị đổi -- không xuất hiện trong diff
    assert "unit" not in fields


def test_get_diff_404_khi_yeu_cau_khong_ton_tai():
    resp = client.get("/catalog-change-approvals/999999/diff")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "CATALOG_CHANGE_REQUEST_NOT_FOUND"


# ---------- Bước 3 + 4: Phê duyệt -- Hệ thống cập nhật và áp dụng thay đổi ----------


def test_approve_ap_dung_thay_doi_vao_muc_danh_muc():
    entry = _create_sensitive_entry(code="UC37-A1", name="Tên cũ A1")
    request = _propose_change(entry["id"], proposed_name="Tên mới A1")

    resp = client.post(
        f"/catalog-change-approvals/{request['id']}/approve",
        json={"decided_by": "Trưởng phòng Tài chính", "reason": "Phù hợp với hồ sơ đính kèm"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["entry"]["name"] == "Tên mới A1"
    assert data["entry"]["version"] == 2

    # yêu cầu chuyển sang APPROVED, không còn ở danh sách chờ duyệt
    detail = client.get(f"/catalog-entries/change-requests/{request['id']}").json()
    assert detail["status"] == "APPROVED"
    assert detail["reviewed_by"] == "Trưởng phòng Tài chính"


def test_approve_422_khi_thieu_ly_do():
    entry = _create_sensitive_entry(code="UC37-A2", name="Tên cũ A2")
    request = _propose_change(entry["id"], proposed_name="Tên mới A2")

    resp = client.post(
        f"/catalog-change-approvals/{request['id']}/approve",
        json={"decided_by": "Trưởng phòng Tài chính", "reason": "   "},
    )
    assert resp.status_code == 422, resp.text


def test_approve_404_khi_yeu_cau_khong_ton_tai():
    resp = client.post(
        "/catalog-change-approvals/999999/approve",
        json={"decided_by": "Trưởng phòng Tài chính", "reason": "Đồng ý"},
    )
    assert resp.status_code == 404


def test_approve_422_khi_yeu_cau_da_xu_ly_truoc_do():
    entry = _create_sensitive_entry(code="UC37-A3", name="Tên cũ A3")
    request = _propose_change(entry["id"], proposed_name="Tên mới A3")
    client.post(
        f"/catalog-change-approvals/{request['id']}/approve",
        json={"decided_by": "Trưởng phòng Tài chính", "reason": "Đồng ý lần 1"},
    )
    resp = client.post(
        f"/catalog-change-approvals/{request['id']}/approve",
        json={"decided_by": "Trưởng phòng Tài chính", "reason": "Duyệt lại"},
    )
    assert resp.status_code == 422


# ---------- Bước 3: Từ chối (KHÔNG áp dụng thay đổi) ----------


def test_reject_khong_ap_dung_thay_doi():
    entry = _create_sensitive_entry(code="UC37-R1", name="Tên cũ R1")
    request = _propose_change(entry["id"], proposed_name="Tên mới R1")

    resp = client.post(
        f"/catalog-change-approvals/{request['id']}/reject",
        json={"decided_by": "Trưởng phòng Tài chính", "reason": "Thiếu căn cứ pháp lý"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["request"]["status"] == "REJECTED"

    unchanged_entry = client.get(f"/catalog-entries/{entry['id']}").json()
    assert unchanged_entry["name"] == "Tên cũ R1"
    assert unchanged_entry["version"] == 1


def test_reject_422_khi_thieu_ly_do():
    entry = _create_sensitive_entry(code="UC37-R2", name="Tên cũ R2")
    request = _propose_change(entry["id"], proposed_name="Tên mới R2")

    resp = client.post(
        f"/catalog-change-approvals/{request['id']}/reject",
        json={"decided_by": "Trưởng phòng Tài chính", "reason": ""},
    )
    assert resp.status_code == 422, resp.text


# ---------- Bước 5: Ghi lý do phê duyệt -- Hệ thống lưu vào nhật ký ----------


def test_approve_ghi_vao_nhat_ky_kem_ly_do_va_diff():
    entry = _create_sensitive_entry(code="UC37-L1", name="Tên cũ L1")
    request = _propose_change(entry["id"], proposed_name="Tên mới L1")

    approve_resp = client.post(
        f"/catalog-change-approvals/{request['id']}/approve",
        json={"decided_by": "Trưởng phòng Tài chính", "reason": "Đã đối chiếu hồ sơ gốc"},
    )
    audit_log = approve_resp.json()["audit_log"]
    assert audit_log["action"] == "APPROVED"
    assert audit_log["decided_by"] == "Trưởng phòng Tài chính"
    assert audit_log["decision_reason"] == "Đã đối chiếu hồ sơ gốc"
    assert "Tên mới L1" in audit_log["diff_snapshot"]

    resp = client.get("/catalog-change-approvals/audit-logs", params={"request_id": request["id"]})
    assert resp.status_code == 200, resp.text
    logs = resp.json()
    assert len(logs) == 1
    assert logs[0]["action"] == "APPROVED"


def test_reject_cung_ghi_vao_nhat_ky():
    entry = _create_sensitive_entry(code="UC37-L2", name="Tên cũ L2")
    request = _propose_change(entry["id"], proposed_name="Tên mới L2")

    client.post(
        f"/catalog-change-approvals/{request['id']}/reject",
        json={"decided_by": "Trưởng phòng Tài chính", "reason": "Không đủ căn cứ"},
    )

    resp = client.get(
        "/catalog-change-approvals/audit-logs",
        params={"request_id": request["id"], "action": "REJECTED"},
    )
    assert resp.status_code == 200, resp.text
    logs = resp.json()
    assert len(logs) == 1
    assert logs[0]["decision_reason"] == "Không đủ căn cứ"


def test_audit_logs_loc_theo_entry_id_va_catalog_type():
    entry = _create_sensitive_entry(code="UC37-L3", name="Tên cũ L3")
    request = _propose_change(entry["id"], proposed_name="Tên mới L3")
    client.post(
        f"/catalog-change-approvals/{request['id']}/approve",
        json={"decided_by": "Trưởng phòng Tài chính", "reason": "Đồng ý"},
    )

    resp = client.get(
        "/catalog-change-approvals/audit-logs",
        params={"entry_id": entry["id"], "catalog_type": "ITEM"},
    )
    assert resp.status_code == 200, resp.text
    assert any(log["entry_id"] == entry["id"] for log in resp.json())
"""Integration test UC-044: Phê duyệt chỉ tiêu, qua HTTP API (SQLite

in-memory). Actor "Chủ quản Nghiệp vụ". Luồng:
1. Xem chỉ tiêu chờ phê duyệt. Hệ thống hiển thị.
2. Xem kết quả kiểm thử + so sánh với số liệu hiện tại. Hệ thống hiển
   thị.
3. Phê duyệt / từ chối chỉ tiêu. Hệ thống công bố hoặc trả về cho
   Quản trị Dữ liệu.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_indicator(
    name="Tổng chi ngân sách",
    expression="SUM('so_tien')",
    domain="Ngân sách",
    **kwargs,
) -> dict:
    payload = {"name": name, "expression": expression, "domain": domain, **kwargs}
    resp = client.post("/semantic-indicators", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _test_indicator(indicator_id: int, sample_rows, tested_by=None) -> dict:
    payload = {"sample_rows": sample_rows}
    if tested_by:
        payload["tested_by"] = tested_by
    resp = client.post(f"/semantic-indicators/{indicator_id}/test", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _submit(indicator_id: int, submitted_by="qtdl01") -> dict:
    resp = client.post(
        f"/indicator-approvals/{indicator_id}/submit", json={"submitted_by": submitted_by}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------- Tiền đề: gửi chỉ tiêu chờ phê duyệt ----------


def test_submit_for_approval_thanh_cong():
    ind = _create_indicator(name="Chỉ tiêu gửi duyệt A")
    updated = _submit(ind["id"])
    assert updated["status"] == "PENDING_APPROVAL"
    assert updated["version"] == 2  # bump_version() từ update_indicator()


def test_submit_for_approval_422_khi_khong_o_trang_thai_draft():
    ind = _create_indicator(name="Chỉ tiêu gửi duyệt B")
    _submit(ind["id"])
    resp = client.post(
        f"/indicator-approvals/{ind['id']}/submit", json={"submitted_by": "qtdl01"}
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INDICATOR_NOT_PENDING_APPROVAL"


def test_submit_for_approval_404_khi_khong_ton_tai():
    resp = client.post("/indicator-approvals/999999/submit", json={"submitted_by": "qtdl01"})
    assert resp.status_code == 404, resp.text


# ---------- Bước 1: Xem chỉ tiêu chờ phê duyệt ----------


def test_list_pending_hien_thi_dung_danh_sach():
    draft = _create_indicator(name="Chỉ tiêu DRAFT không hiện", domain="Tài sản")
    pending = _create_indicator(name="Chỉ tiêu PENDING hiện", domain="Tài sản")
    _submit(pending["id"])

    resp = client.get("/indicator-approvals/pending")
    assert resp.status_code == 200, resp.text
    ids = [i["id"] for i in resp.json()]
    assert pending["id"] in ids
    assert draft["id"] not in ids


def test_list_pending_loc_theo_domain():
    a = _create_indicator(name="Chỉ tiêu lọc domain A", domain="Ngân sách")
    b = _create_indicator(name="Chỉ tiêu lọc domain B", domain="Giá")
    _submit(a["id"])
    _submit(b["id"])

    resp = client.get("/indicator-approvals/pending", params={"domain": "Giá"})
    assert resp.status_code == 200, resp.text
    ids = [i["id"] for i in resp.json()]
    assert b["id"] in ids
    assert a["id"] not in ids


# ---------- Bước 2: Xem kết quả kiểm thử + so sánh với số liệu hiện tại ----------


def test_comparison_chua_co_so_lieu_hien_tai_khi_chua_tung_active():
    ind = _create_indicator(name="Chỉ tiêu so sánh chưa từng ACTIVE")
    _test_indicator(ind["id"], [{"so_tien": 100}, {"so_tien": 200}])
    _submit(ind["id"])

    resp = client.get(f"/indicator-approvals/{ind['id']}/comparison")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["new_value"] == 300
    assert data["current_value"] is None
    assert data["has_current_value"] is False
    assert data["delta"] is None


def test_comparison_so_sanh_dung_voi_so_lieu_dang_active():
    ind = _create_indicator(name="Chỉ tiêu so sánh có ACTIVE trước đó")
    # Lượt kiểm thử đầu -- đại diện "số liệu hiện tại" khi CHƯA active.
    _test_indicator(ind["id"], [{"so_tien": 100}])
    _submit(ind["id"])
    # Duyệt lần 1 để chỉ tiêu trở thành ACTIVE.
    client.post(
        f"/indicator-approvals/{ind['id']}/approve",
        json={"decided_by": "cqnv01", "reason": "Duyệt lần đầu"},
    )
    # Lượt kiểm thử NÀY chạy lúc đang ACTIVE -- sẽ là "số liệu hiện tại".
    _test_indicator(ind["id"], [{"so_tien": 100}, {"so_tien": 50}])

    # Sửa biểu thức/nội dung -> quay về DRAFT, rồi gửi duyệt lại.
    resp = client.put(
        f"/semantic-indicators/{ind['id']}",
        json={"status": "DRAFT", "changed_by": "qtdl01", "note": "Sửa lại để duyệt lần 2"},
    )
    assert resp.status_code == 200, resp.text
    # Lượt kiểm thử mới nhất -- "kết quả kiểm thử" của lần chờ duyệt này.
    _test_indicator(ind["id"], [{"so_tien": 100}, {"so_tien": 50}, {"so_tien": 50}])
    _submit(ind["id"])

    resp = client.get(f"/indicator-approvals/{ind['id']}/comparison")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_current_value"] is True
    assert data["current_value"] == 150
    assert data["new_value"] == 200
    assert data["delta"] == 50
    assert round(data["delta_percent"], 3) == round((50 / 150) * 100, 3)


def test_comparison_404_khi_chi_tieu_khong_ton_tai():
    resp = client.get("/indicator-approvals/999999/comparison")
    assert resp.status_code == 404, resp.text


# ---------- Bước 3: Phê duyệt / từ chối chỉ tiêu ----------


def test_approve_cong_bo_thanh_cong():
    ind = _create_indicator(name="Chỉ tiêu duyệt thành công")
    _test_indicator(ind["id"], [{"so_tien": 10}])
    _submit(ind["id"])

    resp = client.post(
        f"/indicator-approvals/{ind['id']}/approve",
        json={"decided_by": "cqnv01", "reason": "Số liệu hợp lý, đồng ý công bố"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["indicator"]["status"] == "ACTIVE"
    assert data["decision"]["action"] == "APPROVED"
    assert data["decision"]["decision_reason"] == "Số liệu hợp lý, đồng ý công bố"
    assert data["decision"]["comparison_snapshot"]["new_value"] == 10

    # Đã công bố -- không còn nằm trong hàng đợi chờ duyệt.
    resp2 = client.get("/indicator-approvals/pending")
    assert ind["id"] not in [i["id"] for i in resp2.json()]


def test_reject_tra_ve_cho_quan_tri_du_lieu():
    ind = _create_indicator(name="Chỉ tiêu từ chối")
    _test_indicator(ind["id"], [{"so_tien": 10}])
    _submit(ind["id"])

    resp = client.post(
        f"/indicator-approvals/{ind['id']}/reject",
        json={"decided_by": "cqnv01", "reason": "Biểu thức chưa đúng nghiệp vụ, đề nghị sửa lại"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["indicator"]["status"] == "DRAFT"
    assert data["decision"]["action"] == "REJECTED"

    resp2 = client.get("/indicator-approvals/pending")
    assert ind["id"] not in [i["id"] for i in resp2.json()]


def test_approve_422_khi_thieu_ly_do():
    ind = _create_indicator(name="Chỉ tiêu thiếu lý do duyệt")
    _submit(ind["id"])
    resp = client.post(
        f"/indicator-approvals/{ind['id']}/approve",
        json={"decided_by": "cqnv01", "reason": "   "},
    )
    assert resp.status_code == 422, resp.text


def test_reject_422_khi_thieu_ly_do():
    ind = _create_indicator(name="Chỉ tiêu thiếu lý do từ chối")
    _submit(ind["id"])
    resp = client.post(
        f"/indicator-approvals/{ind['id']}/reject",
        json={"decided_by": "cqnv01", "reason": ""},
    )
    assert resp.status_code == 422, resp.text


def test_approve_422_khi_khong_o_trang_thai_pending_approval():
    ind = _create_indicator(name="Chỉ tiêu chưa gửi duyệt")
    resp = client.post(
        f"/indicator-approvals/{ind['id']}/approve",
        json={"decided_by": "cqnv01", "reason": "Thử duyệt khi còn DRAFT"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INDICATOR_NOT_PENDING_APPROVAL"


def test_reject_422_khi_da_duyet_truoc_do():
    ind = _create_indicator(name="Chỉ tiêu duyệt rồi từ chối lại")
    _submit(ind["id"])
    client.post(
        f"/indicator-approvals/{ind['id']}/approve",
        json={"decided_by": "cqnv01", "reason": "Duyệt lần đầu"},
    )
    resp = client.post(
        f"/indicator-approvals/{ind['id']}/reject",
        json={"decided_by": "cqnv01", "reason": "Từ chối lại sau khi đã duyệt"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INDICATOR_NOT_PENDING_APPROVAL"


def test_approve_404_khi_chi_tieu_khong_ton_tai():
    resp = client.post(
        "/indicator-approvals/999999/approve",
        json={"decided_by": "cqnv01", "reason": "Không tồn tại"},
    )
    assert resp.status_code == 404, resp.text


# ---------- Nhật ký quyết định ----------


def test_list_decisions_ghi_dung_lich_su():
    ind = _create_indicator(name="Chỉ tiêu nhật ký quyết định")
    _submit(ind["id"])
    client.post(
        f"/indicator-approvals/{ind['id']}/reject",
        json={"decided_by": "cqnv01", "reason": "Lần 1: cần sửa lại biểu thức"},
    )
    _submit(ind["id"])
    client.post(
        f"/indicator-approvals/{ind['id']}/approve",
        json={"decided_by": "cqnv01", "reason": "Lần 2: đã sửa đúng, đồng ý"},
    )

    resp = client.get(f"/indicator-approvals/{ind['id']}/decisions")
    assert resp.status_code == 200, resp.text
    decisions = resp.json()
    assert len(decisions) == 2
    actions = {d["action"] for d in decisions}
    assert actions == {"APPROVED", "REJECTED"}


def test_list_decisions_404_khi_khong_ton_tai():
    resp = client.get("/indicator-approvals/999999/decisions")
    assert resp.status_code == 404, resp.text


# ---------- Kiểm thử không phá vỡ UC-043 hiện có ----------


def test_audit_log_ghi_du_hanh_dong_submitted_approved():
    ind = _create_indicator(name="Chỉ tiêu audit log đầy đủ")
    _submit(ind["id"])
    client.post(
        f"/indicator-approvals/{ind['id']}/approve",
        json={"decided_by": "cqnv01", "reason": "Đồng ý công bố"},
    )
    resp = client.get(f"/semantic-indicators/{ind['id']}/audit-logs")
    assert resp.status_code == 200, resp.text
    actions = {a["action"] for a in resp.json()}
    assert "SUBMITTED_FOR_APPROVAL" in actions
    assert "APPROVED" in actions
    assert "CREATED" in actions
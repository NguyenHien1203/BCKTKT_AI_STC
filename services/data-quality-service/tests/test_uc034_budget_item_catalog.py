"""Integration test UC-034: Quản lý danh mục khoản mục NSNN, qua HTTP API

(SQLite in-memory). Actor "Quản trị Danh mục". Luồng:
1. Xem cây khoản mục NSNN (Chương/Loại/Khoản/Mục/Tiểu mục). Hệ thống hiển thị.
2. Thêm/Sửa entry. Hệ thống quản lý phiên bản theo năm ngân sách.
3. Đề nghị thay đổi khoản mục nhạy cảm. Hệ thống lưu yêu cầu chờ duyệt.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_item(
    code="CH01", name="Chương Test", level="CHUONG", budget_year=2026, **kwargs
) -> dict:
    payload = {
        "code": code,
        "name": name,
        "level": level,
        "budget_year": budget_year,
        **kwargs,
    }
    resp = client.post("/budget-item-catalog", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Bước 1: Xem cây khoản mục NSNN ----------


def test_get_tree_hien_thi_cay_phan_cap_theo_nam():
    root = _create_item(code="CH-TREE", name="Chương Tài chính", level="CHUONG", budget_year=2030)
    child = _create_item(
        code="LOAI-TREE",
        name="Loại Quản lý nhà nước",
        level="LOAI",
        budget_year=2030,
        parent_id=root["id"],
    )

    resp = client.get("/budget-item-catalog/tree", params={"budget_year": 2030})
    assert resp.status_code == 200, resp.text
    tree = resp.json()

    root_node = next((n for n in tree if n["item"]["id"] == root["id"]), None)
    assert root_node is not None
    child_codes = [c["item"]["code"] for c in root_node["children"]]
    assert child["code"] in child_codes


def test_get_tree_khong_lan_sang_nam_khac():
    _create_item(code="CH-Y1", name="Chương năm 2031", level="CHUONG", budget_year=2031)
    resp = client.get("/budget-item-catalog/tree", params={"budget_year": 2032})
    tree = resp.json()
    codes = [n["item"]["code"] for n in tree]
    assert "CH-Y1" not in codes


def test_list_budget_items_loc_theo_parent_va_level():
    root = _create_item(code="CH-LIST", name="Chương A", level="CHUONG", budget_year=2033)
    _create_item(
        code="LOAI-LIST",
        name="Loại B",
        level="LOAI",
        budget_year=2033,
        parent_id=root["id"],
    )

    resp = client.get("/budget-item-catalog", params={"parent_id": root["id"]})
    codes = [i["code"] for i in resp.json()]
    assert "LOAI-LIST" in codes
    assert "CH-LIST" not in codes

    resp_root = client.get("/budget-item-catalog", params={"only_root": True, "budget_year": 2033})
    root_codes = [i["code"] for i in resp_root.json()]
    assert "CH-LIST" in root_codes
    assert "LOAI-LIST" not in root_codes


def test_get_budget_item_khong_ton_tai_tra_404():
    resp = client.get("/budget-item-catalog/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "BUDGET_ITEM_NOT_FOUND"


# ---------- Bước 2: Thêm / Sửa entry (quản lý phiên bản theo năm) ----------


def test_them_entry_moi_luu_version_1_theo_nam_ngan_sach():
    item = _create_item(code="CH-NEW", name="Chương Mới", budget_year=2034, effective_from="2034-01-01")
    assert item["version"] == 1
    assert item["status"] == "ACTIVE"
    assert item["budget_year"] == 2034

    versions = client.get(f"/budget-item-catalog/{item['id']}/versions").json()
    assert len(versions) == 1
    assert versions[0]["version"] == 1


def test_them_entry_trung_ma_trong_cung_nam_tra_409():
    _create_item(code="CH-DUP", name="Chương Trùng", budget_year=2035)
    resp = client.post(
        "/budget-item-catalog",
        json={"code": "CH-DUP", "name": "Khác", "level": "CHUONG", "budget_year": 2035},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "BUDGET_ITEM_CODE_EXISTS"


def test_them_entry_cung_ma_nhung_khac_nam_ngan_sach_duoc_phep():
    _create_item(code="CH-YEARDIFF", name="Chương A", budget_year=2036)
    resp = client.post(
        "/budget-item-catalog",
        json={"code": "CH-YEARDIFF", "name": "Chương A năm sau", "level": "CHUONG", "budget_year": 2037},
    )
    assert resp.status_code == 201, resp.text


def test_them_entry_level_khong_hop_le_tra_422():
    resp = client.post(
        "/budget-item-catalog",
        json={"code": "CH-BADLEVEL", "name": "X", "level": "INVALID", "budget_year": 2038},
    )
    assert resp.status_code == 422


def test_them_entry_cha_khac_nam_ngan_sach_tra_422():
    root = _create_item(code="CH-PARENTYEAR", name="Chương", budget_year=2039)
    resp = client.post(
        "/budget-item-catalog",
        json={
            "code": "LOAI-PARENTYEAR",
            "name": "Loại",
            "level": "LOAI",
            "budget_year": 2040,
            "parent_id": root["id"],
        },
    )
    assert resp.status_code == 422


def test_them_entry_level_cha_con_sai_thu_tu_tra_422():
    root = _create_item(code="CH-ORDER", name="Chương", level="CHUONG", budget_year=2041)
    resp = client.post(
        "/budget-item-catalog",
        json={
            "code": "CH-ORDER-CHILD",
            "name": "Chương con sai cấp",
            "level": "CHUONG",
            "budget_year": 2041,
            "parent_id": root["id"],
        },
    )
    assert resp.status_code == 422


def test_sua_entry_tang_version_va_ghi_lich_su():
    item = _create_item(code="CH-EDIT", name="Chương Cũ", budget_year=2042)
    resp = client.put(
        f"/budget-item-catalog/{item['id']}", json={"name": "Chương Đã Sửa", "note": "cap nhat ten"}
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["name"] == "Chương Đã Sửa"
    assert updated["version"] == 2

    versions = client.get(f"/budget-item-catalog/{item['id']}/versions").json()
    assert len(versions) == 2
    assert versions[0]["version"] == 2  # mới nhất trước


def test_sua_entry_khong_ton_tai_tra_404():
    resp = client.put("/budget-item-catalog/999999", json={"name": "X"})
    assert resp.status_code == 404


def test_sua_entry_nhay_cam_bi_chan_tra_409():
    item = _create_item(code="CH-SENSITIVE-EDIT", name="Chương Nhạy Cảm", budget_year=2043, is_sensitive=True)
    resp = client.put(f"/budget-item-catalog/{item['id']}", json={"name": "Không được sửa trực tiếp"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "BUDGET_ITEM_SENSITIVE_REQUIRES_APPROVAL"


# ---------- Bước 3: Đề nghị thay đổi khoản mục nhạy cảm ----------


def test_de_nghi_thay_doi_khoan_muc_nhay_cam_luu_cho_duyet():
    item = _create_item(code="CH-PROPOSE", name="Chương Nhạy Cảm 2", budget_year=2044, is_sensitive=True)
    resp = client.post(
        f"/budget-item-catalog/{item['id']}/change-requests",
        json={
            "requested_by": "canbo.a",
            "reason": "Cập nhật lại tên theo quyết định mới",
            "proposed_name": "Chương Nhạy Cảm Đã Đổi Tên",
        },
    )
    assert resp.status_code == 201, resp.text
    request = resp.json()
    assert request["status"] == "PENDING"

    # Khoản mục CHƯA thay đổi cho đến khi được duyệt
    unchanged = client.get(f"/budget-item-catalog/{item['id']}").json()
    assert unchanged["name"] == "Chương Nhạy Cảm 2"
    assert unchanged["version"] == 1


def test_de_nghi_thay_doi_khoan_muc_khong_nhay_cam_tra_422():
    item = _create_item(code="CH-NOTSENSITIVE", name="Chương Thường", budget_year=2045, is_sensitive=False)
    resp = client.post(
        f"/budget-item-catalog/{item['id']}/change-requests",
        json={"requested_by": "canbo.b", "reason": "test", "proposed_name": "X"},
    )
    assert resp.status_code == 422


def test_de_nghi_thay_doi_khoan_muc_khong_ton_tai_tra_404():
    resp = client.post(
        "/budget-item-catalog/999999/change-requests",
        json={"requested_by": "canbo.c", "reason": "test", "proposed_name": "X"},
    )
    assert resp.status_code == 404


def test_de_nghi_thay_doi_thieu_truong_de_nghi_tra_422():
    item = _create_item(code="CH-EMPTYPROPOSE", name="Chương Nhạy Cảm 3", budget_year=2046, is_sensitive=True)
    resp = client.post(
        f"/budget-item-catalog/{item['id']}/change-requests",
        json={"requested_by": "canbo.d", "reason": "test"},
    )
    assert resp.status_code == 422


def test_duyet_yeu_cau_ap_dung_thay_doi_va_tang_version():
    item = _create_item(code="CH-APPROVE", name="Chương Nhạy Cảm 4", budget_year=2047, is_sensitive=True)
    request = client.post(
        f"/budget-item-catalog/{item['id']}/change-requests",
        json={
            "requested_by": "canbo.e",
            "reason": "Đổi tên theo văn bản mới",
            "proposed_name": "Chương Đã Duyệt",
        },
    ).json()

    resp = client.post(
        f"/budget-item-catalog/change-requests/{request['id']}/approve",
        json={"reviewed_by": "truongphong.x", "review_note": "Đồng ý"},
    )
    assert resp.status_code == 200, resp.text
    approved_item = resp.json()
    assert approved_item["name"] == "Chương Đã Duyệt"
    assert approved_item["version"] == 2

    req_after = client.get(f"/budget-item-catalog/change-requests/{request['id']}").json()
    assert req_after["status"] == "APPROVED"
    assert req_after["reviewed_by"] == "truongphong.x"

    versions = client.get(f"/budget-item-catalog/{item['id']}/versions").json()
    assert len(versions) == 2


def test_tu_choi_yeu_cau_khong_ap_dung_thay_doi():
    item = _create_item(code="CH-REJECT", name="Chương Nhạy Cảm 5", budget_year=2048, is_sensitive=True)
    request = client.post(
        f"/budget-item-catalog/{item['id']}/change-requests",
        json={"requested_by": "canbo.f", "reason": "Đề nghị đổi tên", "proposed_name": "Tên mới"},
    ).json()

    resp = client.post(
        f"/budget-item-catalog/change-requests/{request['id']}/reject",
        json={"reviewed_by": "truongphong.y", "review_note": "Không đủ căn cứ"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "REJECTED"

    unchanged = client.get(f"/budget-item-catalog/{item['id']}").json()
    assert unchanged["name"] == "Chương Nhạy Cảm 5"
    assert unchanged["version"] == 1


def test_xu_ly_lai_yeu_cau_da_xu_ly_tra_422():
    item = _create_item(code="CH-TWICE", name="Chương Nhạy Cảm 6", budget_year=2049, is_sensitive=True)
    request = client.post(
        f"/budget-item-catalog/{item['id']}/change-requests",
        json={"requested_by": "canbo.g", "reason": "test", "proposed_name": "X"},
    ).json()
    client.post(
        f"/budget-item-catalog/change-requests/{request['id']}/approve",
        json={"reviewed_by": "truongphong.z"},
    )
    resp = client.post(
        f"/budget-item-catalog/change-requests/{request['id']}/reject",
        json={"reviewed_by": "truongphong.z"},
    )
    assert resp.status_code == 422


def test_duyet_yeu_cau_khong_ton_tai_tra_404():
    resp = client.post(
        "/budget-item-catalog/change-requests/999999/approve",
        json={"reviewed_by": "x"},
    )
    assert resp.status_code == 404


def test_liet_ke_yeu_cau_theo_trang_thai_va_khoan_muc():
    item = _create_item(code="CH-LISTREQ", name="Chương Nhạy Cảm 7", budget_year=2050, is_sensitive=True)
    client.post(
        f"/budget-item-catalog/{item['id']}/change-requests",
        json={"requested_by": "canbo.h", "reason": "test", "proposed_name": "X"},
    )
    resp = client.get(
        "/budget-item-catalog/change-requests/list",
        params={"item_id": item["id"], "status": "PENDING"},
    )
    assert resp.status_code == 200
    requests = resp.json()
    assert len(requests) == 1
    assert requests[0]["item_id"] == item["id"]
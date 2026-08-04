"""Integration test UC-036: Quản lý danh mục mặt hàng, loại văn bản,

nguồn vốn, qua HTTP API (SQLite in-memory). Actor "Quản trị Danh mục".
Luồng:
1. Xem từng danh mục (mặt hàng / loại văn bản / nguồn vốn). Hệ thống
   hiển thị.
2. Thêm / Sửa entry. Hệ thống quản lý phiên bản.
3. Đề nghị thay đổi danh mục nhạy cảm. Hệ thống lưu yêu cầu chờ duyệt.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_entry(
    catalog_type="ITEM", code="MH01", name="Bàn làm việc", **kwargs
) -> dict:
    payload = {"catalog_type": catalog_type, "code": code, "name": name, **kwargs}
    resp = client.post("/catalog-entries", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Bước 1: Xem từng danh mục ----------


def test_list_catalog_entries_hien_thi_danh_muc():
    created = _create_entry(catalog_type="ITEM", code="IT-L1", name="Máy in")
    resp = client.get("/catalog-entries")
    assert resp.status_code == 200, resp.text
    codes = [e["code"] for e in resp.json()]
    assert created["code"] in codes


def test_list_catalog_entries_loc_theo_catalog_type():
    _create_entry(catalog_type="ITEM", code="IT-A", name="Máy tính")
    _create_entry(catalog_type="DOCUMENT_TYPE", code="DT-A", name="Công văn")
    _create_entry(catalog_type="FUNDING_SOURCE", code="FS-A", name="Ngân sách tỉnh")

    resp = client.get("/catalog-entries", params={"catalog_type": "DOCUMENT_TYPE"})
    assert resp.status_code == 200, resp.text
    codes = [e["code"] for e in resp.json()]
    assert "DT-A" in codes
    assert "IT-A" not in codes
    assert "FS-A" not in codes


def test_list_catalog_entries_loc_theo_status():
    entry = _create_entry(catalog_type="ITEM", code="IT-STATUS", name="Mục để đóng")
    client.put(f"/catalog-entries/{entry['id']}", json={"status": "CLOSED"})

    resp = client.get("/catalog-entries", params={"status": "CLOSED"})
    assert resp.status_code == 200, resp.text
    codes = [e["code"] for e in resp.json()]
    assert "IT-STATUS" in codes


def test_get_catalog_entry_404_khi_khong_ton_tai():
    resp = client.get("/catalog-entries/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "CATALOG_ENTRY_NOT_FOUND"


# ---------- Bước 2: Thêm / Sửa entry (hệ thống quản lý phiên bản) ----------


def test_create_catalog_entry_luu_version_1_va_lich_su():
    entry = _create_entry(
        catalog_type="ITEM", code="IT-V1", name="Ghế xoay", unit="Cái"
    )
    assert entry["version"] == 1
    assert entry["unit"] == "Cái"

    resp = client.get(f"/catalog-entries/{entry['id']}/versions")
    assert resp.status_code == 200, resp.text
    versions = resp.json()
    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["code"] == "IT-V1"


def test_create_catalog_entry_409_khi_trung_ma_trong_cung_catalog_type():
    _create_entry(catalog_type="ITEM", code="IT-DUP", name="Mục gốc")
    resp = client.post(
        "/catalog-entries",
        json={"catalog_type": "ITEM", "code": "IT-DUP", "name": "Mục trùng mã"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "CATALOG_ENTRY_CODE_EXISTS"


def test_create_catalog_entry_cho_phep_trung_ma_o_catalog_type_khac():
    _create_entry(catalog_type="ITEM", code="TRUNG-MA", name="Mặt hàng")
    resp = client.post(
        "/catalog-entries",
        json={
            "catalog_type": "DOCUMENT_TYPE",
            "code": "TRUNG-MA",
            "name": "Loại văn bản cùng mã",
        },
    )
    assert resp.status_code == 201, resp.text


def test_create_catalog_entry_422_khi_catalog_type_khong_hop_le():
    resp = client.post(
        "/catalog-entries",
        json={"catalog_type": "KHONG_HOP_LE", "code": "X1", "name": "X"},
    )
    assert resp.status_code == 422


def test_update_catalog_entry_tang_version_va_ghi_lich_su():
    entry = _create_entry(catalog_type="FUNDING_SOURCE", code="FS-UPD", name="Nguồn cũ")
    resp = client.put(
        f"/catalog-entries/{entry['id']}",
        json={"name": "Nguồn mới", "note": "Đổi tên cho rõ nghĩa"},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["version"] == 2
    assert updated["name"] == "Nguồn mới"

    versions = client.get(f"/catalog-entries/{entry['id']}/versions").json()
    assert len(versions) == 2
    assert versions[0]["version"] == 2
    assert versions[0]["change_note"] == "Đổi tên cho rõ nghĩa"


def test_update_catalog_entry_404_khi_khong_ton_tai():
    resp = client.put("/catalog-entries/999999", json={"name": "X"})
    assert resp.status_code == 404


def test_update_catalog_entry_422_khi_da_dong():
    entry = _create_entry(catalog_type="ITEM", code="IT-CLOSED", name="Mục sẽ đóng")
    client.put(f"/catalog-entries/{entry['id']}", json={"status": "CLOSED"})
    resp = client.put(f"/catalog-entries/{entry['id']}", json={"name": "Sửa nữa"})
    assert resp.status_code == 422


def test_update_catalog_entry_409_khi_muc_nhay_cam():
    entry = _create_entry(
        catalog_type="DOCUMENT_TYPE", code="DT-SENS", name="Loại nhạy cảm", is_sensitive=True
    )
    resp = client.put(f"/catalog-entries/{entry['id']}", json={"name": "Sửa trực tiếp"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "CATALOG_ENTRY_SENSITIVE_REQUIRES_APPROVAL"


# ---------- Bước 3: Đề nghị thay đổi danh mục nhạy cảm ----------


def test_propose_change_luu_yeu_cau_cho_duyet_khong_ap_dung_ngay():
    entry = _create_entry(
        catalog_type="FUNDING_SOURCE", code="FS-SENS", name="Nguồn nhạy cảm", is_sensitive=True
    )
    resp = client.post(
        f"/catalog-entries/{entry['id']}/change-requests",
        json={
            "requested_by": "nguyenvana",
            "reason": "Đổi tên cho đúng quy định mới",
            "proposed_name": "Nguồn vốn đã đổi tên",
        },
    )
    assert resp.status_code == 201, resp.text
    request = resp.json()
    assert request["status"] == "PENDING"
    assert request["entry_id"] == entry["id"]
    assert request["catalog_type"] == "FUNDING_SOURCE"

    # Chưa áp dụng thay đổi -- mục vẫn giữ tên cũ, version cũ.
    still = client.get(f"/catalog-entries/{entry['id']}").json()
    assert still["name"] == "Nguồn nhạy cảm"
    assert still["version"] == 1


def test_propose_change_422_khi_muc_khong_nhay_cam():
    entry = _create_entry(catalog_type="ITEM", code="IT-NOTSENS", name="Mục thường")
    resp = client.post(
        f"/catalog-entries/{entry['id']}/change-requests",
        json={"requested_by": "u1", "reason": "Thử", "proposed_name": "Tên khác"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_CATALOG_CHANGE_REQUEST"


def test_propose_change_404_khi_muc_khong_ton_tai():
    resp = client.post(
        "/catalog-entries/999999/change-requests",
        json={"requested_by": "u1", "reason": "Thử", "proposed_name": "X"},
    )
    assert resp.status_code == 404


def test_propose_change_422_khi_thieu_de_xuat():
    entry = _create_entry(
        catalog_type="ITEM", code="IT-SENS2", name="Mục nhạy cảm 2", is_sensitive=True
    )
    resp = client.post(
        f"/catalog-entries/{entry['id']}/change-requests",
        json={"requested_by": "u1", "reason": "Thử không có đề xuất gì"},
    )
    assert resp.status_code == 422


def test_approve_change_ap_dung_thay_doi_va_tang_version():
    entry = _create_entry(
        catalog_type="DOCUMENT_TYPE", code="DT-APPROVE", name="Tên cũ", is_sensitive=True
    )
    request = client.post(
        f"/catalog-entries/{entry['id']}/change-requests",
        json={"requested_by": "u1", "reason": "Đổi tên", "proposed_name": "Tên mới đã duyệt"},
    ).json()

    resp = client.post(
        f"/catalog-entries/change-requests/{request['id']}/approve",
        json={"reviewed_by": "truongphong", "review_note": "Đồng ý"},
    )
    assert resp.status_code == 200, resp.text
    approved_entry = resp.json()
    assert approved_entry["name"] == "Tên mới đã duyệt"
    assert approved_entry["version"] == 2

    reviewed_request = client.get(
        f"/catalog-entries/change-requests/{request['id']}"
    ).json()
    assert reviewed_request["status"] == "APPROVED"
    assert reviewed_request["reviewed_by"] == "truongphong"


def test_reject_change_khong_ap_dung_thay_doi():
    entry = _create_entry(
        catalog_type="FUNDING_SOURCE", code="FS-REJECT", name="Tên gốc", is_sensitive=True
    )
    request = client.post(
        f"/catalog-entries/{entry['id']}/change-requests",
        json={"requested_by": "u1", "reason": "Đổi tên", "proposed_name": "Tên đề xuất"},
    ).json()

    resp = client.post(
        f"/catalog-entries/change-requests/{request['id']}/reject",
        json={"reviewed_by": "truongphong", "review_note": "Chưa hợp lý"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "REJECTED"

    still = client.get(f"/catalog-entries/{entry['id']}").json()
    assert still["name"] == "Tên gốc"
    assert still["version"] == 1


def test_approve_reject_422_khi_da_xu_ly_truoc_do():
    entry = _create_entry(
        catalog_type="ITEM", code="IT-DOUBLE", name="Tên gốc", is_sensitive=True
    )
    request = client.post(
        f"/catalog-entries/{entry['id']}/change-requests",
        json={"requested_by": "u1", "reason": "Đổi tên", "proposed_name": "Tên mới"},
    ).json()
    client.post(
        f"/catalog-entries/change-requests/{request['id']}/approve",
        json={"reviewed_by": "u2"},
    )
    resp = client.post(
        f"/catalog-entries/change-requests/{request['id']}/reject",
        json={"reviewed_by": "u2"},
    )
    assert resp.status_code == 422


def test_list_change_requests_loc_theo_entry_va_catalog_type_va_status():
    entry1 = _create_entry(
        catalog_type="ITEM", code="IT-CR1", name="Mục 1", is_sensitive=True
    )
    entry2 = _create_entry(
        catalog_type="FUNDING_SOURCE", code="FS-CR2", name="Mục 2", is_sensitive=True
    )
    client.post(
        f"/catalog-entries/{entry1['id']}/change-requests",
        json={"requested_by": "u1", "reason": "r1", "proposed_name": "N1"},
    )
    client.post(
        f"/catalog-entries/{entry2['id']}/change-requests",
        json={"requested_by": "u1", "reason": "r2", "proposed_name": "N2"},
    )

    resp = client.get("/catalog-entries/change-requests/list", params={"entry_id": entry1["id"]})
    assert resp.status_code == 200, resp.text
    results = resp.json()
    assert all(r["entry_id"] == entry1["id"] for r in results)

    resp2 = client.get(
        "/catalog-entries/change-requests/list", params={"catalog_type": "FUNDING_SOURCE"}
    )
    assert all(r["catalog_type"] == "FUNDING_SOURCE" for r in resp2.json())

    resp3 = client.get("/catalog-entries/change-requests/list", params={"status": "PENDING"})
    assert all(r["status"] == "PENDING" for r in resp3.json())


def test_get_change_request_404_khi_khong_ton_tai():
    resp = client.get("/catalog-entries/change-requests/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "CATALOG_CHANGE_REQUEST_NOT_FOUND"
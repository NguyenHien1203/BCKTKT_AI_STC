"""Integration test UC-033: Quản lý danh mục đơn vị, qua HTTP API (SQLite

in-memory). Actor "Quản trị Danh mục". Luồng:
1. Xem danh mục đơn vị (cây phân cấp). Hệ thống hiển thị.
2. Thêm đơn vị mới. Hệ thống kiểm tra trùng mã + lưu phiên bản.
3. Sửa thông tin đơn vị. Hệ thống lưu.
4. Đóng / Tách / Sáp nhập đơn vị (lifecycle). Hệ thống lưu effective_from/to.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_unit(code="SO01", name="Sở Tài chính", unit_type="SO", **kwargs) -> dict:
    payload = {"code": code, "name": name, "unit_type": unit_type, **kwargs}
    resp = client.post("/org-unit-catalog", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Bước 1: Xem danh mục đơn vị (cây phân cấp) ----------


def test_get_tree_hien_thi_cay_phan_cap():
    root = _create_unit(code="SO-TREE", name="Sở Tài chính")
    child = _create_unit(code="PHONG-TREE", name="Phòng Ngân sách", unit_type="PHONG", parent_id=root["id"])

    resp = client.get("/org-unit-catalog/tree")
    assert resp.status_code == 200, resp.text
    tree = resp.json()

    root_node = next((n for n in tree if n["unit"]["id"] == root["id"]), None)
    assert root_node is not None
    child_codes = [c["unit"]["code"] for c in root_node["children"]]
    assert child["code"] in child_codes


def test_list_org_units_loc_theo_parent_va_status():
    root = _create_unit(code="SO-LIST", name="Sở A")
    _create_unit(code="PHONG-LIST", name="Phòng B", unit_type="PHONG", parent_id=root["id"])

    resp = client.get("/org-unit-catalog", params={"parent_id": root["id"]})
    assert resp.status_code == 200
    codes = [u["code"] for u in resp.json()]
    assert "PHONG-LIST" in codes
    assert "SO-LIST" not in codes

    resp_root = client.get("/org-unit-catalog", params={"only_root": True})
    root_codes = [u["code"] for u in resp_root.json()]
    assert "SO-LIST" in root_codes
    assert "PHONG-LIST" not in root_codes


def test_get_org_unit_khong_ton_tai_tra_404():
    resp = client.get("/org-unit-catalog/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "ORG_UNIT_CATALOG_NOT_FOUND"


# ---------- Bước 2: Thêm đơn vị mới ----------


def test_them_don_vi_moi_luu_version_1():
    unit = _create_unit(code="SO-NEW", name="Sở Mới", effective_from="2026-01-01")
    assert unit["version"] == 1
    assert unit["status"] == "ACTIVE"
    assert unit["effective_from"] == "2026-01-01"

    versions = client.get(f"/org-unit-catalog/{unit['id']}/versions").json()
    assert len(versions) == 1
    assert versions[0]["version"] == 1


def test_them_don_vi_trung_ma_tra_409():
    _create_unit(code="SO-DUP", name="Sở Trùng")
    resp = client.post("/org-unit-catalog", json={"code": "SO-DUP", "name": "Sở Khác", "unit_type": "SO"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "ORG_UNIT_CATALOG_CODE_EXISTS"


def test_them_don_vi_unit_type_khong_hop_le_tra_422():
    resp = client.post(
        "/org-unit-catalog", json={"code": "SO-BADTYPE", "name": "Sở X", "unit_type": "INVALID"}
    )
    assert resp.status_code == 422


def test_them_don_vi_cha_khong_ton_tai_tra_422():
    resp = client.post(
        "/org-unit-catalog",
        json={"code": "SO-BADPARENT", "name": "Sở Y", "unit_type": "SO", "parent_id": 999999},
    )
    assert resp.status_code == 422


# ---------- Bước 3: Sửa thông tin đơn vị ----------


def test_sua_thong_tin_don_vi_tang_version_va_ghi_lich_su():
    unit = _create_unit(code="SO-EDIT", name="Sở Cũ")
    resp = client.put(f"/org-unit-catalog/{unit['id']}", json={"name": "Sở Đã Sửa", "note": "cap nhat ten"})
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["name"] == "Sở Đã Sửa"
    assert updated["version"] == 2

    versions = client.get(f"/org-unit-catalog/{unit['id']}/versions").json()
    assert len(versions) == 2
    assert versions[0]["version"] == 2  # mới nhất trước


def test_sua_don_vi_khong_ton_tai_tra_404():
    resp = client.put("/org-unit-catalog/999999", json={"name": "X"})
    assert resp.status_code == 404


def test_sua_don_vi_da_dong_tra_422():
    unit = _create_unit(code="SO-CLOSED-EDIT", name="Sở Đóng")
    close_resp = client.post(
        f"/org-unit-catalog/{unit['id']}/close", json={"effective_to": "2026-06-30"}
    )
    assert close_resp.status_code == 200
    resp = client.put(f"/org-unit-catalog/{unit['id']}", json={"name": "Không được sửa"})
    assert resp.status_code == 422


def test_sua_doi_don_vi_cha():
    parent = _create_unit(code="SO-PARENT2", name="Sở Cha 2")
    child = _create_unit(code="PHONG-CHILD2", name="Phòng Con 2", unit_type="PHONG")
    resp = client.put(f"/org-unit-catalog/{child['id']}", json={"parent_id": parent["id"]})
    assert resp.status_code == 200
    assert resp.json()["parent_id"] == parent["id"]


# ---------- Bước 4: Đóng / Tách / Sáp nhập đơn vị (lifecycle) ----------


def test_dong_don_vi_luu_effective_to():
    unit = _create_unit(code="SO-CLOSE", name="Sở Đóng 2")
    resp = client.post(f"/org-unit-catalog/{unit['id']}/close", json={"effective_to": "2026-12-31", "note": "giải thể"})
    assert resp.status_code == 200, resp.text
    closed = resp.json()
    assert closed["status"] == "CLOSED"
    assert closed["effective_to"] == "2026-12-31"
    assert closed["lifecycle_action"] == "CLOSE"


def test_dong_don_vi_da_dong_tra_409():
    unit = _create_unit(code="SO-CLOSE-TWICE", name="Sở Đóng 2 Lần")
    client.post(f"/org-unit-catalog/{unit['id']}/close", json={"effective_to": "2026-06-30"})
    resp = client.post(f"/org-unit-catalog/{unit['id']}/close", json={"effective_to": "2026-07-01"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "ORG_UNIT_CATALOG_ALREADY_CLOSED"


def test_dong_don_vi_khong_ton_tai_tra_404():
    resp = client.post("/org-unit-catalog/999999/close", json={"effective_to": "2026-06-30"})
    assert resp.status_code == 404


def test_tach_don_vi_dong_goc_va_tao_don_vi_moi():
    source = _create_unit(code="SO-SPLIT", name="Sở Tách")
    resp = client.post(
        f"/org-unit-catalog/{source['id']}/split",
        json={
            "effective_from": "2026-07-01",
            "new_units": [
                {"code": "SO-SPLIT-A", "name": "Sở Tách A"},
                {"code": "SO-SPLIT-B", "name": "Sở Tách B"},
            ],
            "note": "tách theo quyết định X",
        },
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()

    assert result["source"]["status"] == "CLOSED"
    assert result["source"]["effective_to"] == "2026-07-01"
    assert result["source"]["lifecycle_action"] == "SPLIT"

    assert len(result["created_units"]) == 2
    for created in result["created_units"]:
        assert created["status"] == "ACTIVE"
        assert created["effective_from"] == "2026-07-01"
        assert created["lifecycle_action"] == "SPLIT"
        assert created["split_from_id"] == source["id"]
        assert created["parent_id"] == source["parent_id"]


def test_tach_don_vi_can_it_nhat_2_don_vi_moi_tra_422():
    source = _create_unit(code="SO-SPLIT-ONE", name="Sở Tách Một")
    resp = client.post(
        f"/org-unit-catalog/{source['id']}/split",
        json={
            "effective_from": "2026-07-01",
            "new_units": [{"code": "SO-SPLIT-ONLY", "name": "Chỉ 1"}],
        },
    )
    assert resp.status_code == 422


def test_tach_don_vi_ma_moi_trung_don_vi_da_co_tra_409():
    _create_unit(code="SO-EXISTING", name="Sở Đã Có")
    source = _create_unit(code="SO-SPLIT-DUP", name="Sở Tách Trùng")
    resp = client.post(
        f"/org-unit-catalog/{source['id']}/split",
        json={
            "effective_from": "2026-07-01",
            "new_units": [
                {"code": "SO-EXISTING", "name": "Trùng mã"},
                {"code": "SO-SPLIT-DUP-B", "name": "Không trùng"},
            ],
        },
    )
    assert resp.status_code == 409


def test_tach_don_vi_da_dong_tra_422():
    source = _create_unit(code="SO-SPLIT-CLOSED", name="Sở Tách Đã Đóng")
    client.post(f"/org-unit-catalog/{source['id']}/close", json={"effective_to": "2026-01-01"})
    resp = client.post(
        f"/org-unit-catalog/{source['id']}/split",
        json={
            "effective_from": "2026-07-01",
            "new_units": [
                {"code": "SO-SPLIT-CLOSED-A", "name": "A"},
                {"code": "SO-SPLIT-CLOSED-B", "name": "B"},
            ],
        },
    )
    assert resp.status_code == 422


def test_sap_nhap_don_vi_dong_nguon_va_tao_don_vi_moi():
    src1 = _create_unit(code="SO-MERGE-1", name="Sở Sáp Nhập 1")
    src2 = _create_unit(code="SO-MERGE-2", name="Sở Sáp Nhập 2")
    resp = client.post(
        "/org-unit-catalog/merge",
        json={
            "source_unit_ids": [src1["id"], src2["id"]],
            "target": {"code": "SO-MERGED", "name": "Sở Sáp Nhập Mới"},
            "effective_from": "2026-08-01",
            "note": "sáp nhập theo quyết định Y",
        },
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()

    for src in result["source_units"]:
        assert src["status"] == "CLOSED"
        assert src["effective_to"] == "2026-08-01"
        assert src["lifecycle_action"] == "MERGE"

    merged = result["merged_unit"]
    assert merged["status"] == "ACTIVE"
    assert merged["effective_from"] == "2026-08-01"
    assert merged["lifecycle_action"] == "MERGE"
    assert sorted(merged["merged_from_ids"]) == sorted([src1["id"], src2["id"]])


def test_sap_nhap_can_it_nhat_2_don_vi_nguon_tra_422():
    src1 = _create_unit(code="SO-MERGE-ONE", name="Sở Một Mình")
    resp = client.post(
        "/org-unit-catalog/merge",
        json={
            "source_unit_ids": [src1["id"]],
            "target": {"code": "SO-MERGE-ONE-TARGET", "name": "Sở Mới"},
            "effective_from": "2026-08-01",
        },
    )
    assert resp.status_code == 422


def test_sap_nhap_don_vi_nguon_khong_ton_tai_tra_404():
    src1 = _create_unit(code="SO-MERGE-EXIST", name="Sở Tồn Tại")
    resp = client.post(
        "/org-unit-catalog/merge",
        json={
            "source_unit_ids": [src1["id"], 999999],
            "target": {"code": "SO-MERGE-404", "name": "Sở Mới"},
            "effective_from": "2026-08-01",
        },
    )
    assert resp.status_code == 404


def test_sap_nhap_ma_moi_trung_tra_409():
    _create_unit(code="SO-MERGE-TARGET-DUP", name="Sở Đã Có Sẵn")
    src1 = _create_unit(code="SO-MERGE-DUPA", name="Sở A")
    src2 = _create_unit(code="SO-MERGE-DUPB", name="Sở B")
    resp = client.post(
        "/org-unit-catalog/merge",
        json={
            "source_unit_ids": [src1["id"], src2["id"]],
            "target": {"code": "SO-MERGE-TARGET-DUP", "name": "Trùng"},
            "effective_from": "2026-08-01",
        },
    )
    assert resp.status_code == 409
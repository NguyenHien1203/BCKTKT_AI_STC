"""Integration test UC-035: Quản lý danh mục nhóm tài sản, qua HTTP API

(SQLite in-memory). Actor "Quản trị Danh mục". Luồng:
1. Xem danh mục nhóm tài sản (TT 48 / TT 162). Hệ thống hiển thị.
2. Thêm / Sửa entry. Hệ thống quản lý phiên bản.
3. Khai báo tỉ lệ khấu hao theo nhóm. Hệ thống lưu.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_group(
    code="NHOM01", name="Nhà cửa, vật kiến trúc", regulation="TT45", **kwargs
) -> dict:
    payload = {"code": code, "name": name, "regulation": regulation, **kwargs}
    resp = client.post("/asset-group-catalog", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Bước 1: Xem danh mục nhóm tài sản ----------


def test_list_asset_groups_hien_thi_danh_muc():
    created = _create_group(code="NHOM-L1", name="Máy móc thiết bị", regulation="TT45")
    resp = client.get("/asset-group-catalog")
    assert resp.status_code == 200, resp.text
    codes = [g["code"] for g in resp.json()]
    assert created["code"] in codes


def test_list_asset_groups_loc_theo_regulation():
    _create_group(code="NHOM-TT45", name="Phương tiện vận tải", regulation="TT45")
    _create_group(code="NHOM-TT162", name="Nhóm theo TT162", regulation="TT162")

    resp = client.get("/asset-group-catalog", params={"regulation": "TT162"})
    assert resp.status_code == 200, resp.text
    codes = [g["code"] for g in resp.json()]
    assert "NHOM-TT162" in codes
    assert "NHOM-TT45" not in codes


def test_list_asset_groups_loc_theo_status():
    group = _create_group(code="NHOM-STATUS", name="Nhóm để đóng", regulation="TT45")
    client.put(f"/asset-group-catalog/{group['id']}", json={"status": "CLOSED"})

    resp = client.get("/asset-group-catalog", params={"status": "CLOSED"})
    assert resp.status_code == 200, resp.text
    codes = [g["code"] for g in resp.json()]
    assert "NHOM-STATUS" in codes


def test_get_asset_group_404_khi_khong_ton_tai():
    resp = client.get("/asset-group-catalog/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "ASSET_GROUP_NOT_FOUND"


# ---------- Bước 2: Thêm / Sửa entry (hệ thống quản lý phiên bản) ----------


def test_create_asset_group_luu_version_1_va_lich_su():
    group = _create_group(
        code="NHOM-V1", name="Thiết bị, dụng cụ quản lý", regulation="TT45", useful_life_years=5
    )
    assert group["version"] == 1
    assert group["useful_life_years"] == 5

    resp = client.get(f"/asset-group-catalog/{group['id']}/versions")
    assert resp.status_code == 200, resp.text
    versions = resp.json()
    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["code"] == "NHOM-V1"


def test_create_asset_group_409_khi_trung_ma():
    _create_group(code="NHOM-DUP", name="Nhóm gốc", regulation="TT45")
    resp = client.post(
        "/asset-group-catalog",
        json={"code": "NHOM-DUP", "name": "Nhóm trùng mã", "regulation": "TT162"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "ASSET_GROUP_CODE_EXISTS"


def test_create_asset_group_422_khi_regulation_khong_hop_le():
    resp = client.post(
        "/asset-group-catalog",
        json={"code": "NHOM-BADREG", "name": "Nhóm sai", "regulation": "TT99"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_ASSET_GROUP"


def test_update_asset_group_tang_version_va_ghi_lich_su():
    group = _create_group(code="NHOM-UPD", name="Tên cũ", regulation="TT45")
    resp = client.put(
        f"/asset-group-catalog/{group['id']}",
        json={"name": "Tên mới", "note": "Sửa lại tên nhóm"},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["version"] == 2
    assert updated["name"] == "Tên mới"

    versions = client.get(f"/asset-group-catalog/{group['id']}/versions").json()
    assert len(versions) == 2
    assert versions[0]["version"] == 2
    assert versions[0]["change_note"] == "Sửa lại tên nhóm"


def test_update_asset_group_404_khi_khong_ton_tai():
    resp = client.put("/asset-group-catalog/999999", json={"name": "X"})
    assert resp.status_code == 404


def test_update_asset_group_422_khi_da_dong():
    group = _create_group(code="NHOM-CLOSED", name="Nhóm sẽ đóng", regulation="TT45")
    client.put(f"/asset-group-catalog/{group['id']}", json={"status": "CLOSED"})

    resp = client.put(f"/asset-group-catalog/{group['id']}", json={"name": "Sửa sau khi đóng"})
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_ASSET_GROUP"


def test_update_asset_group_clear_useful_life_years():
    group = _create_group(
        code="NHOM-CLEAR", name="Nhóm có tuổi thọ", regulation="TT45", useful_life_years=10
    )
    resp = client.put(
        f"/asset-group-catalog/{group['id']}", json={"clear_useful_life_years": True}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["useful_life_years"] is None


def test_update_asset_group_giu_nguyen_useful_life_years_khi_khong_truyen():
    group = _create_group(
        code="NHOM-KEEP", name="Nhóm giữ tuổi thọ", regulation="TT45", useful_life_years=8
    )
    resp = client.put(f"/asset-group-catalog/{group['id']}", json={"name": "Đổi tên thôi"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["useful_life_years"] == 8


# ---------- Bước 3: Khai báo tỉ lệ khấu hao theo nhóm ----------


def test_declare_depreciation_rate_he_thong_luu():
    group = _create_group(code="NHOM-RATE", name="Nhóm khai báo tỉ lệ", regulation="TT45")
    resp = client.post(
        f"/asset-group-catalog/{group['id']}/depreciation-rates",
        json={
            "depreciation_rate_percent": 10.0,
            "useful_life_years": 10,
            "effective_from": "2026-01-01",
            "declared_by": "quantri1",
        },
    )
    assert resp.status_code == 201, resp.text
    rate = resp.json()
    assert rate["asset_group_id"] == group["id"]
    assert rate["depreciation_rate_percent"] == 10.0
    assert rate["declared_by"] == "quantri1"


def test_declare_depreciation_rate_404_khi_nhom_khong_ton_tai():
    resp = client.post(
        "/asset-group-catalog/999999/depreciation-rates",
        json={"depreciation_rate_percent": 5.0},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "ASSET_GROUP_NOT_FOUND"


def test_declare_depreciation_rate_422_khi_ty_le_vuot_100():
    group = _create_group(code="NHOM-RATE-BAD", name="Nhóm tỉ lệ sai", regulation="TT45")
    resp = client.post(
        f"/asset-group-catalog/{group['id']}/depreciation-rates",
        json={"depreciation_rate_percent": 150.0},
    )
    assert resp.status_code == 422


def test_list_depreciation_rates_append_only_moi_nhat_truoc():
    group = _create_group(code="NHOM-RATE-LIST", name="Nhóm nhiều lượt khai báo", regulation="TT45")
    client.post(
        f"/asset-group-catalog/{group['id']}/depreciation-rates",
        json={"depreciation_rate_percent": 10.0, "effective_from": "2025-01-01"},
    )
    client.post(
        f"/asset-group-catalog/{group['id']}/depreciation-rates",
        json={"depreciation_rate_percent": 12.0, "effective_from": "2026-01-01"},
    )

    resp = client.get(f"/asset-group-catalog/{group['id']}/depreciation-rates")
    assert resp.status_code == 200, resp.text
    rates = resp.json()
    assert len(rates) == 2
    # mới nhất (khai báo sau) đứng đầu
    assert rates[0]["depreciation_rate_percent"] == 12.0
    assert rates[1]["depreciation_rate_percent"] == 10.0


def test_get_current_depreciation_rate_tra_ve_luot_moi_nhat():
    group = _create_group(code="NHOM-RATE-CUR", name="Nhóm lấy tỉ lệ hiện hành", regulation="TT45")
    client.post(
        f"/asset-group-catalog/{group['id']}/depreciation-rates",
        json={"depreciation_rate_percent": 8.0},
    )
    client.post(
        f"/asset-group-catalog/{group['id']}/depreciation-rates",
        json={"depreciation_rate_percent": 9.5},
    )

    resp = client.get(f"/asset-group-catalog/{group['id']}/depreciation-rates/current")
    assert resp.status_code == 200, resp.text
    assert resp.json()["depreciation_rate_percent"] == 9.5


def test_get_current_depreciation_rate_null_khi_chua_khai_bao():
    group = _create_group(
        code="NHOM-RATE-NONE", name="Nhóm chưa khai báo tỉ lệ", regulation="TT45"
    )
    resp = client.get(f"/asset-group-catalog/{group['id']}/depreciation-rates/current")
    assert resp.status_code == 200, resp.text
    assert resp.json() is None


def test_list_depreciation_rates_404_khi_nhom_khong_ton_tai():
    resp = client.get("/asset-group-catalog/999999/depreciation-rates")
    assert resp.status_code == 404
"""Integration test UC-042: Đăng ký siêu dữ liệu tập dữ liệu, qua HTTP

API (SQLite in-memory). Actor "Quản trị Dữ liệu". Luồng:
1. Đăng ký siêu dữ liệu tập dữ liệu (chủ sở hữu, mô tả, mức nhạy cảm).
   Hệ thống lưu vào metadata.dataset_catalog.
2. Cập nhật siêu dữ liệu. Hệ thống lưu phiên bản mới.
3. Tra cứu siêu dữ liệu tập dữ liệu. Hệ thống hiển thị.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _register(dataset_id=101, owner="Sở Tài chính", **kwargs) -> dict:
    payload = {"dataset_id": dataset_id, "owner": owner, **kwargs}
    resp = client.post("/dataset-metadata", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Bước 1: Đăng ký siêu dữ liệu tập dữ liệu ----------


def test_register_dataset_metadata_thanh_cong():
    data = _register(
        dataset_id=1001,
        owner="Phòng Ngân sách",
        description="Tập dữ liệu chi ngân sách cấp huyện",
        sensitivity_level="CONFIDENTIAL",
    )
    assert data["dataset_id"] == 1001
    assert data["owner"] == "Phòng Ngân sách"
    assert data["description"] == "Tập dữ liệu chi ngân sách cấp huyện"
    assert data["sensitivity_level"] == "CONFIDENTIAL"
    assert data["version"] == 1


def test_register_dataset_metadata_mac_dinh_sensitivity_internal():
    data = _register(dataset_id=1002, owner="Phòng Tài sản")
    assert data["sensitivity_level"] == "INTERNAL"
    assert data["description"] is None


def test_register_dataset_metadata_409_khi_da_dang_ky():
    _register(dataset_id=1003, owner="Phòng A")
    resp = client.post("/dataset-metadata", json={"dataset_id": 1003, "owner": "Phòng B"})
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "DATASET_METADATA_ALREADY_EXISTS"


def test_register_dataset_metadata_422_khi_thieu_owner():
    resp = client.post("/dataset-metadata", json={"dataset_id": 1004, "owner": "   "})
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_DATASET_METADATA"


def test_register_dataset_metadata_422_khi_sensitivity_khong_hop_le():
    resp = client.post(
        "/dataset-metadata",
        json={"dataset_id": 1005, "owner": "Phòng A", "sensitivity_level": "TUYET_MAT"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_DATASET_METADATA"


# ---------- Bước 2: Cập nhật siêu dữ liệu ----------


def test_update_dataset_metadata_tang_version_va_luu_lich_su():
    _register(dataset_id=2001, owner="Phòng A", description="Mô tả cũ", sensitivity_level="PUBLIC")
    resp = client.put(
        "/dataset-metadata/2001",
        json={"owner": "Phòng B", "sensitivity_level": "SECRET", "note": "Đổi chủ sở hữu"},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["version"] == 2
    assert updated["owner"] == "Phòng B"
    assert updated["sensitivity_level"] == "SECRET"
    assert updated["description"] == "Mô tả cũ"  # giữ nguyên vì không truyền

    versions = client.get("/dataset-metadata/2001/versions").json()
    assert len(versions) == 2
    assert versions[0]["version"] == 2
    assert versions[0]["change_note"] == "Đổi chủ sở hữu"
    assert versions[1]["version"] == 1


def test_update_dataset_metadata_xoa_description_khi_clear_description():
    _register(dataset_id=2002, owner="Phòng A", description="Có mô tả")
    resp = client.put("/dataset-metadata/2002", json={"clear_description": True})
    assert resp.status_code == 200, resp.text
    assert resp.json()["description"] is None
    assert resp.json()["version"] == 2


def test_update_dataset_metadata_404_khi_chua_dang_ky():
    resp = client.put("/dataset-metadata/999999", json={"owner": "Phòng A"})
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "DATASET_METADATA_NOT_FOUND"


def test_update_dataset_metadata_422_khi_owner_rong():
    _register(dataset_id=2003, owner="Phòng A")
    resp = client.put("/dataset-metadata/2003", json={"owner": "   "})
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_DATASET_METADATA"


def test_update_dataset_metadata_422_khi_sensitivity_khong_hop_le():
    _register(dataset_id=2004, owner="Phòng A")
    resp = client.put("/dataset-metadata/2004", json={"sensitivity_level": "KHONG_HOP_LE"})
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["code"] == "INVALID_DATASET_METADATA"


# ---------- Bước 3: Tra cứu siêu dữ liệu tập dữ liệu ----------


def test_get_dataset_metadata_hien_thi_dung():
    _register(dataset_id=3001, owner="Phòng A", description="Mô tả X")
    resp = client.get("/dataset-metadata/3001")
    assert resp.status_code == 200, resp.text
    assert resp.json()["owner"] == "Phòng A"


def test_get_dataset_metadata_404_khi_chua_dang_ky():
    resp = client.get("/dataset-metadata/888888")
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "DATASET_METADATA_NOT_FOUND"


def test_list_dataset_metadata_loc_theo_sensitivity_level():
    _register(dataset_id=3002, owner="Phòng A", sensitivity_level="SECRET")
    _register(dataset_id=3003, owner="Phòng B", sensitivity_level="PUBLIC")

    resp = client.get("/dataset-metadata", params={"sensitivity_level": "SECRET"})
    assert resp.status_code == 200, resp.text
    dataset_ids = [m["dataset_id"] for m in resp.json()]
    assert 3002 in dataset_ids
    assert 3003 not in dataset_ids


def test_list_dataset_metadata_loc_theo_owner():
    _register(dataset_id=3004, owner="Phòng Ngân sách riêng")
    resp = client.get("/dataset-metadata", params={"owner": "Phòng Ngân sách riêng"})
    assert resp.status_code == 200, resp.text
    dataset_ids = [m["dataset_id"] for m in resp.json()]
    assert dataset_ids == [3004]


def test_list_dataset_metadata_versions_404_khi_chua_dang_ky():
    resp = client.get("/dataset-metadata/777777/versions")
    assert resp.status_code == 404, resp.text
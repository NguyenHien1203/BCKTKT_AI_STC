"""Integration test UC-054 (Tra cứu dữ liệu tài sản) qua HTTP API.

Dùng SQLite in-memory (bảng `dm_tai_san` được tạo tự động qua
`Base.metadata.create_all` — xem `app/main.py`), mô phỏng bảng
`curated.dm_tai_san` trên Postgres thật (bảng do Alembic
`0007_uc054_create_dm_tai_san.py` tạo ở schema "curated").
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _seed_tai_san(
    ma_tai_san: str,
    ten_tai_san: str = "Trụ sở UBND xã",
    don_vi_code: str = "DV001",
    don_vi_ten: str = "Sở Tài chính tỉnh Hưng Yên",
    nhom_tai_san_code: str = "NHOM_NHA_DAT",
    nhom_tai_san_ten: str = "Nhà, đất",
    trang_thai: str = "DANG_SU_DUNG",
    **overrides,
):
    payload = {
        "ma_tai_san": ma_tai_san,
        "ten_tai_san": ten_tai_san,
        "don_vi_code": don_vi_code,
        "don_vi_ten": don_vi_ten,
        "nhom_tai_san_code": nhom_tai_san_code,
        "nhom_tai_san_ten": nhom_tai_san_ten,
        "trang_thai": trang_thai,
        "nguyen_gia": 1_000_000_000,
        "gia_tri_con_lai": 800_000_000,
        "ngay_dua_vao_su_dung": "2020-01-01",
        "nam_tai_chinh": 2026,
        "ghi_chu": "",
    }
    payload.update(overrides)
    resp = client.post("/tai-san/seed", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- Bước 1-3: Nhập bộ lọc -> truy vấn curated.dm_tai_san -> hiển thị danh sách ----------


def test_search_without_filter_returns_all():
    _seed_tai_san("TS-UC54-001")
    _seed_tai_san("TS-UC54-002", don_vi_code="DV002")

    resp = client.get("/tai-san")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] >= 2
    codes = {item["ma_tai_san"] for item in data["items"]}
    assert "TS-UC54-001" in codes
    assert "TS-UC54-002" in codes


def test_search_filter_by_don_vi():
    _seed_tai_san("TS-UC54-010", don_vi_code="DV-FILTER-A")
    _seed_tai_san("TS-UC54-011", don_vi_code="DV-FILTER-B")

    resp = client.get("/tai-san", params={"don_vi_code": "DV-FILTER-A"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["ma_tai_san"] == "TS-UC54-010"


def test_search_filter_by_nhom_tai_san():
    _seed_tai_san("TS-UC54-020", nhom_tai_san_code="NHOM_XE")
    _seed_tai_san("TS-UC54-021", nhom_tai_san_code="NHOM_MAY_MOC")

    resp = client.get("/tai-san", params={"nhom_tai_san_code": "NHOM_XE"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["ma_tai_san"] == "TS-UC54-020"


def test_search_filter_by_trang_thai():
    _seed_tai_san("TS-UC54-030", trang_thai="DA_THANH_LY")
    _seed_tai_san("TS-UC54-031", trang_thai="DANG_SU_DUNG")

    resp = client.get("/tai-san", params={"trang_thai": "DA_THANH_LY"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert all(item["trang_thai"] == "DA_THANH_LY" for item in data["items"])
    codes = {item["ma_tai_san"] for item in data["items"]}
    assert "TS-UC54-030" in codes
    assert "TS-UC54-031" not in codes


def test_search_combine_filters_and_pagination():
    for i in range(3):
        _seed_tai_san(
            f"TS-UC54-COMBO-{i}",
            don_vi_code="DV-COMBO",
            nhom_tai_san_code="NHOM_COMBO",
            trang_thai="DANG_SU_DUNG",
        )

    resp = client.get(
        "/tai-san",
        params={
            "don_vi_code": "DV-COMBO",
            "nhom_tai_san_code": "NHOM_COMBO",
            "trang_thai": "DANG_SU_DUNG",
            "page": 1,
            "page_size": 2,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2


def test_search_invalid_trang_thai_returns_422():
    resp = client.get("/tai-san", params={"trang_thai": "KHONG_HOP_LE"})
    assert resp.status_code == 422


def test_search_invalid_page_size_returns_422():
    resp = client.get("/tai-san", params={"page_size": 0})
    assert resp.status_code == 422


# ---------- Bước 4: Xem chi tiết tài sản ----------


def test_get_detail_returns_full_record():
    created = _seed_tai_san("TS-UC54-040", ten_tai_san="Ô tô công vụ 16 chỗ")

    resp = client.get(f"/tai-san/{created['id']}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ma_tai_san"] == "TS-UC54-040"
    assert data["ten_tai_san"] == "Ô tô công vụ 16 chỗ"
    assert data["nguyen_gia"] == 1_000_000_000
    assert data["gia_tri_con_lai"] == 800_000_000


def test_get_detail_not_found_returns_404():
    resp = client.get("/tai-san/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "TAI_SAN_NOT_FOUND"


# ---------- [Hạ tầng hỗ trợ] seed ----------


def test_seed_upsert_updates_existing_record_by_ma_tai_san():
    first = _seed_tai_san("TS-UC54-050", trang_thai="DANG_SU_DUNG")
    second = _seed_tai_san("TS-UC54-050", trang_thai="DA_THANH_LY")

    assert first["id"] == second["id"]
    assert second["trang_thai"] == "DA_THANH_LY"


def test_seed_invalid_trang_thai_returns_422():
    resp = client.post(
        "/tai-san/seed",
        json={
            "ma_tai_san": "TS-UC54-INVALID",
            "ten_tai_san": "Tài sản test",
            "don_vi_code": "DV001",
            "don_vi_ten": "Sở Tài chính",
            "nhom_tai_san_code": "NHOM_X",
            "nhom_tai_san_ten": "Nhóm X",
            "trang_thai": "KHONG_HOP_LE",
        },
    )
    assert resp.status_code == 422
"""Integration test UC-056 (Tra cứu dữ liệu ngân sách) qua HTTP API.

Dùng SQLite in-memory (bảng `dm_ngan_sach` — schema `curated` chỉ áp
dụng khi chạy trên Postgres, xem `app/infrastructure/db/models.py`).
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _index(don_vi_code, don_vi_ten, khoan_muc_code, khoan_muc_ten, ky, **kwargs):
    payload = {
        "don_vi_code": don_vi_code,
        "don_vi_ten": don_vi_ten,
        "khoan_muc_code": khoan_muc_code,
        "khoan_muc_ten": khoan_muc_ten,
        "ky": ky,
        **kwargs,
    }
    resp = client.post("/ngan-sach/index", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _seed_basic_dataset():
    _index(
        "SO_TC", "Sở Tài chính", "KM_SNKT", "Sự nghiệp kinh tế", "2024",
        thu=1000, chi=800, tam_ung=100, don_vi_tinh="triệu đồng",
    )
    _index(
        "SO_TC", "Sở Tài chính", "KM_SNKT", "Sự nghiệp kinh tế", "2025",
        thu=1200, chi=900, tam_ung=120, don_vi_tinh="triệu đồng",
    )
    _index(
        "SO_TC", "Sở Tài chính", "KM_SNGD", "Sự nghiệp giáo dục", "2025",
        thu=2000, chi=1800, tam_ung=50, don_vi_tinh="triệu đồng",
    )
    _index(
        "P_TC_HUYEN", "Phòng Tài chính - Kế hoạch huyện", "KM_SNKT", "Sự nghiệp kinh tế", "2025",
        thu=500, chi=400, tam_ung=20, don_vi_tinh="triệu đồng",
    )


# ---------- Bước 1-3: Nhập bộ lọc -> truy vấn curated.dm_ngan_sach -> hiển thị số liệu ----------


def test_index_ngan_sach_success():
    record = _index("DV_TEST", "Đơn vị test", "KM_TEST", "Khoản mục test", "2026", thu=100, chi=80)
    assert record["don_vi_code"] == "DV_TEST"
    assert record["ky"] == "2026"
    assert record["thu"] == 100
    assert record["chi"] == 80
    assert record["tam_ung"] == 0


def test_index_invalid_ky_returns_422():
    resp = client.post(
        "/ngan-sach/index",
        json={
            "don_vi_code": "SO_TC",
            "don_vi_ten": "Sở Tài chính",
            "khoan_muc_code": "KM_SNKT",
            "khoan_muc_ten": "Sự nghiệp kinh tế",
            "ky": "24",
            "thu": 100,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_NGAN_SACH_RECORD"


def test_index_negative_thu_returns_422():
    resp = client.post(
        "/ngan-sach/index",
        json={
            "don_vi_code": "SO_TC",
            "don_vi_ten": "Sở Tài chính",
            "khoan_muc_code": "KM_SNKT",
            "khoan_muc_ten": "Sự nghiệp kinh tế",
            "ky": "2024",
            "thu": -1,
        },
    )
    # Pydantic (ge=0) chặn trước khi tới domain validate.
    assert resp.status_code == 422


def test_search_no_filter_returns_all():
    _seed_basic_dataset()
    resp = client.get("/ngan-sach")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 4
    assert data["page"] == 1


def test_search_filter_by_don_vi():
    resp = client.get("/ngan-sach", params={"don_vi": "Sở Tài chính"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3
    assert all(item["don_vi_code"] == "SO_TC" for item in data["items"])


def test_search_filter_by_don_vi_code_exact():
    resp = client.get("/ngan-sach", params={"don_vi": "P_TC_HUYEN"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["don_vi_code"] == "P_TC_HUYEN"


def test_search_filter_by_khoan_muc():
    resp = client.get("/ngan-sach", params={"khoan_muc": "giáo dục"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert all(item["khoan_muc_code"] == "KM_SNGD" for item in data["items"])


def test_search_filter_by_ky_range():
    resp = client.get("/ngan-sach", params={"ky_from": "2025", "ky_to": "2025"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["ky"] == "2025" for item in data["items"])
    assert data["total"] >= 3


def test_search_combined_filters():
    resp = client.get(
        "/ngan-sach",
        params={"don_vi": "SO_TC", "khoan_muc": "KM_SNKT", "ky_from": "2024", "ky_to": "2024"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["don_vi_code"] == "SO_TC"
    assert data["items"][0]["ky"] == "2024"


def test_search_invalid_ky_range_returns_422():
    resp = client.get("/ngan-sach", params={"ky_from": "2026", "ky_to": "2020"})
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_NGAN_SACH_SEARCH_QUERY"


def test_search_invalid_ky_format_returns_422():
    resp = client.get("/ngan-sach", params={"ky_from": "24"})
    assert resp.status_code == 422


def test_search_pagination():
    resp = client.get("/ngan-sach", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


# ---------- Bước 4-5: Xem chi tiết theo đơn vị/khoản mục -> Hệ thống re-query ----------


def test_detail_returns_all_periods_and_totals():
    resp = client.get(
        "/ngan-sach/detail", params={"don_vi_code": "SO_TC", "khoan_muc_code": "KM_SNKT"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["don_vi_code"] == "SO_TC"
    assert data["khoan_muc_code"] == "KM_SNKT"
    kys = [item["ky"] for item in data["items"]]
    assert kys == sorted(kys)  # sắp xếp theo kỳ tăng dần
    assert data["tong_thu"] == 1000 + 1200
    assert data["tong_chi"] == 800 + 900
    assert data["tong_tam_ung"] == 100 + 120


def test_detail_no_data_returns_empty_items_zero_totals():
    resp = client.get(
        "/ngan-sach/detail", params={"don_vi_code": "KHONG_TON_TAI", "khoan_muc_code": "KM_SNKT"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["tong_thu"] == 0
    assert data["tong_chi"] == 0
    assert data["tong_tam_ung"] == 0


def test_detail_missing_required_param_returns_422():
    resp = client.get("/ngan-sach/detail", params={"don_vi_code": "SO_TC"})
    assert resp.status_code == 422
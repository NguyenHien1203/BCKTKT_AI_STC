"""Integration test UC-055 (Tra cứu dữ liệu giá) qua HTTP API.

Dùng SQLite in-memory (bảng `dm_gia` — schema `curated` chỉ áp dụng khi
chạy trên Postgres, xem `app/infrastructure/db/models.py`).
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _index(mat_hang_code, mat_hang_name, dia_ban_code, dia_ban_name, ky, gia, **kwargs):
    payload = {
        "mat_hang_code": mat_hang_code,
        "mat_hang_name": mat_hang_name,
        "dia_ban_code": dia_ban_code,
        "dia_ban_name": dia_ban_name,
        "ky": ky,
        "gia": gia,
        **kwargs,
    }
    resp = client.post("/price-data/index", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _seed_basic_dataset():
    _index("GAO-ST25", "Gạo ST25", "HN", "TP. Hà Nội", "2026-05", 24500, don_vi_tinh="đồng/kg")
    _index("GAO-ST25", "Gạo ST25", "HN", "TP. Hà Nội", "2026-06", 24800, don_vi_tinh="đồng/kg")
    _index("GAO-ST25", "Gạo ST25", "HN", "TP. Hà Nội", "2026-07", 25200, don_vi_tinh="đồng/kg")
    _index("GAO-ST25", "Gạo ST25", "HCM", "TP. Hồ Chí Minh", "2026-07", 24900, don_vi_tinh="đồng/kg")
    _index("XANG-A95", "Xăng RON95", "HN", "TP. Hà Nội", "2026-07", 22000, don_vi_tinh="đồng/lít")


# ---------- Bước 1-2: Nhập bộ lọc -> truy vấn curated.dm_gia -> bảng ----------


def test_index_price_record_success():
    record = _index("GAO-TEST", "Gạo mẫu", "HN", "TP. Hà Nội", "2026-07", 25200)
    assert record["mat_hang_code"] == "GAO-TEST"
    assert record["ky"] == "2026-07"
    assert record["gia"] == 25200


def test_index_invalid_ky_returns_422():
    resp = client.post(
        "/price-data/index",
        json={
            "mat_hang_code": "GAO-ST25",
            "mat_hang_name": "Gạo ST25",
            "dia_ban_code": "HN",
            "dia_ban_name": "TP. Hà Nội",
            "ky": "07-2026",
            "gia": 25000,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_PRICE_RECORD"


def test_index_negative_gia_returns_422():
    resp = client.post(
        "/price-data/index",
        json={
            "mat_hang_code": "GAO-ST25",
            "mat_hang_name": "Gạo ST25",
            "dia_ban_code": "HN",
            "dia_ban_name": "TP. Hà Nội",
            "ky": "2026-07",
            "gia": -1,
        },
    )
    # Pydantic (ge=0) chặn trước khi tới domain validate.
    assert resp.status_code == 422


def test_search_no_filter_returns_all():
    _seed_basic_dataset()
    resp = client.get("/price-data")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 5
    assert data["page"] == 1


def test_search_filter_by_mat_hang():
    resp = client.get("/price-data", params={"mat_hang": "gạo"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 4
    assert all("GAO" in item["mat_hang_code"] for item in data["items"])


def test_search_filter_by_mat_hang_code_exact():
    resp = client.get("/price-data", params={"mat_hang": "XANG-A95"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["mat_hang_code"] == "XANG-A95"


def test_search_filter_by_dia_ban():
    resp = client.get("/price-data", params={"dia_ban": "Hồ Chí Minh"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert all(item["dia_ban_code"] == "HCM" for item in data["items"])


def test_search_filter_by_ky_range():
    resp = client.get("/price-data", params={"ky_from": "2026-06", "ky_to": "2026-06"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["ky"] == "2026-06" for item in data["items"])
    assert data["total"] >= 1


def test_search_combined_filters():
    resp = client.get(
        "/price-data",
        params={"mat_hang": "GAO-ST25", "dia_ban": "HN", "ky_from": "2026-07", "ky_to": "2026-07"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["dia_ban_code"] == "HN"
    assert data["items"][0]["ky"] == "2026-07"


def test_search_invalid_ky_range_returns_422():
    resp = client.get("/price-data", params={"ky_from": "2026-08", "ky_to": "2026-01"})
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_PRICE_SEARCH_QUERY"


def test_search_invalid_ky_format_returns_422():
    resp = client.get("/price-data", params={"ky_from": "2026/08"})
    assert resp.status_code == 422


def test_search_pagination():
    resp = client.get("/price-data", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


# ---------- Bước 3-4: Biểu đồ xu hướng giá theo thời gian (line chart) ----------


def test_trend_groups_by_ky_and_averages():
    resp = client.get("/price-data/trend", params={"mat_hang": "GAO-ST25", "dia_ban": "HN"})
    assert resp.status_code == 200
    data = resp.json()
    kys = [p["ky"] for p in data["points"]]
    assert kys == sorted(kys)  # sắp xếp theo kỳ tăng dần
    point_07 = next(p for p in data["points"] if p["ky"] == "2026-07")
    assert point_07["gia_trung_binh"] == 25200
    assert point_07["so_ban_ghi"] == 1


def test_trend_all_dia_ban_averages_multiple_records():
    resp = client.get("/price-data/trend", params={"mat_hang": "GAO-ST25", "ky_from": "2026-07", "ky_to": "2026-07"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["points"]) == 1
    point = data["points"][0]
    assert point["so_ban_ghi"] == 2  # HN + HCM cùng kỳ 2026-07
    assert point["gia_trung_binh"] == round((25200 + 24900) / 2, 2)


def test_trend_invalid_ky_range_returns_422():
    resp = client.get("/price-data/trend", params={"ky_from": "2026-08", "ky_to": "2026-01"})
    assert resp.status_code == 422


def test_trend_no_data_returns_empty_points():
    resp = client.get("/price-data/trend", params={"mat_hang": "KHONG-TON-TAI"})
    assert resp.status_code == 200
    assert resp.json()["points"] == []
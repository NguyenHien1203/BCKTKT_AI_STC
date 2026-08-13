"""Integration test UC-057 (Hiển thị độ mới dữ liệu) qua HTTP API.

Dùng SQLite in-memory (bảng `data_freshness` — schema `curated` chỉ áp
dụng khi chạy trên Postgres, xem `app/infrastructure/db/models.py`).
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from datetime import datetime, timedelta, timezone  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _iso(dt):
    return dt.isoformat()


def _index(nguon_code, nguon_ten, last_sync=None, **kwargs):
    payload = {
        "nguon_code": nguon_code,
        "nguon_ten": nguon_ten,
        **({"last_sync": last_sync} if last_sync is not None else {}),
        **kwargs,
    }
    resp = client.post("/data-freshness/index", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _seed_basic_dataset():
    now = datetime.now(timezone.utc)
    _index(
        "TABMIS", "Hệ thống TABMIS (Ngân sách)",
        last_sync=_iso(now - timedelta(hours=1)),
        expected_record_count=1000, actual_record_count=1000,
    )
    _index(
        "QL_GIA", "Hệ thống Quản lý Giá",
        last_sync=_iso(now - timedelta(hours=6)),
        expected_record_count=500, actual_record_count=250,
    )
    _index(
        "QL_TAI_SAN", "Hệ thống Quản lý Tài sản công",
        last_sync=_iso(now - timedelta(hours=48)),
        expected_record_count=300, actual_record_count=300,
    )


# ---------- Bước 1-2: Xem ô thông tin độ mới dữ liệu trên Bảng điều khiển ----------
# (test rỗng đặt NGAY ĐẦU file, chạy trước mọi test khác trong module vì
# pytest chạy theo thứ tự khai báo và DB SQLite in-memory dùng chung 1
# TestClient cho toàn bộ file)


def test_summary_empty_when_no_data():
    resp = client.get("/data-freshness/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sources"] == 0
    assert data["stale_sources"] == 0
    assert data["average_completeness_percent"] == 0.0
    assert data["latest_last_sync"] is None


# ---------- Nạp dữ liệu (hạ tầng hỗ trợ) ----------


def test_index_new_source_creates_record():
    data = _index(
        "NGUON_A", "Nguồn A", expected_record_count=100, actual_record_count=100,
    )
    assert data["nguon_code"] == "NGUON_A"
    assert data["completeness_percent"] == 100.0
    assert data["is_stale"] is False


def test_index_upsert_updates_existing_record_not_duplicate():
    now = datetime.now(timezone.utc)
    _index("NGUON_B", "Nguồn B", last_sync=_iso(now), expected_record_count=100, actual_record_count=50)
    _index("NGUON_B", "Nguồn B", last_sync=_iso(now), expected_record_count=100, actual_record_count=100)

    resp = client.get("/data-freshness")
    assert resp.status_code == 200
    items = [i for i in resp.json() if i["nguon_code"] == "NGUON_B"]
    assert len(items) == 1
    assert items[0]["actual_record_count"] == 100
    assert items[0]["completeness_percent"] == 100.0


def test_index_invalid_negative_count_returns_422():
    resp = client.post(
        "/data-freshness/index",
        json={"nguon_code": "X", "nguon_ten": "X", "expected_record_count": -1},
    )
    assert resp.status_code == 422


def test_index_missing_nguon_ten_returns_422_pydantic():
    resp = client.post("/data-freshness/index", json={"nguon_code": "X"})
    assert resp.status_code == 422


# ---------- Bước 1-2: Xem ô thông tin độ mới dữ liệu trên Bảng điều khiển ----------


def test_summary_reflects_all_sources():
    _seed_basic_dataset()
    resp = client.get("/data-freshness/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sources"] >= 3
    # QL_TAI_SAN đồng bộ cách đây 48h > ngưỡng 24h -> chậm trễ
    assert data["stale_sources"] >= 1
    assert data["latest_last_sync"] is not None


# ---------- Bước 3-4: Xem chi tiết last_sync + độ đầy đủ theo nguồn ----------


def test_list_detail_returns_table_sorted_by_ten_nguon():
    _seed_basic_dataset()
    resp = client.get("/data-freshness")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 3
    names = [i["nguon_ten"] for i in items]
    assert names == sorted(names)


def test_list_detail_computes_completeness_percent():
    _seed_basic_dataset()
    resp = client.get("/data-freshness")
    items = {i["nguon_code"]: i for i in resp.json()}
    assert items["TABMIS"]["completeness_percent"] == 100.0
    assert items["QL_GIA"]["completeness_percent"] == 50.0


def test_list_detail_flags_stale_source():
    _seed_basic_dataset()
    resp = client.get("/data-freshness")
    items = {i["nguon_code"]: i for i in resp.json()}
    assert items["QL_TAI_SAN"]["is_stale"] is True
    assert items["TABMIS"]["is_stale"] is False


def test_get_detail_for_one_source():
    _seed_basic_dataset()
    resp = client.get("/data-freshness/QL_GIA")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nguon_code"] == "QL_GIA"
    assert data["completeness_percent"] == 50.0


def test_get_detail_for_unknown_source_returns_404():
    resp = client.get("/data-freshness/KHONG_TON_TAI")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATA_FRESHNESS_NOT_FOUND"


def test_completeness_100_when_no_expected_but_has_actual():
    _index("NGUON_C", "Nguồn C", expected_record_count=0, actual_record_count=10)
    resp = client.get("/data-freshness/NGUON_C")
    assert resp.json()["completeness_percent"] == 100.0


def test_completeness_0_when_no_expected_and_no_actual():
    _index("NGUON_D", "Nguồn D", expected_record_count=0, actual_record_count=0)
    resp = client.get("/data-freshness/NGUON_D")
    assert resp.json()["completeness_percent"] == 0.0
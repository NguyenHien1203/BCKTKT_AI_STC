"""Integration test UC-047 qua HTTP API, dùng SQLite in-memory (không cần Postgres).

Khi có Postgres thật, set biến môi trường DATABASE_URL trước khi chạy để
test tích hợp đầy đủ với hạ tầng thật.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _register_dashboard(code="DB-TEST-01", category="NGAN_SACH"):
    resp = client.post(
        "/dashboards",
        json={
            "code": code,
            "name": "Tổng hợp Ngân sách tỉnh",
            "description": "Bảng điều khiển demo",
            "category": category,
            "superset_dashboard_uid": "demo-uid",
            "embed_url": "http://localhost:8088/superset/dashboard/demo-uid/?standalone=1",
        },
    )
    return resp


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_get_dashboard():
    resp = _register_dashboard(code="DB-TEST-REG-01")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["code"] == "DB-TEST-REG-01"
    assert body["category"] == "NGAN_SACH"
    assert body["is_active"] is True

    resp2 = client.get(f"/dashboards/{body['id']}")
    assert resp2.status_code == 200
    assert resp2.json()["superset_dashboard_uid"] == "demo-uid"


def test_register_invalid_category_returns_422():
    resp = client.post(
        "/dashboards",
        json={
            "code": "DB-TEST-INVALID-CAT",
            "name": "X",
            "description": "",
            "category": "KHONG_HOP_LE",
            "superset_dashboard_uid": "uid",
            "embed_url": "http://x",
        },
    )
    assert resp.status_code == 422


def test_register_duplicate_code_returns_409():
    _register_dashboard(code="DB-TEST-DUP-01")
    resp = _register_dashboard(code="DB-TEST-DUP-01")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "DASHBOARD_CODE_EXISTS"


def test_get_dashboard_not_found_returns_404():
    resp = client.get("/dashboards/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DASHBOARD_NOT_FOUND"


def test_list_catalog_chon_bang_dieu_khien_tu_danh_muc():
    """Bước 1 luồng UC-047: chọn Bảng điều khiển từ danh mục -> hệ thống hiển thị danh sách."""
    _register_dashboard(code="DB-TEST-LIST-01", category="TAI_SAN_CONG")
    _register_dashboard(code="DB-TEST-LIST-02", category="GIA")

    resp = client.get("/dashboards")
    assert resp.status_code == 200
    codes = [d["code"] for d in resp.json()]
    assert "DB-TEST-LIST-01" in codes
    assert "DB-TEST-LIST-02" in codes

    resp_filtered = client.get("/dashboards", params={"category": "GIA"})
    assert resp_filtered.status_code == 200
    assert all(d["category"] == "GIA" for d in resp_filtered.json())


def test_list_catalog_only_active_by_default_hides_deactivated():
    reg = _register_dashboard(code="DB-TEST-DEACT-01")
    dashboard_id = reg.json()["id"]
    client.post(f"/dashboards/{dashboard_id}/deactivate")

    resp = client.get("/dashboards")
    codes = [d["code"] for d in resp.json()]
    assert "DB-TEST-DEACT-01" not in codes

    resp_all = client.get("/dashboards", params={"only_active": False})
    codes_all = [d["code"] for d in resp_all.json()]
    assert "DB-TEST-DEACT-01" in codes_all


def test_pin_and_unpin_favorite_dashboard():
    """Bước 3 luồng UC-047: ghim bảng điều khiển yêu thích -> lưu vào tùy chọn cá nhân."""
    reg = _register_dashboard(code="DB-TEST-PIN-01")
    dashboard_id = reg.json()["id"]

    resp = client.post(f"/dashboards/{dashboard_id}/favorite", json={"user_id": 42})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user_id"] == 42
    assert body["dashboard_id"] == dashboard_id

    resp_list = client.get("/dashboards/favorites", params={"user_id": 42})
    assert resp_list.status_code == 200
    ids = [d["id"] for d in resp_list.json()]
    assert dashboard_id in ids

    resp_unpin = client.delete(f"/dashboards/{dashboard_id}/favorite", params={"user_id": 42})
    assert resp_unpin.status_code == 204

    resp_list2 = client.get("/dashboards/favorites", params={"user_id": 42})
    ids2 = [d["id"] for d in resp_list2.json()]
    assert dashboard_id not in ids2


def test_pin_duplicate_favorite_returns_409():
    reg = _register_dashboard(code="DB-TEST-PIN-DUP-01")
    dashboard_id = reg.json()["id"]

    resp1 = client.post(f"/dashboards/{dashboard_id}/favorite", json={"user_id": 7})
    assert resp1.status_code == 201
    resp2 = client.post(f"/dashboards/{dashboard_id}/favorite", json={"user_id": 7})
    assert resp2.status_code == 409
    assert resp2.json()["detail"]["code"] == "DASHBOARD_ALREADY_PINNED"


def test_pin_nonexistent_dashboard_returns_404():
    resp = client.post("/dashboards/999999/favorite", json={"user_id": 1})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DASHBOARD_NOT_FOUND"


def test_pin_inactive_dashboard_returns_409():
    reg = _register_dashboard(code="DB-TEST-PIN-INACTIVE-01")
    dashboard_id = reg.json()["id"]
    client.post(f"/dashboards/{dashboard_id}/deactivate")

    resp = client.post(f"/dashboards/{dashboard_id}/favorite", json={"user_id": 99})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "DASHBOARD_INACTIVE"


def test_unpin_not_favorited_returns_404():
    reg = _register_dashboard(code="DB-TEST-UNPIN-404-01")
    dashboard_id = reg.json()["id"]

    resp = client.delete(f"/dashboards/{dashboard_id}/favorite", params={"user_id": 5})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DASHBOARD_FAVORITE_NOT_FOUND"


def test_activate_dashboard():
    reg = _register_dashboard(code="DB-TEST-ACTIVATE-01")
    dashboard_id = reg.json()["id"]
    client.post(f"/dashboards/{dashboard_id}/deactivate")

    resp = client.post(f"/dashboards/{dashboard_id}/activate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True
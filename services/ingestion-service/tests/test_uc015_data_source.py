"""Integration test UC-015 qua HTTP API, dùng SQLite in-memory (không cần Postgres).

Khi có Postgres thật, set biến môi trường DATABASE_URL trước khi chạy để
test tích hợp đầy đủ với hạ tầng thật.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_get_data_source():
    resp = client.post(
        "/data-sources",
        json={
            "code": "TABMIS-01",
            "name": "TABMIS Kho bạc tỉnh",
            "source_system": "TABMIS",
            "provider": "Kho bạc Nhà nước",
            "owner": "Phòng NSNN",
            "sensitivity_level": "CONFIDENTIAL",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["code"] == "TABMIS-01"
    assert body["source_system"] == "TABMIS"
    assert body["is_active"] is True

    resp2 = client.get(f"/data-sources/{body['id']}")
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "TABMIS Kho bạc tỉnh"


def test_register_invalid_source_system_returns_422():
    resp = client.post(
        "/data-sources",
        json={
            "code": "INVALID-01",
            "name": "X",
            "source_system": "KHONG_HOP_LE",
            "provider": "P",
            "owner": "O",
        },
    )
    assert resp.status_code == 422


def test_register_duplicate_code_returns_409():
    payload = {
        "code": "DUP-SRC-01",
        "name": "A",
        "source_system": "MISA",
        "provider": "P",
        "owner": "O",
    }
    client.post("/data-sources", json=payload)
    resp = client.post("/data-sources", json={**payload, "name": "B"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_CODE_EXISTS"


def test_get_not_found_returns_404():
    resp = client.get("/data-sources/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_NOT_FOUND"


def test_list_data_sources():
    client.post(
        "/data-sources",
        json={
            "code": "QLG-01",
            "name": "QL Giá",
            "source_system": "QL_GIA",
            "provider": "Sở Tài chính",
            "owner": "Phòng Giá",
        },
    )
    resp = client.get("/data-sources")
    assert resp.status_code == 200
    codes = [s["code"] for s in resp.json()]
    assert "QLG-01" in codes


def test_update_data_source_info():
    create = client.post(
        "/data-sources",
        json={
            "code": "UPD-01",
            "name": "PMSTT nguồn",
            "source_system": "PMSTT",
            "provider": "Cũ",
            "owner": "Chủ cũ",
            "sensitivity_level": "INTERNAL",
        },
    ).json()

    resp = client.patch(
        f"/data-sources/{create['id']}",
        json={
            "provider": "Nhà cung cấp mới",
            "owner": "Chủ sở hữu mới",
            "sensitivity_level": "SECRET",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "Nhà cung cấp mới"
    assert body["owner"] == "Chủ sở hữu mới"
    assert body["sensitivity_level"] == "SECRET"


def test_deactivate_and_reactivate_data_source():
    create = client.post(
        "/data-sources",
        json={
            "code": "DEACT-SRC-01",
            "name": "QLVBĐH nguồn",
            "source_system": "QLVBDH",
            "provider": "P",
            "owner": "O",
        },
    ).json()

    resp = client.post(f"/data-sources/{create['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    listing = client.get("/data-sources", params={"only_active": True}).json()
    codes = [s["code"] for s in listing]
    assert "DEACT-SRC-01" not in codes

    resp2 = client.post(f"/data-sources/{create['id']}/activate")
    assert resp2.status_code == 200
    assert resp2.json()["is_active"] is True

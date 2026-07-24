"""Integration test UC-01 qua HTTP API, dùng SQLite in-memory (không cần Postgres).

Khi có Postgres thật, set biến môi trường DATABASE_URL trước khi chạy để
test tích hợp đầy đủ với hạ tầng thật (xem README.md phần giới hạn môi trường).
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


def test_create_and_get_org_unit():
    resp = client.post(
        "/org-units",
        json={"code": "SO-TC-01", "name": "Sở Tài chính", "unit_type": "SO"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["code"] == "SO-TC-01"

    resp2 = client.get(f"/org-units/{body['id']}")
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Sở Tài chính"


def test_create_duplicate_code_returns_409():
    client.post("/org-units", json={"code": "DUP-01", "name": "A", "unit_type": "SO"})
    resp = client.post("/org-units", json={"code": "DUP-01", "name": "B", "unit_type": "SO"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "ORG_UNIT_CODE_EXISTS"


def test_get_not_found_returns_404():
    resp = client.get("/org-units/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "ORG_UNIT_NOT_FOUND"


def test_rename_org_unit():
    create = client.post(
        "/org-units", json={"code": "REN-01", "name": "Ten cu", "unit_type": "SO"}
    ).json()
    resp = client.patch(f"/org-units/{create['id']}/rename", json={"name": "Ten moi"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Ten moi"


def test_deactivate_and_list_only_active():
    create = client.post(
        "/org-units", json={"code": "DEACT-01", "name": "X", "unit_type": "SO"}
    ).json()
    resp = client.post(f"/org-units/{create['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    listing = client.get("/org-units", params={"only_active": True}).json()
    codes = [u["code"] for u in listing]
    assert "DEACT-01" not in codes


def test_delete_unit_with_children_returns_409():
    parent = client.post(
        "/org-units", json={"code": "PARENT-01", "name": "Cha", "unit_type": "SO"}
    ).json()
    client.post(
        "/org-units",
        json={
            "code": "CHILD-01",
            "name": "Con",
            "unit_type": "PHONG",
            "parent_id": parent["id"],
        },
    )
    resp = client.delete(f"/org-units/{parent['id']}")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "ORG_UNIT_HAS_CHILDREN"

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_org_unit(code="SO-U-01"):
    resp = client.post("/org-units", json={"code": code, "name": "Sở A", "unit_type": "SO"})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_and_get_user():
    org_unit = _create_org_unit("SO-U-01")
    resp = client.post(
        "/users",
        json={
            "username": "nguyenvana",
            "full_name": "Nguyễn Văn A",
            "email": "a@hungyen.gov.vn",
            "org_unit_id": org_unit["id"],
            "role": "STAFF",
            "password": "Passw0rd!123",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["username"] == "nguyenvana"

    resp2 = client.get(f"/users/{body['id']}")
    assert resp2.status_code == 200
    assert resp2.json()["full_name"] == "Nguyễn Văn A"


def test_create_user_with_invalid_org_unit_returns_409():
    resp = client.post(
        "/users",
        json={
            "username": "userx",
            "full_name": "X",
            "email": "x@x.vn",
            "org_unit_id": 999999,
            "role": "STAFF",
            "password": "Passw0rd!123",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "USER_INVALID_ORG_UNIT"


def test_create_duplicate_username_returns_409():
    org_unit = _create_org_unit("SO-U-02")
    payload = {
        "username": "dupuser",
        "full_name": "A",
        "email": "a@x.vn",
        "org_unit_id": org_unit["id"],
        "role": "STAFF",
            "password": "Passw0rd!123",
    }
    client.post("/users", json=payload)
    resp = client.post("/users", json=payload)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "USERNAME_EXISTS"


def test_update_profile():
    org_unit = _create_org_unit("SO-U-03")
    created = client.post(
        "/users",
        json={
            "username": "userupd",
            "full_name": "Ten cu",
            "email": "cu@x.vn",
            "org_unit_id": org_unit["id"],
            "role": "STAFF",
            "password": "Passw0rd!123",
        },
    ).json()
    resp = client.patch(
        f"/users/{created['id']}/profile",
        json={"full_name": "Ten moi", "email": "moi@x.vn"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Ten moi"


def test_deactivate_and_list_only_active():
    org_unit = _create_org_unit("SO-U-04")
    created = client.post(
        "/users",
        json={
            "username": "userdeact",
            "full_name": "X",
            "email": "x@x.vn",
            "org_unit_id": org_unit["id"],
            "role": "STAFF",
            "password": "Passw0rd!123",
        },
    ).json()
    resp = client.post(f"/users/{created['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    listing = client.get("/users", params={"only_active": True}).json()
    usernames = [u["username"] for u in listing]
    assert "userdeact" not in usernames


def test_get_not_found_returns_404():
    resp = client.get("/users/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "USER_NOT_FOUND"


def test_delete_user():
    org_unit = _create_org_unit("SO-U-05")
    created = client.post(
        "/users",
        json={
            "username": "userdel",
            "full_name": "X",
            "email": "x@x.vn",
            "org_unit_id": org_unit["id"],
            "role": "STAFF",
            "password": "Passw0rd!123",
        },
    ).json()
    resp = client.delete(f"/users/{created['id']}")
    assert resp.status_code == 204
    resp2 = client.get(f"/users/{created['id']}")
    assert resp2.status_code == 404

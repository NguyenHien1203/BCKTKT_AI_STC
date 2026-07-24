import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_org_unit(code):
    resp = client.post("/org-units", json={"code": code, "name": f"Đơn vị {code}", "unit_type": "SO"})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_user(username, org_unit_id, password="Passw0rd!123"):
    resp = client.post(
        "/users",
        json={
            "username": username,
            "full_name": "Người dùng test",
            "email": f"{username}@x.vn",
            "org_unit_id": org_unit_id,
            "role": "STAFF",
            "password": password,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_login_happy_path():
    org_unit = _create_org_unit("AUTH-01")
    _create_user("authuser1", org_unit["id"])

    resp = client.post("/auth/login", json={"username": "authuser1", "password": "Passw0rd!123"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "token" in body
    assert body["user"]["username"] == "authuser1"


def test_login_wrong_password_returns_401():
    org_unit = _create_org_unit("AUTH-02")
    _create_user("authuser2", org_unit["id"])

    resp = client.post("/auth/login", json={"username": "authuser2", "password": "sai-mat-khau"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_locked_user_returns_403():
    org_unit = _create_org_unit("AUTH-03")
    user = _create_user("authuser3", org_unit["id"])
    client.post(f"/users/{user['id']}/lock")

    resp = client.post("/auth/login", json={"username": "authuser3", "password": "Passw0rd!123"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "USER_LOCKED"


def test_me_without_token_returns_401():
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_with_valid_token():
    org_unit = _create_org_unit("AUTH-04")
    _create_user("authuser4", org_unit["id"])
    login_resp = client.post(
        "/auth/login", json={"username": "authuser4", "password": "Passw0rd!123"}
    )
    token = login_resp.json()["token"]

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "authuser4"


def test_logout_then_me_returns_401():
    org_unit = _create_org_unit("AUTH-05")
    _create_user("authuser5", org_unit["id"])
    login_resp = client.post(
        "/auth/login", json={"username": "authuser5", "password": "Passw0rd!123"}
    )
    token = login_resp.json()["token"]

    logout_resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 204

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401

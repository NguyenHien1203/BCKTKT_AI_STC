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
            "full_name": "Người dùng UC14",
            "email": f"{username}@x.vn",
            "org_unit_id": org_unit_id,
            "role": "STAFF",
            "password": password,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _login(username, password="Passw0rd!123"):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_list_all_sessions_returns_enriched_view():
    org_unit = _create_org_unit("UC14-01")
    user = _create_user("uc14api1", org_unit["id"])
    _login("uc14api1")

    resp = client.get("/sessions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    matched = [s for s in body if s["user_id"] == user["id"]]
    assert len(matched) == 1
    assert matched[0]["username"] == "uc14api1"
    assert matched[0]["is_revoked"] is False
    assert matched[0]["token_preview"].startswith("...")


def test_list_sessions_filtered_by_user_id():
    org_unit = _create_org_unit("UC14-02")
    user = _create_user("uc14api2", org_unit["id"])
    _login("uc14api2")
    _login("uc14api2")  # đăng nhập thêm 1 phiên nữa (vd từ thiết bị khác)

    resp = client.get(f"/users/{user['id']}/sessions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 2
    assert all(s["user_id"] == user["id"] for s in body)


def test_list_sessions_unknown_user_returns_404():
    resp = client.get("/users/999999/sessions")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "USER_NOT_FOUND"


def test_revoke_session_then_token_becomes_invalid():
    org_unit = _create_org_unit("UC14-03")
    user = _create_user("uc14api3", org_unit["id"])
    login = _login("uc14api3")
    token = login["token"]

    sessions = client.get(f"/users/{user['id']}/sessions").json()
    session_id = sessions[0]["id"]

    resp = client.delete(f"/sessions/{session_id}")
    assert resp.status_code == 204

    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 401


def test_revoke_unknown_session_returns_404():
    resp = client.delete("/sessions/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "SESSION_NOT_FOUND"
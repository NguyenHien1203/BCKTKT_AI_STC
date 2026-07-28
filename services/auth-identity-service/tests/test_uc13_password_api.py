import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.interfaces.api import password_router as password_router_module  # noqa: E402

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


def _login(username, password="Passw0rd!123"):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


# ---------- POST /auth/change-password ----------


def test_change_password_happy_path():
    org_unit = _create_org_unit("PWD-01")
    _create_user("pwduser1", org_unit["id"])
    token = _login("pwduser1")

    resp = client.post(
        "/auth/change-password",
        json={"old_password": "Passw0rd!123", "new_password": "NewPass456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    # Đăng nhập lại bằng mật khẩu mới phải thành công.
    resp2 = client.post("/auth/login", json={"username": "pwduser1", "password": "NewPass456"})
    assert resp2.status_code == 200


def test_change_password_wrong_old_password_returns_401():
    org_unit = _create_org_unit("PWD-02")
    _create_user("pwduser2", org_unit["id"])
    token = _login("pwduser2")

    resp = client.post(
        "/auth/change-password",
        json={"old_password": "sai-mat-khau", "new_password": "NewPass456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "WRONG_OLD_PASSWORD"


def test_change_password_weak_new_password_returns_422():
    org_unit = _create_org_unit("PWD-03")
    _create_user("pwduser3", org_unit["id"])
    token = _login("pwduser3")

    resp = client.post(
        "/auth/change-password",
        json={"old_password": "Passw0rd!123", "new_password": "short1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_change_password_without_token_returns_401():
    resp = client.post(
        "/auth/change-password",
        json={"old_password": "x", "new_password": "NewPass456"},
    )
    assert resp.status_code == 401


def test_change_password_revokes_old_session():
    org_unit = _create_org_unit("PWD-04")
    _create_user("pwduser4", org_unit["id"])
    token = _login("pwduser4")

    client.post(
        "/auth/change-password",
        json={"old_password": "Passw0rd!123", "new_password": "NewPass456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # token cũ phải bị thu hồi sau khi đổi mật khẩu.
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# ---------- POST /auth/forgot-password + /auth/reset-password ----------


def test_forgot_password_then_reset_password_happy_path():
    org_unit = _create_org_unit("PWD-05")
    _create_user("pwduser5", org_unit["id"])

    captured = {}

    def fake_send_reset_link(to_email, reset_link):
        captured["to_email"] = to_email
        captured["reset_link"] = reset_link

    password_router_module._email_sender.send_reset_link = fake_send_reset_link

    resp = client.post("/auth/forgot-password", json={"username": "pwduser5"})
    assert resp.status_code == 200, resp.text
    assert captured["to_email"] == "pwduser5@x.vn"
    token = captured["reset_link"].rsplit("/", 1)[-1]

    resp2 = client.post(
        "/auth/reset-password", json={"token": token, "new_password": "ResetPass789"}
    )
    assert resp2.status_code == 200, resp2.text

    resp3 = client.post("/auth/login", json={"username": "pwduser5", "password": "ResetPass789"})
    assert resp3.status_code == 200


def test_forgot_password_unknown_username_still_returns_200():
    resp = client.post("/auth/forgot-password", json={"username": "khongtontai"})
    assert resp.status_code == 200


def test_reset_password_with_invalid_token_returns_400():
    resp = client.post(
        "/auth/reset-password", json={"token": "token-khong-ton-tai", "new_password": "ResetPass789"}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "PASSWORD_RESET_TOKEN_NOT_FOUND"


def test_reset_password_token_reused_returns_400():
    org_unit = _create_org_unit("PWD-06")
    _create_user("pwduser6", org_unit["id"])

    captured = {}
    password_router_module._email_sender.send_reset_link = lambda to_email, reset_link: captured.update(
        to_email=to_email, reset_link=reset_link
    )
    client.post("/auth/forgot-password", json={"username": "pwduser6"})
    token = captured["reset_link"].rsplit("/", 1)[-1]

    client.post("/auth/reset-password", json={"token": token, "new_password": "ResetPass789"})
    resp = client.post("/auth/reset-password", json={"token": token, "new_password": "AnotherPass1"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "PASSWORD_RESET_TOKEN_USED"


# ---------- POST /users/{user_id}/reset-password (admin) ----------


def test_admin_reset_password_happy_path():
    org_unit = _create_org_unit("PWD-07")
    user = _create_user("pwduser7", org_unit["id"])

    captured = {}
    password_router_module._email_sender.send_temp_password = (
        lambda to_email, temp_password: captured.update(
            to_email=to_email, temp_password=temp_password
        )
    )

    resp = client.post(f"/users/{user['id']}/reset-password")
    assert resp.status_code == 200, resp.text
    assert captured["to_email"] == "pwduser7@x.vn"
    assert len(captured["temp_password"]) >= 8

    # Mật khẩu cũ không còn hiệu lực, mật khẩu tạm hoạt động.
    resp_old = client.post(
        "/auth/login", json={"username": "pwduser7", "password": "Passw0rd!123"}
    )
    assert resp_old.status_code == 401

    resp_new = client.post(
        "/auth/login", json={"username": "pwduser7", "password": captured["temp_password"]}
    )
    assert resp_new.status_code == 200


def test_admin_reset_password_user_not_found_returns_404():
    resp = client.post("/users/999999/reset-password")
    assert resp.status_code == 404
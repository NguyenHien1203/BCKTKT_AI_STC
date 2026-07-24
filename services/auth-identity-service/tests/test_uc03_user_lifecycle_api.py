import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _create_org_unit(code):
    resp = client.post("/org-units", json={"code": code, "name": f"Đơn vị {code}", "unit_type": "SO"})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_user(username, org_unit_id):
    resp = client.post(
        "/users",
        json={
            "username": username,
            "full_name": "Người dùng test",
            "email": f"{username}@x.vn",
            "org_unit_id": org_unit_id,
            "role": "STAFF",
            "password": "Passw0rd!123",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_lock_then_unlock_user():
    org_unit = _create_org_unit("LCK-01")
    user = _create_user("lockuser1", org_unit["id"])

    resp = client.post(f"/users/{user['id']}/lock")
    assert resp.status_code == 200
    assert resp.json()["is_locked"] is True

    resp2 = client.post(f"/users/{user['id']}/unlock")
    assert resp2.status_code == 200
    assert resp2.json()["is_locked"] is False


def test_lock_not_found_returns_404():
    resp = client.post("/users/999999/lock")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "USER_NOT_FOUND"


def test_force_logout_revokes_sessions():
    org_unit = _create_org_unit("LCK-02")
    user = _create_user("logoutuser1", org_unit["id"])

    login_resp = client.post(
        "/auth/login", json={"username": "logoutuser1", "password": "Passw0rd!123"}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]

    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200

    force_resp = client.post(f"/users/{user['id']}/force-logout")
    assert force_resp.status_code == 200
    assert force_resp.json()["revoked_sessions"] == 1

    me_resp2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp2.status_code == 401


def test_reassign_org_unit_with_history():
    org_unit_a = _create_org_unit("HIST-A")
    org_unit_b = _create_org_unit("HIST-B")
    user = _create_user("histuser1", org_unit_a["id"])

    resp = client.patch(
        f"/users/{user['id']}/org-unit-with-history", json={"org_unit_id": org_unit_b["id"]}
    )
    assert resp.status_code == 200
    assert resp.json()["org_unit_id"] == org_unit_b["id"]

    history_resp = client.get(f"/users/{user['id']}/org-unit-history")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 1
    assert history[0]["new_org_unit_id"] == org_unit_b["id"]
    assert history[0]["old_org_unit_id"] == org_unit_a["id"]


def test_reassign_with_history_invalid_org_unit_returns_409():
    org_unit = _create_org_unit("HIST-C")
    user = _create_user("histuser2", org_unit["id"])

    resp = client.patch(
        f"/users/{user['id']}/org-unit-with-history", json={"org_unit_id": 999999}
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "USER_INVALID_ORG_UNIT"


def test_manual_sync_endpoint():
    resp = client.post("/users/manual-sync")
    assert resp.status_code == 200
    body = resp.json()
    assert body["remote_total"] == 0
    assert body["matched"] == 0

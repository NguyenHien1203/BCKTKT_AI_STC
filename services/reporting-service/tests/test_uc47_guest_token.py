"""Test UC-047 (nâng cấp): Superset Embedded Dashboard SDK + Guest Token.

Không gọi Superset thật (không có mạng trong sandbox test) — override
dependency `get_guest_token_service` bằng service dùng fake
GuestTokenIssuer/UserAccessContextProvider (unit test qua HTTP, cùng
tinh thần các NoOp stub khác trong dự án).
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from typing import Any, Dict, List  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.application.use_cases.issue_dashboard_guest_token import (  # noqa: E402
    DashboardGuestTokenService,
)
from app.domain.exceptions import GuestTokenIssueFailed  # noqa: E402
from app.domain.repositories import GuestTokenIssuer, UserAccessContextProvider  # noqa: E402
from app.infrastructure.db.repository_impl import (  # noqa: E402
    SqlAlchemyDashboardRepository,
)
from app.infrastructure.db.session import SessionLocal  # noqa: E402
from app.interfaces.api.dashboard_router import get_guest_token_service  # noqa: E402
from app.main import app  # noqa: E402


class FakeUserAccessContextProvider(UserAccessContextProvider):
    def get_rls_filters(self, user_id: int) -> List[Dict[str, Any]]:
        return [{"clause": f"org_unit_id = {user_id}"}]


class FakeGuestTokenIssuer(GuestTokenIssuer):
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.last_call = None

    def issue(self, dashboard_uid, user_id, username, full_name, rls_filters):
        self.last_call = {
            "dashboard_uid": dashboard_uid,
            "user_id": user_id,
            "username": username,
            "rls_filters": rls_filters,
        }
        if self.fail:
            raise GuestTokenIssueFailed("Superset không phản hồi (mô phỏng lỗi)")
        return "fake-guest-token-jwt"


_fake_issuer = FakeGuestTokenIssuer()


def _override_guest_token_service():
    db = SessionLocal()
    try:
        yield DashboardGuestTokenService(
            dashboard_repo=SqlAlchemyDashboardRepository(db),
            access_context_provider=FakeUserAccessContextProvider(),
            guest_token_issuer=_fake_issuer,
            superset_public_url="http://localhost:8088",
        )
    finally:
        db.close()


app.dependency_overrides[get_guest_token_service] = _override_guest_token_service
client = TestClient(app)


def _register_dashboard(code="DB-GT-01"):
    resp = client.post(
        "/dashboards",
        json={
            "code": code,
            "name": "Tổng hợp Ngân sách tỉnh",
            "description": "Bảng điều khiển demo",
            "category": "NGAN_SACH",
            "superset_dashboard_uid": "demo-uid-gt",
            "embed_url": "http://localhost:8088/superset/dashboard/demo-uid-gt/?standalone=1",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_get_guest_token_success():
    dashboard = _register_dashboard("DB-GT-SUCCESS")
    resp = client.get(
        f"/dashboards/{dashboard['id']}/guest-token",
        params={"user_id": 7, "username": "nguyenvana", "full_name": "Nguyễn Văn A"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["guest_token"] == "fake-guest-token-jwt"
    assert body["superset_dashboard_uid"] == "demo-uid-gt"
    assert body["superset_domain"] == "http://localhost:8088"

    # RLS filter theo người dùng đã được dựng và truyền đúng xuống issuer.
    assert _fake_issuer.last_call["user_id"] == 7
    assert _fake_issuer.last_call["username"] == "nguyenvana"
    assert _fake_issuer.last_call["rls_filters"] == [{"clause": "org_unit_id = 7"}]


def test_get_guest_token_dashboard_not_found():
    resp = client.get("/dashboards/999999/guest-token", params={"user_id": 1})
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DASHBOARD_NOT_FOUND"


def test_get_guest_token_dashboard_inactive():
    dashboard = _register_dashboard("DB-GT-INACTIVE")
    deact = client.post(f"/dashboards/{dashboard['id']}/deactivate")
    assert deact.status_code == 200
    resp = client.get(
        f"/dashboards/{dashboard['id']}/guest-token", params={"user_id": 1}
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "DASHBOARD_INACTIVE"


def test_get_guest_token_superset_failure_returns_502():
    dashboard = _register_dashboard("DB-GT-FAIL")
    _fake_issuer.fail = True
    try:
        resp = client.get(
            f"/dashboards/{dashboard['id']}/guest-token", params={"user_id": 1}
        )
        assert resp.status_code == 502
        assert resp.json()["detail"]["code"] == "SUPERSET_GUEST_TOKEN_FAILED"
    finally:
        _fake_issuer.fail = False


def test_get_guest_token_defaults_username_when_missing():
    dashboard = _register_dashboard("DB-GT-DEFAULT-USER")
    resp = client.get(
        f"/dashboards/{dashboard['id']}/guest-token", params={"user_id": 42}
    )
    assert resp.status_code == 200, resp.text
    assert _fake_issuer.last_call["username"] == "user-42"
"""Application layer — UC-12 (bản dùng Keycloak thật).

Thay vì tự kiểm tra password_hash nội bộ (xem auth_service.py — AuthService cũ,
vẫn giữ lại cho môi trường dev/test không có Keycloak), lớp này gửi
username/password sang Keycloak qua luồng "Direct Access Grant" (Resource
Owner Password Credentials) để lấy access token, xác nhận đăng nhập đúng,
rồi vẫn tạo session nội bộ như cũ để UC-03 "buộc đăng xuất" hoạt động được
(Keycloak token không thể bị thu hồi tức thì từ phía app nếu không gọi thêm
API revoke riêng — session nội bộ cho phép buộc đăng xuất ngay lập tức).

Yêu cầu: username đăng nhập phải trùng với username đã tạo trong Keycloak
(được tạo tự động khi gọi UserService.create — xem manage_user.py).
"""
import os
from datetime import datetime, timezone

import httpx

from app.domain.entities import User, UserSession
from app.domain.exceptions import InvalidCredentials, SessionNotFound, UserIsLocked
from app.domain.repositories import SessionRepository, TokenGenerator, UserRepository


class KeycloakAuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        token_generator: TokenGenerator,
        base_url: str | None = None,
        realm: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self._users = user_repo
        self._sessions = session_repo
        self._tokens = token_generator
        self._base_url = (base_url or os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080")).rstrip("/")
        self._realm = realm or os.getenv("KEYCLOAK_REALM", "hungyen-financial")
        self._client_id = client_id or os.getenv("KEYCLOAK_CLIENT_ID", "auth-identity-service")
        self._client_secret = client_secret or os.getenv("KEYCLOAK_CLIENT_SECRET", "")

    def _verify_with_keycloak(self, username: str, password: str) -> None:
        resp = httpx.post(
            f"{self._base_url}/realms/{self._realm}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "username": username,
                "password": password,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            raise InvalidCredentials()

    def login(self, username: str, password: str) -> tuple[User, str]:
        user = self._users.get_by_username(username)
        if user is None:
            raise InvalidCredentials()

        # Xác thực thật với Keycloak — ném InvalidCredentials nếu sai mật khẩu
        # hoặc user không tồn tại/không tìm thấy bên Keycloak.
        self._verify_with_keycloak(username, password)

        if not user.is_active or user.is_locked:
            raise UserIsLocked(user.id)

        token = self._tokens.generate()
        session = UserSession(
            id=None,
            user_id=user.id,
            token=token,
            created_at=datetime.now(timezone.utc).isoformat(),
            is_revoked=False,
        )
        self._sessions.create(session)
        return user, token

    def logout(self, token: str) -> None:
        session = self._sessions.get_by_token(token)
        if session is None or session.is_revoked:
            raise SessionNotFound()
        self._sessions.revoke_all_for_user(session.user_id)

    def get_current_user(self, token: str) -> User:
        session = self._sessions.get_by_token(token)
        if session is None or session.is_revoked:
            raise SessionNotFound()
        user = self._users.get_by_id(session.user_id)
        if user is None or not user.is_active or user.is_locked:
            raise SessionNotFound()
        return user

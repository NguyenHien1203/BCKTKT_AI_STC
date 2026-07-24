"""Application layer — UC-12: Đăng nhập / Đăng xuất hệ thống.

Đối chiếu docs/use_cases.json id=12. Tài liệu gốc mô tả SSO qua Keycloak
(OIDC, access 5 phút/refresh 30 phút, MFA cho vai trò quản trị). Ở giai đoạn
hiện tại, khi Keycloak chưa được cắm vào (dev/test), ta dùng đăng nhập
username/password nội bộ + session token — cùng interface `IdentityProviderClient`
nên khi tích hợp Keycloak thật, chỉ cần thay use case này bằng luồng OIDC
(authorization code / token exchange) mà không đổi domain/schema DB nhiều.

ADR liên quan: xem ARCHITECTURE.md — bổ sung ADR-003 khi merge UC-12.
"""
from datetime import datetime, timezone

from app.domain.entities import User, UserSession
from app.domain.exceptions import InvalidCredentials, SessionNotFound, UserIsLocked
from app.domain.repositories import PasswordHasher, SessionRepository, TokenGenerator, UserRepository


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        password_hasher: PasswordHasher,
        token_generator: TokenGenerator,
    ):
        self._users = user_repo
        self._sessions = session_repo
        self._hasher = password_hasher
        self._tokens = token_generator

    def login(self, username: str, password: str) -> tuple[User, str]:
        user = self._users.get_by_username(username)
        if user is None or not self._hasher.verify(password, user.password_hash):
            raise InvalidCredentials()
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

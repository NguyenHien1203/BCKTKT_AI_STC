"""Application layer — UC-12 (Keycloak SSO thật, Authorization Code Flow + PKCE).

Thay cho bản ROPC cũ (keycloak_auth_service.py — đã bỏ): ứng dụng KHÔNG BAO GIỜ
nhìn thấy mật khẩu người dùng. Luồng hoạt động:

1. Frontend (SPA, public client) tự tạo code_verifier/code_challenge (PKCE),
   điều hướng trình duyệt sang trang đăng nhập THẬT của Keycloak
   (GET /auth/oidc/config cho frontend biết auth_base_url/realm/client_id).
2. Người dùng đăng nhập trên Keycloak. Keycloak redirect về `redirect_uri` của
   frontend kèm `code`.
3. Frontend đổi `code` lấy `access_token` TRỰC TIẾP với Keycloak (client-side,
   public client + PKCE, không cần client_secret).
4. Frontend gửi `access_token` đó cho backend (POST /auth/oidc/session).
   Backend gọi Keycloak userinfo endpoint để XÁC THỰC access_token có hợp lệ
   không (không tự giải mã/verify chữ ký — dựa vào chính Keycloak trả lời),
   lấy `preferred_username`, map sang user nội bộ, rồi tạo session nội bộ như
   cũ để UC-03 "buộc đăng xuất" vẫn hoạt động (access_token Keycloak không thể
   bị thu hồi tức thì từ phía app).

Yêu cầu: username đăng nhập (preferred_username bên Keycloak) phải trùng với
username đã có trong bảng `users` nội bộ (được tạo tự động khi gọi
UserService.create — xem manage_user.py, hoặc phải seed thủ công cho user có
sẵn trong Keycloak, xem scripts/seed_keycloak_admin.py).
"""
import os

import httpx

from app.domain.entities import User, UserSession
from app.domain.exceptions import InvalidCredentials, SessionNotFound, UserIsLocked
from app.domain.repositories import SessionRepository, TokenGenerator, UserRepository
from datetime import datetime, timezone


class KeycloakOidcAuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        token_generator: TokenGenerator,
        base_url: str | None = None,
        realm: str | None = None,
    ):
        self._users = user_repo
        self._sessions = session_repo
        self._tokens = token_generator
        # KEYCLOAK_BASE_URL: URL nội bộ (docker network), dùng để backend gọi Keycloak
        # server-to-server (ví dụ http://keycloak:8080). Khác với KEYCLOAK_PUBLIC_BASE_URL
        # (trình duyệt dùng để redirect, ví dụ http://localhost:8080).
        self._base_url = (base_url or os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080")).rstrip("/")
        self._realm = realm or os.getenv("KEYCLOAK_REALM", "hungyen-financial")

    def _get_userinfo(self, access_token: str) -> dict:
        resp = httpx.get(
            f"{self._base_url}/realms/{self._realm}/protocol/openid-connect/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            www_auth = resp.headers.get("www-authenticate", "")
            print(
                f"[KeycloakOidcAuthService] userinfo call thất bại: "
                f"status={resp.status_code} www-authenticate={www_auth!r} "
                f"body={resp.text!r} url={self._base_url} realm={self._realm} "
                f"token_preview={access_token[:16]!r}...(len={len(access_token)})"
            )
            try:
                import base64
                import json as _json

                payload_b64 = access_token.split(".")[1]
                payload_b64 += "=" * (-len(payload_b64) % 4)
                claims = _json.loads(base64.urlsafe_b64decode(payload_b64))
                print(
                    f"[KeycloakOidcAuthService] token claims: iss={claims.get('iss')!r} "
                    f"aud={claims.get('aud')!r} azp={claims.get('azp')!r} "
                    f"exp={claims.get('exp')} typ={claims.get('typ')!r}"
                )
            except Exception as decode_exc:
                print(f"[KeycloakOidcAuthService] Không decode được token để debug: {decode_exc!r}")
            raise InvalidCredentials()
        return resp.json()

    def login_with_access_token(self, access_token: str) -> tuple[User, str]:
        userinfo = self._get_userinfo(access_token)
        username = userinfo.get("preferred_username")
        if not username:
            print(f"[KeycloakOidcAuthService] userinfo không có preferred_username: {userinfo!r}")
            raise InvalidCredentials()

        user = self._users.get_by_username(username)
        if user is None:
            print(f"[KeycloakOidcAuthService] Keycloak xác thực OK cho username='{username}' nhưng KHÔNG tìm thấy user này trong Postgres nội bộ (bảng identity.users).")
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

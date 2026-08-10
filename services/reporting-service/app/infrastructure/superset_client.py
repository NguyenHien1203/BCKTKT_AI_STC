"""Client gọi Superset REST API để phát hành Guest Token.

Luồng chuẩn theo tài liệu Superset (Embedded Dashboard SDK):
  1. POST /api/v1/security/login  (tài khoản dịch vụ riêng, quyền tối
     thiểu — xem SupersetConfig) -> access_token.
  2. POST /api/v1/security/guest_token/ (kèm access_token ở bước 1,
     payload user + resources (dashboard uid) + rls filters theo người
     dùng) -> guest_token (JWT ngắn hạn Superset tự ký, KHÔNG phải
     access_token của bước 1).
  3. Trả guest_token cho frontend, `@superset-ui/embedded-sdk` dùng token
     này gọi thẳng Superset (client-side) để tải + render dashboard trong
     iframe do SDK tự quản lý — Superset tự kiểm tra quyền/RLS theo guest
     token này cho MỌI truy vấn dữ liệu, không phải chỉ lúc tải trang.
"""
from typing import Any, Dict, List

import requests

from app.domain.exceptions import GuestTokenIssueFailed
from app.domain.repositories import GuestTokenIssuer
from app.infrastructure.config import SupersetConfig

_REQUEST_TIMEOUT_SECONDS = 10


class SupersetGuestTokenClient(GuestTokenIssuer):
    def __init__(self, config: type = SupersetConfig):
        self._config = config

    def _login(self) -> str:
        try:
            resp = requests.post(
                f"{self._config.BASE_URL}/api/v1/security/login",
                json={
                    "username": self._config.GUEST_TOKEN_USERNAME,
                    "password": self._config.GUEST_TOKEN_PASSWORD,
                    "provider": self._config.PROVIDER,
                    "refresh": True,
                },
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise GuestTokenIssueFailed(
                f"Không kết nối được tới Superset ({self._config.BASE_URL}): {exc}"
            ) from exc

        if resp.status_code != 200:
            raise GuestTokenIssueFailed(
                "Đăng nhập tài khoản dịch vụ Superset thất bại "
                f"(HTTP {resp.status_code}): {resp.text[:300]}"
            )
        access_token = resp.json().get("access_token")
        if not access_token:
            raise GuestTokenIssueFailed(
                "Superset không trả về access_token khi đăng nhập tài khoản dịch vụ"
            )
        return access_token

    def _csrf_token(self, access_token: str, session: requests.Session) -> str:
        """Superset bật CSRF protection mặc định (WTF_CSRF_ENABLED=True) cho
        mọi request ghi (POST/PUT/DELETE), kể cả khi gọi qua REST API bằng
        Bearer token. Phải lấy csrf_token riêng trước khi gọi guest_token/,
        dùng cùng `session` để giữ cookie (Set-Cookie session ở response
        này) rồi gửi lại cả cookie lẫn header X-CSRFToken ở request POST.
        """
        try:
            resp = session.get(
                f"{self._config.BASE_URL}/api/v1/security/csrf_token/",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise GuestTokenIssueFailed(
                f"Không lấy được CSRF token từ Superset: {exc}"
            ) from exc

        if resp.status_code != 200:
            raise GuestTokenIssueFailed(
                f"Superset từ chối cấp CSRF token (HTTP {resp.status_code}): "
                f"{resp.text[:300]}"
            )
        csrf_token = resp.json().get("result")
        if not csrf_token:
            raise GuestTokenIssueFailed("Superset không trả về CSRF token")
        return csrf_token

    def issue(
        self,
        dashboard_uid: str,
        user_id: int,
        username: str,
        full_name: str,
        rls_filters: List[Dict[str, Any]],
    ) -> str:
        if not self._config.is_configured():
            raise GuestTokenIssueFailed(
                "Chưa cấu hình SUPERSET_BASE_URL/SUPERSET_GUEST_TOKEN_USERNAME/"
                "SUPERSET_GUEST_TOKEN_PASSWORD — không thể phát hành guest token"
            )

        session = requests.Session()
        access_token = self._login()
        csrf_token = self._csrf_token(access_token, session)

        first_name, _, last_name = (full_name or username).partition(" ")
        payload = {
            "user": {
                "username": username or f"user-{user_id}",
                "first_name": first_name or username or "Người",
                "last_name": last_name or "dùng",
            },
            "resources": [{"type": "dashboard", "id": dashboard_uid}],
            "rls": rls_filters,
        }
        try:
            resp = session.post(
                f"{self._config.BASE_URL}/api/v1/security/guest_token/",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-CSRFToken": csrf_token,
                    "Referer": self._config.BASE_URL,
                },
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise GuestTokenIssueFailed(f"Gọi Superset guest_token thất bại: {exc}") from exc

        if resp.status_code != 200:
            raise GuestTokenIssueFailed(
                f"Superset từ chối phát hành guest token cho dashboard "
                f"'{dashboard_uid}' (HTTP {resp.status_code}): {resp.text[:300]} — "
                "kiểm tra dashboard đã bật \"Embed dashboard\" bên Superset chưa."
            )
        token = resp.json().get("token")
        if not token:
            raise GuestTokenIssueFailed("Superset không trả về guest token")
        return token
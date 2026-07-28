"""Application layer — UC-13: Đổi mật khẩu / Cấp lại mật khẩu.

Đối chiếu docs/use_cases.json id=13. 3 luồng nghiệp vụ:

1. Người dùng tự đổi mật khẩu (`change_password`): yêu cầu mật khẩu hiện tại
   đúng + mật khẩu mới thoả password policy.
2. Người dùng quên mật khẩu, tự cấp lại (`request_password_reset` +
   `reset_password_with_token`): hệ thống sinh token dùng 1 lần, có hạn
   `RESET_TOKEN_TTL_MINUTES` phút, gửi kèm link reset qua email. Để tránh lộ
   thông tin tài khoản nào tồn tại, `request_password_reset` luôn coi như
   thành công (không raise nếu không tìm thấy username/email).
3. Quản trị hệ thống cấp lại mật khẩu cho người dùng khác
   (`admin_reset_password`): hệ thống tự sinh mật khẩu tạm, cập nhật rồi
   gửi qua email — không trả mật khẩu tạm ra ngoài response API (chỉ gửi
   qua kênh email) để giảm rủi ro lộ lọt.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.domain.entities import PasswordResetToken, User
from app.domain.exceptions import (
    PasswordResetTokenExpired,
    PasswordResetTokenNotFound,
    PasswordResetTokenUsed,
    UserNotFound,
    WrongOldPassword,
)
from app.domain.repositories import (
    PasswordEmailSender,
    PasswordHasher,
    PasswordResetTokenRepository,
    SessionRepository,
    UserRepository,
)
from app.infrastructure.security import (
    generate_reset_token,
    generate_temp_password,
    validate_password_policy,
)

RESET_TOKEN_TTL_MINUTES = 30


class PasswordService:
    def __init__(
        self,
        user_repo: UserRepository,
        reset_token_repo: PasswordResetTokenRepository,
        password_hasher: PasswordHasher,
        email_sender: PasswordEmailSender,
        session_repo: Optional[SessionRepository] = None,
    ):
        self._users = user_repo
        self._reset_tokens = reset_token_repo
        self._hasher = password_hasher
        self._email_sender = email_sender
        self._sessions = session_repo

    # ---------- 1. Người dùng tự đổi mật khẩu ----------

    def change_password(self, user_id: int, old_password: str, new_password: str) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFound(user_id)
        if not self._hasher.verify(old_password, user.password_hash):
            raise WrongOldPassword()
        validate_password_policy(new_password)

        user.password_hash = self._hasher.hash(new_password)
        updated = self._users.update(user)
        # Đổi mật khẩu xong -> vô hiệu hoá toàn bộ phiên đăng nhập cũ (buộc
        # đăng nhập lại bằng mật khẩu mới), tương tự UC-03 buộc đăng xuất.
        if self._sessions is not None:
            self._sessions.revoke_all_for_user(user_id)
        return updated

    # ---------- 2. Người dùng quên mật khẩu, tự cấp lại ----------

    def request_password_reset(self, username: str, reset_link_base: str) -> None:
        user = self._users.get_by_username(username)
        if user is None or not user.is_active:
            # Không raise lỗi để tránh lộ thông tin tài khoản nào tồn tại
            # trong hệ thống (theo thông lệ bảo mật cho luồng quên mật khẩu).
            return

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
        reset_token = PasswordResetToken(
            id=None,
            user_id=user.id,
            token=generate_reset_token(),
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            is_used=False,
        )
        saved = self._reset_tokens.add(reset_token)
        reset_link = f"{reset_link_base.rstrip('/')}/{saved.token}"
        self._email_sender.send_reset_link(user.email, reset_link)

    def reset_password_with_token(self, token: str, new_password: str) -> User:
        reset_token = self._reset_tokens.get_by_token(token)
        if reset_token is None:
            raise PasswordResetTokenNotFound()
        if reset_token.is_used:
            raise PasswordResetTokenUsed()

        expires_at = datetime.fromisoformat(reset_token.expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise PasswordResetTokenExpired()

        user = self._users.get_by_id(reset_token.user_id)
        if user is None:
            raise UserNotFound(reset_token.user_id)

        validate_password_policy(new_password)
        user.password_hash = self._hasher.hash(new_password)
        updated = self._users.update(user)

        reset_token.mark_used()
        self._reset_tokens.update(reset_token)

        if self._sessions is not None:
            self._sessions.revoke_all_for_user(user.id)
        return updated

    # ---------- 3. Quản trị hệ thống cấp lại mật khẩu cho người dùng ----------

    def admin_reset_password(self, user_id: int) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFound(user_id)

        temp_password = generate_temp_password()
        user.password_hash = self._hasher.hash(temp_password)
        updated = self._users.update(user)

        self._email_sender.send_temp_password(user.email, temp_password)
        if self._sessions is not None:
            self._sessions.revoke_all_for_user(user_id)
        return updated
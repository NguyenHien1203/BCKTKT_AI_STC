"""Application layer — UC-14: Quản lý phiên đăng nhập.

Đối chiếu docs/use_cases.json id=14: Quản trị hệ thống xem danh sách phiên
đăng nhập đang hoạt động (toàn hệ thống hoặc theo từng người dùng) và có thể
thu hồi (vô hiệu hoá) một phiên cụ thể — khác với UC-03 "buộc đăng xuất" vốn
thu hồi toàn bộ phiên của 1 người dùng cùng lúc.
"""
from dataclasses import dataclass
from typing import List, Optional

from app.domain.entities import UserSession
from app.domain.exceptions import SessionNotFound, UserNotFound
from app.domain.repositories import SessionRepository, UserRepository


@dataclass
class SessionView:
    """Phiên đăng nhập kèm thông tin người dùng để hiển thị trên UI."""

    id: int
    user_id: int
    username: str
    full_name: str
    created_at: str
    is_revoked: bool
    token_preview: str


class SessionManagementService:
    def __init__(self, session_repo: SessionRepository, user_repo: UserRepository):
        self._sessions = session_repo
        self._users = user_repo

    def _to_view(self, session: UserSession) -> SessionView:
        user = self._users.get_by_id(session.user_id)
        token = session.token or ""
        token_preview = f"...{token[-8:]}" if len(token) > 8 else token
        return SessionView(
            id=session.id,
            user_id=session.user_id,
            username=user.username if user else "(đã xoá)",
            full_name=user.full_name if user else "(đã xoá)",
            created_at=session.created_at,
            is_revoked=session.is_revoked,
            token_preview=token_preview,
        )

    def list_sessions(
        self, user_id: Optional[int] = None, only_active: bool = True
    ) -> List[SessionView]:
        """Xem danh sách phiên đăng nhập — toàn hệ thống hoặc lọc theo user_id."""
        if user_id is not None:
            self._get_user(user_id)  # raise UserNotFound nếu không tồn tại
            sessions = self._sessions.list_for_user(user_id, only_active=only_active)
        else:
            sessions = self._sessions.list_all(only_active=only_active)
        return [self._to_view(s) for s in sessions]

    def revoke_session(self, session_id: int) -> None:
        """Thu hồi (vô hiệu hoá) 1 phiên đăng nhập cụ thể."""
        session = self._sessions.get_by_id(session_id)
        if session is None or session.is_revoked:
            raise SessionNotFound()
        self._sessions.revoke_by_id(session_id)

    def _get_user(self, user_id: int):
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user
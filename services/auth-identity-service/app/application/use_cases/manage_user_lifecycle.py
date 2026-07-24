"""Application layer — UC-03: Quản lý vòng đời người dùng.

Đối chiếu docs/use_cases.json id=3: khoá/mở khoá, buộc đăng xuất (vô hiệu hoá
tất cả phiên), đồng bộ thủ công từ IdP (đối soát), chuyển đơn vị + lưu lịch sử.
"""
from datetime import datetime, timezone
from typing import List

from app.domain.entities import OrgUnitAssignmentHistory, User
from app.domain.exceptions import InvalidOrgUnitForUser, UserNotFound
from app.domain.repositories import (
    IdentityProviderClient,
    OrgUnitHistoryRepository,
    OrgUnitRepository,
    SessionRepository,
    UserRepository,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserLifecycleService:
    def __init__(
        self,
        user_repo: UserRepository,
        org_unit_repo: OrgUnitRepository,
        session_repo: SessionRepository,
        history_repo: OrgUnitHistoryRepository,
        identity_provider: IdentityProviderClient,
    ):
        self._users = user_repo
        self._org_units = org_unit_repo
        self._sessions = session_repo
        self._history = history_repo
        self._idp = identity_provider

    def _get(self, user_id: int) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user

    def lock(self, user_id: int) -> User:
        user = self._get(user_id)
        user.lock()
        self._idp.disable_account(f"noop-{user.username}")
        updated = self._users.update(user)
        # Khoá xong thì buộc đăng xuất luôn, tránh phiên cũ vẫn dùng được.
        self._sessions.revoke_all_for_user(user_id)
        return updated

    def unlock(self, user_id: int) -> User:
        user = self._get(user_id)
        user.unlock()
        self._idp.enable_account(f"noop-{user.username}")
        return self._users.update(user)

    def force_logout(self, user_id: int) -> int:
        """Buộc đăng xuất người dùng. Trả về số phiên đã bị vô hiệu hoá."""
        self._get(user_id)  # đảm bảo tồn tại, raise UserNotFound nếu không
        return self._sessions.revoke_all_for_user(user_id)

    def manual_sync_from_idp(self) -> dict:
        """Đồng bộ thủ công từ IdP (Keycloak) để đối soát.

        Ở giai đoạn hiện tại (NoOpIdentityProviderClient), luôn trả về kết quả
        rỗng — hàm được thiết kế sẵn để khi cắm KeycloakIdentityProviderClient
        thật vào, logic đối soát (so khớp username, tạo/cập nhật local) chạy
        được ngay mà không cần sửa lại use case này.
        """
        remote_users = self._idp.sync_users()
        matched = 0
        unmatched = []
        for remote in remote_users:
            local = self._users.get_by_username(remote.get("username", ""))
            if local:
                matched += 1
            else:
                unmatched.append(remote.get("username"))
        return {
            "remote_total": len(remote_users),
            "matched": matched,
            "unmatched_usernames": unmatched,
            "synced_at": _now_iso(),
        }

    def reassign_org_unit_with_history(self, user_id: int, new_org_unit_id: int) -> User:
        user = self._get(user_id)
        target = self._org_units.get_by_id(new_org_unit_id)
        if target is None or not target.is_active:
            raise InvalidOrgUnitForUser(new_org_unit_id)

        old_org_unit_id = user.org_unit_id
        user.org_unit_id = new_org_unit_id
        updated = self._users.update(user)

        self._history.add(
            OrgUnitAssignmentHistory(
                id=None,
                user_id=user_id,
                old_org_unit_id=old_org_unit_id,
                new_org_unit_id=new_org_unit_id,
                changed_at=_now_iso(),
            )
        )
        return updated

    def get_org_unit_history(self, user_id: int) -> List[OrgUnitAssignmentHistory]:
        self._get(user_id)
        return self._history.list_for_user(user_id)

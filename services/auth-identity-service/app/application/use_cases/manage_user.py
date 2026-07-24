"""Application layer — UC-02: Quản lý người dùng (CRUD).

Đối chiếu docs/use_cases.json id=2. Nghiệp vụ: CRUD người dùng, gán đơn vị
công tác (phải là OrgUnit đang hoạt động), đồng bộ tạo/sửa/vô hiệu hoá sang
IdP (Keycloak) qua interface IdentityProviderClient.
"""
from typing import List, Optional

from app.domain.entities import User
from app.domain.exceptions import (
    InvalidOrgUnitForUser,
    UserNotFound,
    UsernameAlreadyExists,
)
from app.domain.repositories import IdentityProviderClient, OrgUnitRepository, UserRepository


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        org_unit_repo: OrgUnitRepository,
        identity_provider: IdentityProviderClient,
    ):
        self._users = user_repo
        self._org_units = org_unit_repo
        self._idp = identity_provider

    def _ensure_org_unit_active(self, org_unit_id: int) -> None:
        org_unit = self._org_units.get_by_id(org_unit_id)
        if org_unit is None or not org_unit.is_active:
            raise InvalidOrgUnitForUser(org_unit_id)

    def create(
        self,
        username: str,
        full_name: str,
        email: str,
        org_unit_id: int,
        role: str,
        password_hash: str,
    ) -> User:
        if self._users.get_by_username(username):
            raise UsernameAlreadyExists(username)
        self._ensure_org_unit_active(org_unit_id)

        # Đồng bộ tạo tài khoản ở IdP trước khi lưu (nếu IdP lỗi, không tạo bản ghi local mồ côi).
        self._idp.create_account(username=username, email=email, full_name=full_name)

        user = User(
            id=None,
            username=username.strip(),
            full_name=full_name.strip(),
            email=email.strip(),
            org_unit_id=org_unit_id,
            role=role,
            password_hash=password_hash,
            is_active=True,
        )
        return self._users.add(user)

    def get(self, user_id: int) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user

    def list_users(
        self, only_active: bool = False, org_unit_id: Optional[int] = None
    ) -> List[User]:
        return self._users.list(only_active=only_active, org_unit_id=org_unit_id)

    def update_profile(self, user_id: int, full_name: str, email: str) -> User:
        user = self.get(user_id)
        user.rename(full_name)
        user.email = email.strip()
        self._idp.update_account(f"noop-{user.username}", user.email, user.full_name)
        return self._users.update(user)

    def reassign_org_unit(self, user_id: int, new_org_unit_id: int) -> User:
        user = self.get(user_id)
        self._ensure_org_unit_active(new_org_unit_id)
        user.org_unit_id = new_org_unit_id
        return self._users.update(user)

    def deactivate(self, user_id: int) -> User:
        user = self.get(user_id)
        user.deactivate()
        self._idp.disable_account(f"noop-{user.username}")
        return self._users.update(user)

    def activate(self, user_id: int) -> User:
        user = self.get(user_id)
        user.activate()
        self._idp.enable_account(f"noop-{user.username}")
        return self._users.update(user)

    def delete(self, user_id: int) -> None:
        self.get(user_id)
        self._users.delete(user_id)

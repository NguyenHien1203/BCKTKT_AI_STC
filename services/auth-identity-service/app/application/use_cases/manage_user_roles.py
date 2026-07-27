"""Application layer — UC-05: Quản lý vai trò người dùng.

Đối chiếu docs/use_cases.json id=5: xem danh sách, thêm + gán bộ quyền, sửa
(lưu phiên bản mới — tăng `version`), xoá (kiểm tra ràng buộc: không cho xoá
nếu còn user đang gán role đó).
"""
from typing import List

from app.domain.entities import Role
from app.domain.exceptions import RoleCodeAlreadyExists, RoleInUse, RoleNotFound
from app.domain.repositories import RoleRepository, UserRepository


class RoleService:
    def __init__(self, role_repo: RoleRepository, user_repo: UserRepository):
        self._roles = role_repo
        self._users = user_repo

    def create(self, code: str, name: str, description: str, permissions: list) -> Role:
        if self._roles.get_by_code(code):
            raise RoleCodeAlreadyExists(code)
        role = Role(
            id=None,
            code=code.strip(),
            name=name.strip(),
            description=(description or "").strip(),
            permissions=list(permissions),
            version=1,
        )
        return self._roles.add(role)

    def get(self, role_id: int) -> Role:
        role = self._roles.get_by_id(role_id)
        if role is None:
            raise RoleNotFound(role_id)
        return role

    def list_roles(self) -> List[Role]:
        return self._roles.list()

    def update(self, role_id: int, name: str, description: str, permissions: list) -> Role:
        role = self.get(role_id)
        role.update(name, description, permissions)
        return self._roles.update(role)

    def delete(self, role_id: int) -> None:
        role = self.get(role_id)
        users_with_role = [u for u in self._users.list() if u.role == role.code]
        if users_with_role:
            raise RoleInUse(role.code, len(users_with_role))
        self._roles.delete(role_id)
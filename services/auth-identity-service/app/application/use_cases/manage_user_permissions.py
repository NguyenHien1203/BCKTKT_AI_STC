"""Application layer — UC-04: Quản lý quyền người dùng.

Đối chiếu docs/use_cases.json id=4: xem thông tin quyền của người dùng,
phân quyền theo vai trò (lưu permission_context), cấu hình permitted_domains +
unit, cấu hình mức nhạy cảm.

`UserPermissionContext` được tạo tự động (mặc định) lần đầu được truy vấn nếu
người dùng chưa từng được cấu hình quyền — tránh phải có 1 bước "khởi tạo"
riêng trước khi admin có thể xem/sửa.
"""
from app.domain.entities import UserPermissionContext
from app.domain.exceptions import (
    InvalidSensitivityLevel,
    PermissionContextNotFound,
    RoleNotFoundByCode,
    UserNotFound,
)
from app.domain.repositories import PermissionContextRepository, RoleRepository, UserRepository


class PermissionContextService:
    def __init__(
        self,
        context_repo: PermissionContextRepository,
        user_repo: UserRepository,
        role_repo: RoleRepository,
    ):
        self._contexts = context_repo
        self._users = user_repo
        self._roles = role_repo

    def _require_user(self, user_id: int):
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user

    def get_or_create(self, user_id: int) -> UserPermissionContext:
        """Xem thông tin quyền của người dùng.

        Nếu chưa có bản ghi permission_context, khởi tạo mặc định từ vai trò
        và đơn vị công tác hiện tại của người dùng.
        """
        user = self._require_user(user_id)
        context = self._contexts.get_by_user_id(user_id)
        if context is None:
            context = UserPermissionContext(
                id=None,
                user_id=user_id,
                role_code=user.role,
                permitted_domains=[],
                permitted_unit_id=user.org_unit_id,
                sensitivity_level="INTERNAL",
            )
            context = self._contexts.add(context)
        return context

    def get(self, user_id: int) -> UserPermissionContext:
        context = self._contexts.get_by_user_id(user_id)
        if context is None:
            raise PermissionContextNotFound(user_id)
        return context

    def assign_role(self, user_id: int, role_code: str) -> UserPermissionContext:
        """Phân quyền theo vai trò — hệ thống lưu permission_context."""
        context = self.get_or_create(user_id)
        role = self._roles.get_by_code(role_code)
        if role is None:
            raise RoleNotFoundByCode(role_code)
        context.assign_role(role.code)
        return self._contexts.update(context)

    def configure_domains(
        self, user_id: int, permitted_domains: list, permitted_unit_id
    ) -> UserPermissionContext:
        """Cấu hình permitted_domains + unit cho người dùng."""
        context = self.get_or_create(user_id)
        context.configure_domains(permitted_domains, permitted_unit_id)
        return self._contexts.update(context)

    def configure_sensitivity(self, user_id: int, sensitivity_level: str) -> UserPermissionContext:
        """Cấu hình mức nhạy cảm cho người dùng."""
        context = self.get_or_create(user_id)
        try:
            context.configure_sensitivity(sensitivity_level)
        except ValueError:
            raise InvalidSensitivityLevel(sensitivity_level)
        return self._contexts.update(context)
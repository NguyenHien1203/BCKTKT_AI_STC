"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities import (
    OrgUnit,
    OrgUnitAssignmentHistory,
    Role,
    SystemConfig,
    User,
    UserPermissionContext,
    UserSession,
)


class OrgUnitRepository(ABC):
    @abstractmethod
    def add(self, org_unit: OrgUnit) -> OrgUnit:
        ...

    @abstractmethod
    def get_by_id(self, org_unit_id: int) -> Optional[OrgUnit]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[OrgUnit]:
        ...

    @abstractmethod
    def list(self, only_active: bool = False) -> List[OrgUnit]:
        ...

    @abstractmethod
    def update(self, org_unit: OrgUnit) -> OrgUnit:
        ...

    @abstractmethod
    def delete(self, org_unit_id: int) -> None:
        ...


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> User:
        ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        ...

    @abstractmethod
    def list(self, only_active: bool = False, org_unit_id: Optional[int] = None) -> List[User]:
        ...

    @abstractmethod
    def update(self, user: User) -> User:
        ...

    @abstractmethod
    def delete(self, user_id: int) -> None:
        ...


class IdentityProviderClient(ABC):
    """Cổng đồng bộ người dùng với nhà cung cấp danh tính (Keycloak).

    Implement thật (Keycloak) hoặc giả (NoOp cho dev/test) đặt ở
    infrastructure/identity_provider.py.
    """

    @abstractmethod
    def create_account(self, username: str, email: str, full_name: str) -> str:
        """Tạo tài khoản ở IdP, trả về external_id (vd Keycloak user id)."""

    @abstractmethod
    def update_account(self, external_id: str, email: str, full_name: str) -> None:
        ...

    @abstractmethod
    def disable_account(self, external_id: str) -> None:
        ...

    @abstractmethod
    def enable_account(self, external_id: str) -> None:
        ...

    @abstractmethod
    def sync_users(self) -> list:
        """Kéo danh sách user mới nhất từ IdP để đối soát (UC-03).

        Trả về list[dict] với ít nhất {username, email, full_name}.
        """


class SessionRepository(ABC):
    @abstractmethod
    def create(self, session: UserSession) -> UserSession:
        ...

    @abstractmethod
    def get_by_token(self, token: str) -> Optional[UserSession]:
        ...

    @abstractmethod
    def revoke_all_for_user(self, user_id: int) -> int:
        """Trả về số phiên đã bị vô hiệu hoá."""


class OrgUnitHistoryRepository(ABC):
    @abstractmethod
    def add(self, entry: OrgUnitAssignmentHistory) -> OrgUnitAssignmentHistory:
        ...

    @abstractmethod
    def list_for_user(self, user_id: int) -> List[OrgUnitAssignmentHistory]:
        ...


class PasswordHasher(ABC):
    """Cổng băm/kiểm tra mật khẩu — implement ở infrastructure/security.py."""

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        ...

    @abstractmethod
    def verify(self, plain_password: str, password_hash: str) -> bool:
        ...


class TokenGenerator(ABC):
    """Cổng sinh session token — implement ở infrastructure/security.py."""

    @abstractmethod
    def generate(self) -> str:
        ...


class RoleRepository(ABC):
    @abstractmethod
    def add(self, role: Role) -> Role:
        ...

    @abstractmethod
    def get_by_id(self, role_id: int) -> Optional[Role]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Role]:
        ...

    @abstractmethod
    def list(self) -> List[Role]:
        ...

    @abstractmethod
    def update(self, role: Role) -> Role:
        ...

    @abstractmethod
    def delete(self, role_id: int) -> None:
        ...


class PermissionContextRepository(ABC):
    """Repository cho UC-04: Quản lý quyền người dùng."""

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> Optional[UserPermissionContext]:
        ...

    @abstractmethod
    def add(self, context: UserPermissionContext) -> UserPermissionContext:
        ...

    @abstractmethod
    def update(self, context: UserPermissionContext) -> UserPermissionContext:
        ...


class SystemConfigRepository(ABC):
    """Repository cho UC-06: Quản lý cấu hình hệ thống chung.

    Bản ghi "singleton" — chỉ có tối đa 1 dòng cấu hình đang hiệu lực.
    """

    @abstractmethod
    def get(self) -> Optional[SystemConfig]:
        ...

    @abstractmethod
    def save(self, config: SystemConfig) -> SystemConfig:
        """Tạo mới (lần đầu) hoặc cập nhật (upsert) dòng cấu hình singleton."""
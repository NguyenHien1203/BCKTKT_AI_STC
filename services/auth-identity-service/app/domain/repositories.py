"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities import OrgUnit, User


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

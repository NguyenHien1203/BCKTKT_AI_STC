"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities import OrgUnit


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

"""Application layer — UC-01: Quản lý cơ cấu tổ chức.

Đối chiếu docs/use_cases.json id=1: actor "Quản trị hệ thống".
Nghiệp vụ: CRUD đơn vị tổ chức dạng cây (Sở/Phòng/Xã), không cho xoá đơn vị
còn con trực thuộc, không cho trùng mã đơn vị.
"""
from typing import List, Optional

from app.domain.entities import OrgUnit
from app.domain.exceptions import (
    InvalidParentUnit,
    OrgUnitCodeAlreadyExists,
    OrgUnitHasChildren,
    OrgUnitNotFound,
)
from app.domain.repositories import OrgUnitRepository


class OrgUnitService:
    def __init__(self, repo: OrgUnitRepository):
        self._repo = repo

    def create(
        self,
        code: str,
        name: str,
        unit_type: str,
        parent_id: Optional[int] = None,
    ) -> OrgUnit:
        if self._repo.get_by_code(code):
            raise OrgUnitCodeAlreadyExists(code)

        if parent_id is not None and self._repo.get_by_id(parent_id) is None:
            raise InvalidParentUnit(parent_id)

        org_unit = OrgUnit(
            id=None,
            code=code.strip(),
            name=name.strip(),
            unit_type=unit_type,
            parent_id=parent_id,
            is_active=True,
        )
        return self._repo.add(org_unit)

    def get(self, org_unit_id: int) -> OrgUnit:
        org_unit = self._repo.get_by_id(org_unit_id)
        if org_unit is None:
            raise OrgUnitNotFound(org_unit_id)
        return org_unit

    def list_units(self, only_active: bool = False) -> List[OrgUnit]:
        return self._repo.list(only_active=only_active)

    def rename(self, org_unit_id: int, new_name: str) -> OrgUnit:
        org_unit = self.get(org_unit_id)
        org_unit.rename(new_name)
        return self._repo.update(org_unit)

    def deactivate(self, org_unit_id: int) -> OrgUnit:
        org_unit = self.get(org_unit_id)
        org_unit.deactivate()
        return self._repo.update(org_unit)

    def activate(self, org_unit_id: int) -> OrgUnit:
        org_unit = self.get(org_unit_id)
        org_unit.activate()
        return self._repo.update(org_unit)

    def delete(self, org_unit_id: int) -> None:
        self.get(org_unit_id)  # đảm bảo tồn tại -> raise OrgUnitNotFound nếu không
        children = [u for u in self._repo.list() if u.parent_id == org_unit_id]
        if children:
            raise OrgUnitHasChildren(org_unit_id)
        self._repo.delete(org_unit_id)

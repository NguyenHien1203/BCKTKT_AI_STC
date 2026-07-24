"""Unit test cho UC-01 (application layer) dùng fake in-memory repository.

Không cần Postgres/SQLite — test thuần logic nghiệp vụ theo RULE.md mục 3.
"""
import pytest

from app.application.use_cases.manage_org_unit import OrgUnitService
from app.domain.entities import OrgUnit
from app.domain.exceptions import (
    InvalidParentUnit,
    OrgUnitCodeAlreadyExists,
    OrgUnitHasChildren,
    OrgUnitNotFound,
)
from app.domain.repositories import OrgUnitRepository


class FakeOrgUnitRepository(OrgUnitRepository):
    def __init__(self):
        self._data = {}
        self._next_id = 1

    def add(self, org_unit: OrgUnit) -> OrgUnit:
        org_unit.id = self._next_id
        self._data[self._next_id] = org_unit
        self._next_id += 1
        return org_unit

    def get_by_id(self, org_unit_id):
        return self._data.get(org_unit_id)

    def get_by_code(self, code):
        for u in self._data.values():
            if u.code == code:
                return u
        return None

    def list(self, only_active: bool = False):
        values = list(self._data.values())
        if only_active:
            values = [u for u in values if u.is_active]
        return values

    def update(self, org_unit: OrgUnit) -> OrgUnit:
        self._data[org_unit.id] = org_unit
        return org_unit

    def delete(self, org_unit_id: int) -> None:
        self._data.pop(org_unit_id, None)


@pytest.fixture
def service():
    return OrgUnitService(FakeOrgUnitRepository())


def test_create_org_unit_happy_path(service):
    unit = service.create(code="SO-TC", name="Sở Tài chính", unit_type="SO")
    assert unit.id == 1
    assert unit.code == "SO-TC"
    assert unit.is_active is True


def test_create_child_org_unit(service):
    parent = service.create(code="SO-TC", name="Sở Tài chính", unit_type="SO")
    child = service.create(
        code="P-NS", name="Phòng Ngân sách", unit_type="PHONG", parent_id=parent.id
    )
    assert child.parent_id == parent.id


def test_create_duplicate_code_raises(service):
    service.create(code="SO-TC", name="Sở Tài chính", unit_type="SO")
    with pytest.raises(OrgUnitCodeAlreadyExists):
        service.create(code="SO-TC", name="Sở Tài chính (dup)", unit_type="SO")


def test_create_with_invalid_parent_raises(service):
    with pytest.raises(InvalidParentUnit):
        service.create(code="P-NS", name="Phòng Ngân sách", unit_type="PHONG", parent_id=999)


def test_get_not_found_raises(service):
    with pytest.raises(OrgUnitNotFound):
        service.get(999)


def test_rename_org_unit(service):
    unit = service.create(code="SO-TC", name="Sở Tài chính", unit_type="SO")
    renamed = service.rename(unit.id, "  Sở Tài chính tỉnh Hưng Yên  ")
    assert renamed.name == "Sở Tài chính tỉnh Hưng Yên"


def test_rename_with_empty_name_raises(service):
    unit = service.create(code="SO-TC", name="Sở Tài chính", unit_type="SO")
    with pytest.raises(ValueError):
        service.rename(unit.id, "   ")


def test_deactivate_then_activate(service):
    unit = service.create(code="SO-TC", name="Sở Tài chính", unit_type="SO")
    deactivated = service.deactivate(unit.id)
    assert deactivated.is_active is False
    activated = service.activate(unit.id)
    assert activated.is_active is True


def test_list_only_active(service):
    a = service.create(code="A", name="Đơn vị A", unit_type="SO")
    service.create(code="B", name="Đơn vị B", unit_type="SO")
    service.deactivate(a.id)
    active = service.list_units(only_active=True)
    assert len(active) == 1
    assert active[0].code == "B"


def test_delete_leaf_unit_ok(service):
    unit = service.create(code="SO-TC", name="Sở Tài chính", unit_type="SO")
    service.delete(unit.id)
    with pytest.raises(OrgUnitNotFound):
        service.get(unit.id)


def test_delete_unit_with_children_raises(service):
    parent = service.create(code="SO-TC", name="Sở Tài chính", unit_type="SO")
    service.create(code="P-NS", name="Phòng Ngân sách", unit_type="PHONG", parent_id=parent.id)
    with pytest.raises(OrgUnitHasChildren):
        service.delete(parent.id)


def test_delete_not_found_raises(service):
    with pytest.raises(OrgUnitNotFound):
        service.delete(999)

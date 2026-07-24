"""Unit test cho UC-02 (application layer) dùng fake in-memory repository."""
import pytest

from app.application.use_cases.manage_user import UserService
from app.domain.entities import OrgUnit, User
from app.domain.exceptions import (
    InvalidOrgUnitForUser,
    UserNotFound,
    UsernameAlreadyExists,
)
from app.domain.repositories import IdentityProviderClient, OrgUnitRepository, UserRepository
from app.infrastructure.identity_provider import NoOpIdentityProviderClient


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
        return next((u for u in self._data.values() if u.code == code), None)

    def list(self, only_active: bool = False):
        values = list(self._data.values())
        return [u for u in values if u.is_active] if only_active else values

    def update(self, org_unit: OrgUnit) -> OrgUnit:
        self._data[org_unit.id] = org_unit
        return org_unit

    def delete(self, org_unit_id: int) -> None:
        self._data.pop(org_unit_id, None)


class FakeUserRepository(UserRepository):
    def __init__(self):
        self._data = {}
        self._next_id = 1

    def add(self, user: User) -> User:
        user.id = self._next_id
        self._data[self._next_id] = user
        self._next_id += 1
        return user

    def get_by_id(self, user_id):
        return self._data.get(user_id)

    def get_by_username(self, username):
        return next((u for u in self._data.values() if u.username == username), None)

    def list(self, only_active: bool = False, org_unit_id=None):
        values = list(self._data.values())
        if only_active:
            values = [u for u in values if u.is_active]
        if org_unit_id is not None:
            values = [u for u in values if u.org_unit_id == org_unit_id]
        return values

    def update(self, user: User) -> User:
        self._data[user.id] = user
        return user

    def delete(self, user_id: int) -> None:
        self._data.pop(user_id, None)


@pytest.fixture
def org_unit_repo():
    return FakeOrgUnitRepository()


@pytest.fixture
def active_org_unit(org_unit_repo):
    return org_unit_repo.add(
        OrgUnit(id=None, code="SO-TC", name="Sở Tài chính", unit_type="SO")
    )


@pytest.fixture
def service(org_unit_repo):
    return UserService(
        user_repo=FakeUserRepository(),
        org_unit_repo=org_unit_repo,
        identity_provider=NoOpIdentityProviderClient(),
    )


def test_create_user_happy_path(service, active_org_unit):
    user = service.create(
        username="nguyenvana",
        full_name="Nguyễn Văn A",
        email="a@hungyen.gov.vn",
        org_unit_id=active_org_unit.id,
        role="STAFF",
    )
    assert user.id == 1
    assert user.is_active is True


def test_create_duplicate_username_raises(service, active_org_unit):
    service.create("nguyenvana", "A", "a@x.vn", active_org_unit.id, "STAFF")
    with pytest.raises(UsernameAlreadyExists):
        service.create("nguyenvana", "B", "b@x.vn", active_org_unit.id, "STAFF")


def test_create_with_invalid_org_unit_raises(service):
    with pytest.raises(InvalidOrgUnitForUser):
        service.create("nguyenvana", "A", "a@x.vn", 999, "STAFF")


def test_create_with_inactive_org_unit_raises(service, org_unit_repo, active_org_unit):
    org_unit_repo.update(
        OrgUnit(
            id=active_org_unit.id,
            code=active_org_unit.code,
            name=active_org_unit.name,
            unit_type=active_org_unit.unit_type,
            is_active=False,
        )
    )
    with pytest.raises(InvalidOrgUnitForUser):
        service.create("nguyenvana", "A", "a@x.vn", active_org_unit.id, "STAFF")


def test_get_not_found_raises(service):
    with pytest.raises(UserNotFound):
        service.get(999)


def test_update_profile(service, active_org_unit):
    user = service.create("nguyenvana", "A", "a@x.vn", active_org_unit.id, "STAFF")
    updated = service.update_profile(user.id, "Nguyễn Văn A (mới)", "moi@x.vn")
    assert updated.full_name == "Nguyễn Văn A (mới)"
    assert updated.email == "moi@x.vn"


def test_reassign_org_unit(service, org_unit_repo, active_org_unit):
    other_unit = org_unit_repo.add(
        OrgUnit(id=None, code="P-NS", name="Phòng Ngân sách", unit_type="PHONG")
    )
    user = service.create("nguyenvana", "A", "a@x.vn", active_org_unit.id, "STAFF")
    updated = service.reassign_org_unit(user.id, other_unit.id)
    assert updated.org_unit_id == other_unit.id


def test_reassign_to_invalid_org_unit_raises(service, active_org_unit):
    user = service.create("nguyenvana", "A", "a@x.vn", active_org_unit.id, "STAFF")
    with pytest.raises(InvalidOrgUnitForUser):
        service.reassign_org_unit(user.id, 999)


def test_deactivate_then_activate(service, active_org_unit):
    user = service.create("nguyenvana", "A", "a@x.vn", active_org_unit.id, "STAFF")
    deactivated = service.deactivate(user.id)
    assert deactivated.is_active is False
    activated = service.activate(user.id)
    assert activated.is_active is True


def test_list_filter_by_org_unit(service, org_unit_repo, active_org_unit):
    other_unit = org_unit_repo.add(
        OrgUnit(id=None, code="P-NS", name="Phòng Ngân sách", unit_type="PHONG")
    )
    service.create("a", "A", "a@x.vn", active_org_unit.id, "STAFF")
    service.create("b", "B", "b@x.vn", other_unit.id, "STAFF")
    result = service.list_users(org_unit_id=active_org_unit.id)
    assert len(result) == 1
    assert result[0].username == "a"


def test_delete_user(service, active_org_unit):
    user = service.create("nguyenvana", "A", "a@x.vn", active_org_unit.id, "STAFF")
    service.delete(user.id)
    with pytest.raises(UserNotFound):
        service.get(user.id)

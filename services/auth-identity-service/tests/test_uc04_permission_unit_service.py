"""Unit test cho UC-04 (application layer) dùng fake in-memory repository."""
import pytest

from app.application.use_cases.manage_user_permissions import PermissionContextService
from app.domain.entities import Role, User, UserPermissionContext
from app.domain.exceptions import (
    InvalidSensitivityLevel,
    PermissionContextNotFound,
    RoleNotFoundByCode,
    UserNotFound,
)
from app.domain.repositories import PermissionContextRepository, RoleRepository, UserRepository


class FakePermissionContextRepository(PermissionContextRepository):
    def __init__(self):
        self._data = {}
        self._next_id = 1

    def get_by_user_id(self, user_id):
        for c in self._data.values():
            if c.user_id == user_id:
                return c
        return None

    def add(self, context: UserPermissionContext) -> UserPermissionContext:
        context.id = self._next_id
        self._data[self._next_id] = context
        self._next_id += 1
        return context

    def update(self, context: UserPermissionContext) -> UserPermissionContext:
        self._data[context.id] = context
        return context


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
        for u in self._data.values():
            if u.username == username:
                return u
        return None

    def list(self, only_active=False, org_unit_id=None):
        return list(self._data.values())

    def update(self, user: User) -> User:
        self._data[user.id] = user
        return user

    def delete(self, user_id: int) -> None:
        self._data.pop(user_id, None)


class FakeRoleRepository(RoleRepository):
    def __init__(self):
        self._data = {}
        self._next_id = 1

    def add(self, role: Role) -> Role:
        role.id = self._next_id
        self._data[self._next_id] = role
        self._next_id += 1
        return role

    def get_by_id(self, role_id):
        return self._data.get(role_id)

    def get_by_code(self, code):
        for r in self._data.values():
            if r.code == code:
                return r
        return None

    def list(self):
        return list(self._data.values())

    def update(self, role: Role) -> Role:
        self._data[role.id] = role
        return role

    def delete(self, role_id: int) -> None:
        self._data.pop(role_id, None)


@pytest.fixture
def user_repo():
    repo = FakeUserRepository()
    repo.add(
        User(
            id=None,
            username="user1",
            full_name="Nguyễn Văn A",
            email="a@example.com",
            org_unit_id=10,
            role="STAFF",
        )
    )
    return repo


@pytest.fixture
def role_repo():
    repo = FakeRoleRepository()
    repo.add(Role(id=None, code="ADMIN", name="Quản trị", description="", permissions=["ALL"]))
    return repo


@pytest.fixture
def service(user_repo, role_repo):
    return PermissionContextService(FakePermissionContextRepository(), user_repo, role_repo)


def test_get_or_create_creates_default_context(service):
    ctx = service.get_or_create(1)
    assert ctx.id == 1
    assert ctx.user_id == 1
    assert ctx.role_code == "STAFF"
    assert ctx.permitted_unit_id == 10
    assert ctx.permitted_domains == []
    assert ctx.sensitivity_level == "INTERNAL"


def test_get_or_create_idempotent(service):
    ctx1 = service.get_or_create(1)
    ctx2 = service.get_or_create(1)
    assert ctx1.id == ctx2.id


def test_get_or_create_user_not_found_raises(service):
    with pytest.raises(UserNotFound):
        service.get_or_create(999)


def test_get_without_prior_context_raises(service):
    with pytest.raises(PermissionContextNotFound):
        service.get(1)


def test_assign_role_happy_path(service):
    ctx = service.assign_role(1, "ADMIN")
    assert ctx.role_code == "ADMIN"


def test_assign_role_unknown_code_raises(service):
    with pytest.raises(RoleNotFoundByCode):
        service.assign_role(1, "NOT_EXIST")


def test_configure_domains(service):
    ctx = service.configure_domains(1, ["TAI_SAN", "NGAN_SACH"], 20)
    assert ctx.permitted_domains == ["TAI_SAN", "NGAN_SACH"]
    assert ctx.permitted_unit_id == 20


def test_configure_sensitivity_happy_path(service):
    ctx = service.configure_sensitivity(1, "CONFIDENTIAL")
    assert ctx.sensitivity_level == "CONFIDENTIAL"


def test_configure_sensitivity_invalid_raises(service):
    with pytest.raises(InvalidSensitivityLevel):
        service.configure_sensitivity(1, "TOP_SECRET_INVALID")
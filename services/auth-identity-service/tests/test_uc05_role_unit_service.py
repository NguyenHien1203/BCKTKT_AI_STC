"""Unit test cho UC-05 (application layer) dùng fake in-memory repository."""
import pytest

from app.application.use_cases.manage_user_roles import RoleService
from app.domain.entities import Role, User
from app.domain.exceptions import RoleCodeAlreadyExists, RoleInUse, RoleNotFound
from app.domain.repositories import RoleRepository, UserRepository


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


@pytest.fixture
def role_repo():
    return FakeRoleRepository()


@pytest.fixture
def user_repo():
    return FakeUserRepository()


@pytest.fixture
def service(role_repo, user_repo):
    return RoleService(role_repo, user_repo)


def test_create_role_happy_path(service):
    role = service.create(
        code="STAFF_NS",
        name="Cán bộ ngân sách",
        description="Vai trò cho cán bộ phòng ngân sách",
        permissions=["REPORT_VIEW", "BUDGET_VIEW"],
    )
    assert role.id == 1
    assert role.version == 1
    assert role.permissions == ["REPORT_VIEW", "BUDGET_VIEW"]


def test_create_duplicate_code_raises(service):
    service.create(code="ADMIN", name="Quản trị", description="", permissions=[])
    with pytest.raises(RoleCodeAlreadyExists):
        service.create(code="ADMIN", name="Quản trị (dup)", description="", permissions=[])


def test_get_not_found_raises(service):
    with pytest.raises(RoleNotFound):
        service.get(999)


def test_update_role_increments_version(service):
    role = service.create(code="VIEWER", name="Người xem", description="", permissions=["VIEW"])
    updated = service.update(
        role.id, name="Người xem báo cáo", description="Cập nhật", permissions=["VIEW", "EXPORT"]
    )
    assert updated.version == 2
    assert updated.permissions == ["VIEW", "EXPORT"]
    assert updated.name == "Người xem báo cáo"


def test_list_roles(service):
    service.create(code="A", name="A", description="", permissions=[])
    service.create(code="B", name="B", description="", permissions=[])
    assert len(service.list_roles()) == 2


def test_delete_role_not_in_use_ok(service):
    role = service.create(code="TEMP", name="Tạm thời", description="", permissions=[])
    service.delete(role.id)
    with pytest.raises(RoleNotFound):
        service.get(role.id)


def test_delete_role_in_use_raises(service, user_repo):
    role = service.create(code="STAFF", name="Cán bộ", description="", permissions=[])
    user_repo.add(
        User(
            id=None,
            username="user1",
            full_name="Nguyễn Văn A",
            email="a@example.com",
            org_unit_id=1,
            role="STAFF",
        )
    )
    with pytest.raises(RoleInUse):
        service.delete(role.id)


def test_delete_not_found_raises(service):
    with pytest.raises(RoleNotFound):
        service.delete(999)
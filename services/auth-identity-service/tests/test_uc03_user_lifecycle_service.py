"""Unit test cho UC-03 (application layer) dùng fake in-memory repository."""
import pytest

from app.application.use_cases.manage_user_lifecycle import UserLifecycleService
from app.domain.entities import OrgUnit, OrgUnitAssignmentHistory, User, UserSession
from app.domain.exceptions import InvalidOrgUnitForUser, UserNotFound
from app.domain.repositories import (
    IdentityProviderClient,
    OrgUnitHistoryRepository,
    OrgUnitRepository,
    SessionRepository,
    UserRepository,
)


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


class FakeSessionRepository(SessionRepository):
    def __init__(self):
        self._data = {}
        self._next_id = 1

    def create(self, session: UserSession) -> UserSession:
        session.id = self._next_id
        self._data[self._next_id] = session
        self._next_id += 1
        return session

    def get_by_token(self, token: str):
        return next((s for s in self._data.values() if s.token == token), None)

    def revoke_all_for_user(self, user_id: int) -> int:
        count = 0
        for s in self._data.values():
            if s.user_id == user_id and not s.is_revoked:
                s.is_revoked = True
                count += 1
        return count


class FakeOrgUnitHistoryRepository(OrgUnitHistoryRepository):
    def __init__(self):
        self._data = []
        self._next_id = 1

    def add(self, entry: OrgUnitAssignmentHistory) -> OrgUnitAssignmentHistory:
        entry.id = self._next_id
        self._next_id += 1
        self._data.append(entry)
        return entry

    def list_for_user(self, user_id: int):
        return [e for e in self._data if e.user_id == user_id]


class FakeIdentityProviderClient(IdentityProviderClient):
    def __init__(self):
        self.disabled = []
        self.enabled = []

    def create_account(self, username, email, full_name) -> str:
        return f"fake-{username}"

    def update_account(self, external_id, email, full_name) -> None:
        return None

    def disable_account(self, external_id) -> None:
        self.disabled.append(external_id)

    def enable_account(self, external_id) -> None:
        self.enabled.append(external_id)

    def sync_users(self) -> list:
        return [{"username": "remoteuser", "email": "r@x.vn", "full_name": "Remote User"}]


@pytest.fixture
def org_unit_repo():
    return FakeOrgUnitRepository()


@pytest.fixture
def user_repo():
    return FakeUserRepository()


@pytest.fixture
def session_repo():
    return FakeSessionRepository()


@pytest.fixture
def history_repo():
    return FakeOrgUnitHistoryRepository()


@pytest.fixture
def idp():
    return FakeIdentityProviderClient()


@pytest.fixture
def active_org_unit(org_unit_repo):
    return org_unit_repo.add(OrgUnit(id=None, code="SO-TC", name="Sở Tài chính", unit_type="SO"))


@pytest.fixture
def other_org_unit(org_unit_repo):
    return org_unit_repo.add(OrgUnit(id=None, code="P-NS", name="Phòng Ngân sách", unit_type="PHONG"))


@pytest.fixture
def sample_user(user_repo, active_org_unit):
    return user_repo.add(
        User(
            id=None,
            username="nguyenvana",
            full_name="Nguyễn Văn A",
            email="a@x.vn",
            org_unit_id=active_org_unit.id,
            role="STAFF",
            password_hash="hash",
        )
    )


@pytest.fixture
def service(user_repo, org_unit_repo, session_repo, history_repo, idp):
    return UserLifecycleService(
        user_repo=user_repo,
        org_unit_repo=org_unit_repo,
        session_repo=session_repo,
        history_repo=history_repo,
        identity_provider=idp,
    )


def test_lock_user(service, sample_user, idp):
    locked = service.lock(sample_user.id)
    assert locked.is_locked is True
    assert f"noop-{sample_user.username}" in idp.disabled


def test_lock_not_found_raises(service):
    with pytest.raises(UserNotFound):
        service.lock(999)


def test_unlock_user(service, sample_user, idp):
    service.lock(sample_user.id)
    unlocked = service.unlock(sample_user.id)
    assert unlocked.is_locked is False
    assert f"noop-{sample_user.username}" in idp.enabled


def test_lock_revokes_all_sessions(service, sample_user, session_repo):
    session_repo.create(UserSession(id=None, user_id=sample_user.id, token="t1", created_at="now"))
    session_repo.create(UserSession(id=None, user_id=sample_user.id, token="t2", created_at="now"))
    service.lock(sample_user.id)
    assert session_repo.get_by_token("t1").is_revoked is True
    assert session_repo.get_by_token("t2").is_revoked is True


def test_force_logout_revokes_sessions(service, sample_user, session_repo):
    session_repo.create(UserSession(id=None, user_id=sample_user.id, token="t1", created_at="now"))
    session_repo.create(UserSession(id=None, user_id=sample_user.id, token="t2", created_at="now"))
    revoked_count = service.force_logout(sample_user.id)
    assert revoked_count == 2


def test_force_logout_not_found_raises(service):
    with pytest.raises(UserNotFound):
        service.force_logout(999)


def test_manual_sync_from_idp(service):
    result = service.manual_sync_from_idp()
    assert result["remote_total"] == 1
    assert result["matched"] == 0
    assert result["unmatched_usernames"] == ["remoteuser"]


def test_manual_sync_matches_existing_user(service, user_repo, active_org_unit):
    user_repo.add(
        User(
            id=None,
            username="remoteuser",
            full_name="Remote User",
            email="r@x.vn",
            org_unit_id=active_org_unit.id,
            role="STAFF",
            password_hash="hash",
        )
    )
    result = service.manual_sync_from_idp()
    assert result["matched"] == 1
    assert result["unmatched_usernames"] == []


def test_reassign_org_unit_with_history(service, sample_user, other_org_unit, history_repo):
    updated = service.reassign_org_unit_with_history(sample_user.id, other_org_unit.id)
    assert updated.org_unit_id == other_org_unit.id

    history = history_repo.list_for_user(sample_user.id)
    assert len(history) == 1
    assert history[0].new_org_unit_id == other_org_unit.id


def test_reassign_to_invalid_org_unit_raises(service, sample_user):
    with pytest.raises(InvalidOrgUnitForUser):
        service.reassign_org_unit_with_history(sample_user.id, 999)


def test_get_org_unit_history(service, sample_user, other_org_unit):
    service.reassign_org_unit_with_history(sample_user.id, other_org_unit.id)
    history = service.get_org_unit_history(sample_user.id)
    assert len(history) == 1

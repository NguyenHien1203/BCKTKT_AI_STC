"""Unit test cho UC-14 (application layer) dùng fake in-memory repository."""
import pytest

from app.application.use_cases.manage_session import SessionManagementService
from app.domain.entities import User, UserSession
from app.domain.exceptions import SessionNotFound, UserNotFound
from app.domain.repositories import SessionRepository, UserRepository


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
        return list(self._data.values())

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

    def get_by_id(self, session_id: int):
        return self._data.get(session_id)

    def list_for_user(self, user_id: int, only_active: bool = True):
        return [
            s
            for s in self._data.values()
            if s.user_id == user_id and (not only_active or not s.is_revoked)
        ]

    def list_all(self, only_active: bool = True):
        return [s for s in self._data.values() if not only_active or not s.is_revoked]

    def revoke_by_id(self, session_id: int) -> bool:
        s = self._data.get(session_id)
        if s is None or s.is_revoked:
            return False
        s.is_revoked = True
        return True


@pytest.fixture
def user_repo():
    repo = FakeUserRepository()
    repo.add(
        User(
            id=None,
            username="uc14user",
            full_name="Người dùng UC14",
            email="uc14@x.vn",
            org_unit_id=1,
            role="STAFF",
            password_hash="x",
            external_id="",
            is_active=True,
            is_locked=False,
        )
    )
    return repo


@pytest.fixture
def session_repo():
    return FakeSessionRepository()


@pytest.fixture
def service(session_repo, user_repo):
    return SessionManagementService(session_repo=session_repo, user_repo=user_repo)


def _make_session(session_repo, user_id, token):
    return session_repo.create(
        UserSession(id=None, user_id=user_id, token=token, created_at="2026-01-01T00:00:00+00:00")
    )


def test_list_sessions_all(service, session_repo):
    _make_session(session_repo, 1, "token-aaaaaaaa")
    _make_session(session_repo, 1, "token-bbbbbbbb")

    views = service.list_sessions()
    assert len(views) == 2
    assert views[0].username == "uc14user"
    assert views[0].token_preview.startswith("...")


def test_list_sessions_filtered_by_user(service, session_repo):
    _make_session(session_repo, 1, "token-aaaaaaaa")

    views = service.list_sessions(user_id=1)
    assert len(views) == 1
    assert views[0].user_id == 1


def test_list_sessions_unknown_user_raises(service):
    with pytest.raises(UserNotFound):
        service.list_sessions(user_id=999)


def test_revoke_session_marks_revoked(service, session_repo):
    session = _make_session(session_repo, 1, "token-aaaaaaaa")

    service.revoke_session(session.id)

    assert session_repo.get_by_id(session.id).is_revoked is True
    assert service.list_sessions(only_active=True) == []


def test_revoke_unknown_session_raises(service):
    with pytest.raises(SessionNotFound):
        service.revoke_session(999)


def test_revoke_already_revoked_session_raises(service, session_repo):
    session = _make_session(session_repo, 1, "token-aaaaaaaa")
    service.revoke_session(session.id)

    with pytest.raises(SessionNotFound):
        service.revoke_session(session.id)
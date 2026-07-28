"""Unit test cho UC-12 (application layer) dùng fake in-memory repository."""
import pytest

from app.application.use_cases.auth_service import AuthService
from app.domain.entities import User, UserSession
from app.domain.exceptions import InvalidCredentials, SessionNotFound, UserIsLocked
from app.domain.repositories import SessionRepository, UserRepository
from app.infrastructure.security import Pbkdf2PasswordHasher, SecretsTokenGenerator, hash_password


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
    return FakeUserRepository()


@pytest.fixture
def session_repo():
    return FakeSessionRepository()


@pytest.fixture
def service(user_repo, session_repo):
    return AuthService(
        user_repo=user_repo,
        session_repo=session_repo,
        password_hasher=Pbkdf2PasswordHasher(),
        token_generator=SecretsTokenGenerator(),
    )


@pytest.fixture
def active_user(user_repo):
    return user_repo.add(
        User(
            id=None,
            username="nguyenvana",
            full_name="Nguyễn Văn A",
            email="a@x.vn",
            org_unit_id=1,
            role="STAFF",
            password_hash=hash_password("Passw0rd!123"),
        )
    )


def test_login_happy_path(service, active_user):
    user, token = service.login("nguyenvana", "Passw0rd!123")
    assert user.id == active_user.id
    assert isinstance(token, str) and len(token) > 10


def test_login_wrong_password_raises(service, active_user):
    with pytest.raises(InvalidCredentials):
        service.login("nguyenvana", "sai-mat-khau")


def test_login_unknown_username_raises(service):
    with pytest.raises(InvalidCredentials):
        service.login("khongtontai", "Passw0rd!123")


def test_login_locked_user_raises(service, active_user, user_repo):
    active_user.lock()
    user_repo.update(active_user)
    with pytest.raises(UserIsLocked):
        service.login("nguyenvana", "Passw0rd!123")


def test_login_inactive_user_raises(service, active_user, user_repo):
    active_user.deactivate()
    user_repo.update(active_user)
    with pytest.raises(UserIsLocked):
        service.login("nguyenvana", "Passw0rd!123")


def test_get_current_user_with_valid_token(service, active_user):
    _, token = service.login("nguyenvana", "Passw0rd!123")
    current = service.get_current_user(token)
    assert current.username == "nguyenvana"


def test_get_current_user_invalid_token_raises(service):
    with pytest.raises(SessionNotFound):
        service.get_current_user("token-khong-ton-tai")


def test_logout_revokes_session(service, active_user):
    _, token = service.login("nguyenvana", "Passw0rd!123")
    service.logout(token)
    with pytest.raises(SessionNotFound):
        service.get_current_user(token)


def test_logout_invalid_token_raises(service):
    with pytest.raises(SessionNotFound):
        service.logout("token-khong-ton-tai")
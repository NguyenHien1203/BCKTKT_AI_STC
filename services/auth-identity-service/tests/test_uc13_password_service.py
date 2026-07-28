"""Unit test cho UC-13 (application layer) dùng fake in-memory repository."""
from datetime import datetime, timedelta, timezone

import pytest

from app.application.use_cases.password_service import PasswordService
from app.domain.entities import PasswordResetToken, User
from app.domain.exceptions import (
    PasswordResetTokenExpired,
    PasswordResetTokenNotFound,
    PasswordResetTokenUsed,
    UserNotFound,
    WeakPassword,
    WrongOldPassword,
)
from app.domain.repositories import PasswordEmailSender, PasswordResetTokenRepository, UserRepository
from app.infrastructure.security import Pbkdf2PasswordHasher, hash_password


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


class FakePasswordResetTokenRepository(PasswordResetTokenRepository):
    def __init__(self):
        self._data = {}
        self._next_id = 1

    def add(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        reset_token.id = self._next_id
        self._data[self._next_id] = reset_token
        self._next_id += 1
        return reset_token

    def get_by_token(self, token: str):
        return next((t for t in self._data.values() if t.token == token), None)

    def update(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        self._data[reset_token.id] = reset_token
        return reset_token


class FakePasswordEmailSender(PasswordEmailSender):
    def __init__(self):
        self.reset_links = []
        self.temp_passwords = []

    def send_reset_link(self, to_email: str, reset_link: str) -> None:
        self.reset_links.append((to_email, reset_link))

    def send_temp_password(self, to_email: str, temp_password: str) -> None:
        self.temp_passwords.append((to_email, temp_password))


@pytest.fixture
def user_repo():
    return FakeUserRepository()


@pytest.fixture
def reset_token_repo():
    return FakePasswordResetTokenRepository()


@pytest.fixture
def email_sender():
    return FakePasswordEmailSender()


@pytest.fixture
def service(user_repo, reset_token_repo, email_sender):
    return PasswordService(
        user_repo=user_repo,
        reset_token_repo=reset_token_repo,
        password_hasher=Pbkdf2PasswordHasher(),
        email_sender=email_sender,
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


# ---------- 1. Đổi mật khẩu ----------


def test_change_password_happy_path(service, active_user, user_repo):
    service.change_password(active_user.id, "Passw0rd!123", "NewPass456")
    updated = user_repo.get_by_id(active_user.id)
    hasher = Pbkdf2PasswordHasher()
    assert hasher.verify("NewPass456", updated.password_hash)


def test_change_password_wrong_old_password_raises(service, active_user):
    with pytest.raises(WrongOldPassword):
        service.change_password(active_user.id, "sai-mat-khau", "NewPass456")


def test_change_password_weak_new_password_raises(service, active_user):
    with pytest.raises(WeakPassword):
        service.change_password(active_user.id, "Passw0rd!123", "short1")


def test_change_password_weak_no_digit_raises(service, active_user):
    with pytest.raises(WeakPassword):
        service.change_password(active_user.id, "Passw0rd!123", "onlylettersnodigits")


def test_change_password_user_not_found_raises(service):
    with pytest.raises(UserNotFound):
        service.change_password(999, "x", "NewPass456")


# ---------- 2. Quên mật khẩu / cấp lại bằng token ----------


def test_request_password_reset_sends_email(service, active_user, email_sender, reset_token_repo):
    service.request_password_reset("nguyenvana", "https://app.local/reset")
    assert len(email_sender.reset_links) == 1
    to_email, link = email_sender.reset_links[0]
    assert to_email == "a@x.vn"
    assert link.startswith("https://app.local/reset/")
    assert len(reset_token_repo._data) == 1


def test_request_password_reset_unknown_username_no_error(service, email_sender):
    # Không raise lỗi để tránh lộ thông tin tài khoản tồn tại hay không.
    service.request_password_reset("khongtontai", "https://app.local/reset")
    assert len(email_sender.reset_links) == 0


def test_reset_password_with_token_happy_path(service, active_user, email_sender, user_repo):
    service.request_password_reset("nguyenvana", "https://app.local/reset")
    _, link = email_sender.reset_links[0]
    token = link.rsplit("/", 1)[-1]

    service.reset_password_with_token(token, "BrandNewPass1")
    updated = user_repo.get_by_id(active_user.id)
    hasher = Pbkdf2PasswordHasher()
    assert hasher.verify("BrandNewPass1", updated.password_hash)


def test_reset_password_with_invalid_token_raises(service):
    with pytest.raises(PasswordResetTokenNotFound):
        service.reset_password_with_token("token-khong-ton-tai", "BrandNewPass1")


def test_reset_password_with_used_token_raises(service, active_user, email_sender):
    service.request_password_reset("nguyenvana", "https://app.local/reset")
    _, link = email_sender.reset_links[0]
    token = link.rsplit("/", 1)[-1]

    service.reset_password_with_token(token, "BrandNewPass1")
    with pytest.raises(PasswordResetTokenUsed):
        service.reset_password_with_token(token, "AnotherPass2")


def test_reset_password_with_expired_token_raises(service, active_user, reset_token_repo):
    expired_token = PasswordResetToken(
        id=None,
        user_id=active_user.id,
        token="expired-token-123",
        created_at=(datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat(),
        expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        is_used=False,
    )
    reset_token_repo.add(expired_token)
    with pytest.raises(PasswordResetTokenExpired):
        service.reset_password_with_token("expired-token-123", "BrandNewPass1")


# ---------- 3. Quản trị viên cấp lại mật khẩu ----------


def test_admin_reset_password_generates_and_sends_temp_password(
    service, active_user, email_sender, user_repo
):
    service.admin_reset_password(active_user.id)
    assert len(email_sender.temp_passwords) == 1
    to_email, temp_password = email_sender.temp_passwords[0]
    assert to_email == "a@x.vn"

    updated = user_repo.get_by_id(active_user.id)
    hasher = Pbkdf2PasswordHasher()
    assert hasher.verify(temp_password, updated.password_hash)
    # Mật khẩu cũ không còn dùng được nữa.
    assert not hasher.verify("Passw0rd!123", updated.password_hash)


def test_admin_reset_password_user_not_found_raises(service):
    with pytest.raises(UserNotFound):
        service.admin_reset_password(999)
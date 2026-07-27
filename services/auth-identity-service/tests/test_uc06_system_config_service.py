"""Unit test cho UC-06 (application layer) dùng fake in-memory repository."""
import pytest

from app.application.use_cases.manage_system_config import SystemConfigService
from app.domain.entities import SystemConfig
from app.domain.exceptions import InvalidSystemConfig
from app.domain.repositories import SystemConfigRepository


class FakeSystemConfigRepository(SystemConfigRepository):
    def __init__(self):
        self._config = None
        self._next_id = 1

    def get(self):
        return self._config

    def save(self, config: SystemConfig) -> SystemConfig:
        if config.id is None:
            config.id = self._next_id
            self._next_id += 1
        self._config = config
        return config


@pytest.fixture
def repo():
    return FakeSystemConfigRepository()


@pytest.fixture
def service(repo):
    return SystemConfigService(repo)


def test_get_config_auto_creates_default(service):
    config = service.get_config()
    assert config.id == 1
    assert config.request_timeout_seconds == 30
    assert config.max_upload_size_mb == 50
    assert config.default_language == "vi"
    assert config.updated_at is not None


def test_get_config_returns_same_singleton_on_repeated_calls(service):
    first = service.get_config()
    second = service.get_config()
    assert first.id == second.id == 1


def test_update_config_happy_path(service):
    updated = service.update_config(
        request_timeout_seconds=60, max_upload_size_mb=200, default_language="en"
    )
    assert updated.request_timeout_seconds == 60
    assert updated.max_upload_size_mb == 200
    assert updated.default_language == "en"

    # Áp dụng ngay: đọc lại phải thấy giá trị mới, không cần khởi động lại.
    reread = service.get_config()
    assert reread.request_timeout_seconds == 60
    assert reread.max_upload_size_mb == 200
    assert reread.default_language == "en"


def test_update_config_invalid_timeout_raises(service):
    with pytest.raises(InvalidSystemConfig):
        service.update_config(
            request_timeout_seconds=0, max_upload_size_mb=50, default_language="vi"
        )


def test_update_config_invalid_upload_size_raises(service):
    with pytest.raises(InvalidSystemConfig):
        service.update_config(
            request_timeout_seconds=30, max_upload_size_mb=99999, default_language="vi"
        )


def test_update_config_invalid_language_raises(service):
    with pytest.raises(InvalidSystemConfig):
        service.update_config(
            request_timeout_seconds=30, max_upload_size_mb=50, default_language="fr"
        )


def test_update_config_does_not_persist_on_validation_error(service):
    service.update_config(
        request_timeout_seconds=45, max_upload_size_mb=100, default_language="vi"
    )
    with pytest.raises(InvalidSystemConfig):
        service.update_config(
            request_timeout_seconds=-5, max_upload_size_mb=100, default_language="vi"
        )
    # Giá trị cũ (hợp lệ trước đó) không bị ghi đè bởi lần cập nhật lỗi.
    config = service.get_config()
    assert config.request_timeout_seconds == 45
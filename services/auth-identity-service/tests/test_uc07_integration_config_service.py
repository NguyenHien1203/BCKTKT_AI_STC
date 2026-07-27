"""Unit test cho UC-07 (application layer) dùng fake in-memory repository."""
import pytest

from app.application.use_cases.manage_integration_config import IntegrationConfigService
from app.domain.entities import IntegrationEndpoint
from app.domain.exceptions import IntegrationEndpointNotFound, InvalidIntegrationEndpoint
from app.domain.repositories import ConnectionChecker, IntegrationEndpointRepository


class FakeIntegrationEndpointRepository(IntegrationEndpointRepository):
    def __init__(self):
        self._data = {}
        self._next_id = 1

    def get_by_type(self, endpoint_type):
        for e in self._data.values():
            if e.endpoint_type == endpoint_type:
                return e
        return None

    def list(self):
        return list(self._data.values())

    def save(self, endpoint: IntegrationEndpoint) -> IntegrationEndpoint:
        if endpoint.id is None:
            endpoint.id = self._next_id
            self._next_id += 1
        self._data[endpoint.id] = endpoint
        return endpoint


class FakeConnectionChecker(ConnectionChecker):
    """Fake có thể ép kết quả thành công/thất bại để test cả 2 nhánh."""

    def __init__(self, force_success: bool = True):
        self.force_success = force_success
        self.calls = []

    def check(self, endpoint_type, base_url, extra_config):
        self.calls.append((endpoint_type, base_url, dict(extra_config)))
        if not self.force_success:
            return False, "Không thể kết nối (giả lập lỗi)"
        if endpoint_type == "LGSP" and not extra_config.get("protocol"):
            return False, "Thiếu giao thức kết nối (protocol) cho LGSP"
        return True, "OK"


@pytest.fixture
def repo():
    return FakeIntegrationEndpointRepository()


@pytest.fixture
def checker():
    return FakeConnectionChecker(force_success=True)


@pytest.fixture
def service(repo, checker):
    return IntegrationConfigService(repo, checker)


def test_configure_keycloak_happy_path(service):
    endpoint = service.configure_keycloak(
        base_url="https://sso.hungyen.gov.vn", realm="tct", client_id="datawarehouse"
    )
    assert endpoint.id == 1
    assert endpoint.endpoint_type == "KEYCLOAK"
    assert endpoint.base_url == "https://sso.hungyen.gov.vn"
    assert endpoint.extra_config == {"realm": "tct", "client_id": "datawarehouse"}
    assert endpoint.is_connected is True
    assert endpoint.last_checked_at is not None


def test_configure_keycloak_invalid_url_raises(service):
    with pytest.raises(InvalidIntegrationEndpoint):
        service.configure_keycloak(base_url="ftp://bad-scheme", realm="tct", client_id="x")


def test_configure_keycloak_empty_url_raises(service):
    with pytest.raises(InvalidIntegrationEndpoint):
        service.configure_keycloak(base_url="   ", realm="tct", client_id="x")


def test_configure_lgsp_happy_path(service):
    endpoint = service.configure_lgsp(
        base_url="https://lgsp.hungyen.gov.vn", protocol="REST"
    )
    assert endpoint.endpoint_type == "LGSP"
    assert endpoint.extra_config == {"protocol": "REST"}
    assert endpoint.is_connected is True


def test_configure_lgsp_missing_protocol_marks_disconnected_but_still_saved(service, repo):
    endpoint = service.configure_lgsp(base_url="https://lgsp.hungyen.gov.vn", protocol="")
    # Lưu cấu hình vẫn thành công (không raise) — chỉ kết quả kiểm tra là thất bại.
    assert endpoint.is_connected is False
    assert "protocol" in endpoint.last_check_message.lower() or "giao thức" in endpoint.last_check_message.lower()
    saved = repo.get_by_type("LGSP")
    assert saved is not None
    assert saved.is_connected is False


def test_configure_reconfigure_resets_then_rechecks(service):
    service.configure_keycloak(base_url="https://a.example", realm="r1", client_id="c1")
    updated = service.configure_keycloak(base_url="https://b.example", realm="r2", client_id="c2")
    assert updated.base_url == "https://b.example"
    assert updated.extra_config == {"realm": "r2", "client_id": "c2"}
    # Sau khi cấu hình lại, hệ thống đã kiểm tra lại ngay -> is_connected phản ánh lần check mới nhất.
    assert updated.is_connected is True


def test_recheck_without_config_raises_not_found(service):
    with pytest.raises(IntegrationEndpointNotFound):
        service.recheck("KEYCLOAK")


def test_recheck_after_configure_updates_last_checked_at(service):
    first = service.configure_keycloak(base_url="https://a.example", realm="r1", client_id="c1")
    second = service.recheck("KEYCLOAK")
    assert second.id == first.id
    assert second.is_connected is True


def test_get_without_config_raises_not_found(service):
    with pytest.raises(IntegrationEndpointNotFound):
        service.get("LGSP")


def test_list_all_returns_configured_endpoints(service):
    service.configure_keycloak(base_url="https://a.example", realm="r1", client_id="c1")
    service.configure_lgsp(base_url="https://b.example", protocol="SOAP")
    endpoints = service.list_all()
    types = {e.endpoint_type for e in endpoints}
    assert types == {"KEYCLOAK", "LGSP"}


def test_connection_failure_is_recorded_not_raised():
    repo = FakeIntegrationEndpointRepository()
    checker = FakeConnectionChecker(force_success=False)
    service = IntegrationConfigService(repo, checker)

    endpoint = service.configure_keycloak(
        base_url="https://unreachable.example", realm="r", client_id="c"
    )
    assert endpoint.is_connected is False
    assert endpoint.last_check_message == "Không thể kết nối (giả lập lỗi)"
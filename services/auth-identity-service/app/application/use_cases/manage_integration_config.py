"""Application layer — UC-07: Quản lý cấu hình tích hợp.

Đối chiếu docs/use_cases.json id=7: cấu hình điểm cuối Keycloak (lưu + kiểm
tra kết nối) và cấu hình điểm cuối LGSP (lưu + kiểm tra giao thức kết nối).
Việc lưu luôn thành công nếu dữ liệu hợp lệ; kiểm tra kết nối là bước tiếp
theo, kết quả (thành công/thất bại) được ghi nhận lại trên chính bản ghi để
admin biết trạng thái hiện tại, không chặn việc lưu cấu hình.
"""
from datetime import datetime, timezone

from app.domain.entities import IntegrationEndpoint
from app.domain.exceptions import IntegrationEndpointNotFound, InvalidIntegrationEndpoint
from app.domain.repositories import ConnectionChecker, IntegrationEndpointRepository


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IntegrationConfigService:
    def __init__(self, endpoint_repo: IntegrationEndpointRepository, checker: ConnectionChecker):
        self._endpoints = endpoint_repo
        self._checker = checker

    def _get_or_create(self, endpoint_type: str) -> IntegrationEndpoint:
        endpoint = self._endpoints.get_by_type(endpoint_type)
        if endpoint is None:
            endpoint = IntegrationEndpoint(
                id=None, endpoint_type=endpoint_type, base_url="", extra_config={}
            )
        return endpoint

    def configure_keycloak(self, base_url: str, realm: str, client_id: str) -> IntegrationEndpoint:
        """Cấu hình điểm cuối Keycloak — lưu + kiểm tra kết nối."""
        endpoint = self._get_or_create("KEYCLOAK")
        try:
            endpoint.configure(base_url, {"realm": realm, "client_id": client_id})
        except ValueError as exc:
            raise InvalidIntegrationEndpoint(str(exc)) from exc
        saved = self._endpoints.save(endpoint)
        return self._check_and_save(saved)

    def configure_lgsp(self, base_url: str, protocol: str) -> IntegrationEndpoint:
        """Cấu hình điểm cuối LGSP — lưu + kiểm tra giao thức kết nối."""
        endpoint = self._get_or_create("LGSP")
        try:
            endpoint.configure(base_url, {"protocol": protocol})
        except ValueError as exc:
            raise InvalidIntegrationEndpoint(str(exc)) from exc
        saved = self._endpoints.save(endpoint)
        return self._check_and_save(saved)

    def _check_and_save(self, endpoint: IntegrationEndpoint) -> IntegrationEndpoint:
        is_connected, message = self._checker.check(
            endpoint.endpoint_type, endpoint.base_url, endpoint.extra_config
        )
        endpoint.record_check_result(is_connected, message, _utc_now_iso())
        return self._endpoints.save(endpoint)

    def recheck(self, endpoint_type: str) -> IntegrationEndpoint:
        """Kiểm tra lại kết nối cho điểm cuối đã cấu hình (không đổi cấu hình)."""
        endpoint = self._endpoints.get_by_type(endpoint_type)
        if endpoint is None:
            raise IntegrationEndpointNotFound(endpoint_type)
        return self._check_and_save(endpoint)

    def get(self, endpoint_type: str) -> IntegrationEndpoint:
        endpoint = self._endpoints.get_by_type(endpoint_type)
        if endpoint is None:
            raise IntegrationEndpointNotFound(endpoint_type)
        return endpoint

    def list_all(self) -> list:
        return self._endpoints.list()
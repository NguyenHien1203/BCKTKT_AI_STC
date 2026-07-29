"""Application layer — UC-016: Quản lý thư viện bộ kết nối.

Đối chiếu docs/use_cases.json id=16: actor "Quản trị Tích hợp".
Luồng nghiệp vụ:
1. Xem danh sách bộ kết nối có sẵn (tệp/REST API/JDBC/SOAP) -> hệ thống hiển thị.
2. Đăng ký bộ kết nối mới (plugin) -> hệ thống nạp mô-đun + kiểm tra giao diện.
3. Cập nhật phiên bản bộ kết nối -> hệ thống khởi động lại luân phiên tiến
   trình nhận sự kiện (rolling restart của consumer/listener).

Không cho trùng mã bộ kết nối (`code`). Đăng ký thất bại (409) nếu bước
kiểm tra giao diện plugin không hợp lệ (`entry_point` sai định dạng).
"""
from typing import List, Optional

from app.domain.entities import Connector
from app.domain.exceptions import (
    ConnectorCodeAlreadyExists,
    ConnectorInterfaceInvalid,
    ConnectorNotFound,
)
from app.domain.repositories import ConnectorRepository


class ConnectorService:
    def __init__(self, repo: ConnectorRepository):
        self._repo = repo

    def register(
        self,
        code: str,
        name: str,
        connector_type: str,
        version: str,
        entry_point: str,
        description: str = "",
    ) -> Connector:
        """Đăng ký bộ kết nối mới (plugin): hệ thống nạp mô-đun + kiểm tra
        giao diện trước khi lưu vào thư viện."""
        if self._repo.get_by_code(code):
            raise ConnectorCodeAlreadyExists(code)

        if not Connector.check_interface(entry_point):
            raise ConnectorInterfaceInvalid(entry_point)

        connector = Connector(
            id=None,
            code=code.strip(),
            name=name.strip(),
            connector_type=connector_type,
            version=version.strip(),
            entry_point=entry_point.strip(),
            description=(description or "").strip(),
            interface_status="PASSED",
            is_active=True,
            restart_count=0,
        )
        return self._repo.add(connector)

    def get(self, connector_id: int) -> Connector:
        connector = self._repo.get_by_id(connector_id)
        if connector is None:
            raise ConnectorNotFound(connector_id)
        return connector

    def list_connectors(
        self,
        only_active: bool = False,
        connector_type: Optional[str] = None,
    ) -> List[Connector]:
        """Xem danh sách bộ kết nối có sẵn (tệp/REST API/JDBC/SOAP)."""
        return self._repo.list(only_active=only_active, connector_type=connector_type)

    def update_version(self, connector_id: int, new_version: str) -> Connector:
        """Cập nhật phiên bản bộ kết nối -> hệ thống khởi động lại luân
        phiên tiến trình nhận sự kiện (tăng `restart_count`)."""
        connector = self.get(connector_id)
        connector.update_version(new_version)
        return self._repo.update(connector)

    def deactivate(self, connector_id: int) -> Connector:
        connector = self.get(connector_id)
        connector.deactivate()
        return self._repo.update(connector)

    def activate(self, connector_id: int) -> Connector:
        connector = self.get(connector_id)
        connector.activate()
        return self._repo.update(connector)
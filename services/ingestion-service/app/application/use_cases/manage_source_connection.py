"""Application layer — UC-017 (phần 1/2): Cấu hình kết nối nguồn (credentials).

Đối chiếu docs/use_cases.json id=17: actor "Quản trị Tích hợp, DBA".
Luồng nghiệp vụ:
1. Cấu hình connection (API/DB/File) -> hệ thống lưu thông tin xác thực
   đã mã hoá (không bao giờ lưu plaintext).
2. Kiểm thử kết nối -> hệ thống gọi thử (qua cổng `ConnectionTester`) và
   trả kết quả, đồng thời ghi nhận lại trạng thái/kết quả gần nhất.

Phần certificate/API key + cảnh báo hết hạn xem
`manage_credential_asset.py`.
"""
from datetime import datetime, timezone
import json
from typing import List, Optional

from app.domain.entities import SourceConnection
from app.domain.exceptions import (
    DataSourceNotFound,
    InvalidSourceConnection,
    SourceConnectionNotFound,
)
from app.domain.repositories import (
    ConnectionTester,
    CredentialCrypto,
    DataSourceRepository,
    SourceConnectionRepository,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SourceConnectionService:
    def __init__(
        self,
        connection_repo: SourceConnectionRepository,
        data_source_repo: DataSourceRepository,
        crypto: CredentialCrypto,
        tester: ConnectionTester,
    ):
        self._connections = connection_repo
        self._data_sources = data_source_repo
        self._crypto = crypto
        self._tester = tester

    def configure(
        self,
        data_source_id: int,
        connection_type: str,
        config: dict,
        credentials: dict,
    ) -> SourceConnection:
        """Cấu hình connection (API/DB/File): hệ thống lưu thông tin xác
        thực đã mã hoá."""
        if self._data_sources.get_by_id(data_source_id) is None:
            raise DataSourceNotFound(data_source_id)

        try:
            connection = SourceConnection(
                id=None,
                data_source_id=data_source_id,
                connection_type=connection_type,
                config=config or {},
            )
        except ValueError as exc:
            raise InvalidSourceConnection(str(exc)) from exc

        connection.encrypted_credentials = self._encrypt_credentials(credentials or {})
        return self._connections.add(connection)

    def update_config(
        self,
        connection_id: int,
        config: dict,
        credentials: Optional[dict] = None,
    ) -> SourceConnection:
        """Sửa lại cấu hình connection hiện có; nếu có `credentials` mới thì
        mã hoá lại và ghi đè bản cũ."""
        connection = self.get(connection_id)
        connection.config = config or {}
        if credentials is not None:
            connection.encrypted_credentials = self._encrypt_credentials(credentials)
        return self._connections.update(connection)

    def _encrypt_credentials(self, credentials: dict) -> str:
        plaintext = json.dumps(credentials or {})
        return self._crypto.encrypt(plaintext)

    def _decrypt_credentials(self, connection: SourceConnection) -> dict:
        if not connection.encrypted_credentials:
            return {}
        plaintext = self._crypto.decrypt(connection.encrypted_credentials)
        return json.loads(plaintext) if plaintext else {}

    def get(self, connection_id: int) -> SourceConnection:
        connection = self._connections.get_by_id(connection_id)
        if connection is None:
            raise SourceConnectionNotFound(connection_id)
        return connection

    def list_connections(
        self,
        data_source_id: Optional[int] = None,
        connection_type: Optional[str] = None,
        only_active: bool = False,
    ) -> List[SourceConnection]:
        return self._connections.list(
            data_source_id=data_source_id,
            connection_type=connection_type,
            only_active=only_active,
        )

    def test_connection(self, connection_id: int) -> SourceConnection:
        """Kiểm thử kết nối: hệ thống gọi thử và trả kết quả."""
        connection = self.get(connection_id)
        credentials = self._decrypt_credentials(connection)
        success, message = self._tester.test(
            connection.connection_type, connection.config, credentials
        )
        connection.record_test_result(success, message, _utc_now_iso())
        return self._connections.update(connection)

    def deactivate(self, connection_id: int) -> SourceConnection:
        connection = self.get(connection_id)
        connection.deactivate()
        return self._connections.update(connection)

    def activate(self, connection_id: int) -> SourceConnection:
        connection = self.get(connection_id)
        connection.activate()
        return self._connections.update(connection)
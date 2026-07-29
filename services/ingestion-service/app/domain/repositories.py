"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities import Connector, CredentialAsset, DataSource, SourceConnection


class DataSourceRepository(ABC):
    """Repository cho UC-015: Đăng ký và quản lý nguồn dữ liệu."""

    @abstractmethod
    def add(self, data_source: DataSource) -> DataSource:
        ...

    @abstractmethod
    def get_by_id(self, data_source_id: int) -> Optional[DataSource]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[DataSource]:
        ...

    @abstractmethod
    def list(
        self,
        only_active: bool = False,
        source_system: Optional[str] = None,
    ) -> List[DataSource]:
        ...

    @abstractmethod
    def update(self, data_source: DataSource) -> DataSource:
        ...


class ConnectorRepository(ABC):
    """Repository cho UC-016: Quản lý thư viện bộ kết nối."""

    @abstractmethod
    def add(self, connector: Connector) -> Connector:
        ...

    @abstractmethod
    def get_by_id(self, connector_id: int) -> Optional[Connector]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Connector]:
        ...

    @abstractmethod
    def list(
        self,
        only_active: bool = False,
        connector_type: Optional[str] = None,
    ) -> List[Connector]:
        ...

    @abstractmethod
    def update(self, connector: Connector) -> Connector:
        ...


class SourceConnectionRepository(ABC):
    """Repository cho UC-017: Cấu hình kết nối nguồn."""

    @abstractmethod
    def add(self, connection: SourceConnection) -> SourceConnection:
        ...

    @abstractmethod
    def get_by_id(self, connection_id: int) -> Optional[SourceConnection]:
        ...

    @abstractmethod
    def list(
        self,
        data_source_id: Optional[int] = None,
        connection_type: Optional[str] = None,
        only_active: bool = False,
    ) -> List[SourceConnection]:
        ...

    @abstractmethod
    def update(self, connection: SourceConnection) -> SourceConnection:
        ...


class CredentialAssetRepository(ABC):
    """Repository cho UC-017: Quản lý certificate/API key + lịch luân chuyển."""

    @abstractmethod
    def add(self, asset: CredentialAsset) -> CredentialAsset:
        ...

    @abstractmethod
    def get_by_id(self, asset_id: int) -> Optional[CredentialAsset]:
        ...

    @abstractmethod
    def list(
        self,
        connection_id: Optional[int] = None,
        asset_type: Optional[str] = None,
        only_active: bool = False,
    ) -> List[CredentialAsset]:
        ...

    @abstractmethod
    def update(self, asset: CredentialAsset) -> CredentialAsset:
        ...


class CredentialCrypto(ABC):
    """Cổng mã hoá/giải mã thông tin xác thực trước khi lưu CSDL (UC-017)."""

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        ...

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        ...


class ConnectionTester(ABC):
    """Cổng gọi thử kết nối tới nguồn (API/DB/File) (UC-017)."""

    @abstractmethod
    def test(self, connection_type: str, config: dict, credentials: dict) -> tuple:
        """Trả về (success: bool, message: str)."""
        ...


class CredentialAlertSender(ABC):
    """Cổng gửi cảnh báo (qua Alertmanager) trước khi credential hết hạn (UC-017)."""

    @abstractmethod
    def send_expiry_alert(
        self,
        asset_type: str,
        connection_id: int,
        expires_at: str,
        days_remaining: int,
    ) -> tuple:
        """Trả về (sent: bool, message: str)."""
        ...
"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities import (
    Connector,
    CredentialAsset,
    CriticalField,
    DataSource,
    Dataset,
    IngestionRun,
    ScheduledTask,
    SchemaVersion,
    SourceConnection,
)


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

class DatasetRepository(ABC):
    """Repository cho UC-018 bước 1-2: Định nghĩa tập dữ liệu + lược đồ,
    khoá chính + chiến lược phân mảnh (lưu vào `dataset_catalog`)."""

    @abstractmethod
    def add(self, dataset: Dataset) -> Dataset:
        ...

    @abstractmethod
    def get_by_id(self, dataset_id: int) -> Optional[Dataset]:
        ...

    @abstractmethod
    def get_by_code(self, data_source_id: int, code: str) -> Optional[Dataset]:
        ...

    @abstractmethod
    def list(
        self,
        data_source_id: Optional[int] = None,
        only_active: bool = False,
    ) -> List[Dataset]:
        ...

    @abstractmethod
    def update(self, dataset: Dataset) -> Dataset:
        ...


class CriticalFieldRepository(ABC):
    """Repository cho UC-018 bước 3: Khai báo trường bắt buộc (NOT NULL)
    (lưu vào `critical_fields`)."""

    @abstractmethod
    def replace_for_dataset(self, dataset_id: int, field_names: List[str]) -> List[CriticalField]:
        """Thay toàn bộ danh sách trường bắt buộc hiện có của 1 dataset
        bằng danh sách mới (idempotent)."""
        ...

    @abstractmethod
    def list_for_dataset(self, dataset_id: int) -> List[CriticalField]:
        ...


class SchemaVersionRepository(ABC):
    """Repository cho UC-018 bước 4: Đăng ký vào Schema Registry — hệ
    thống quản lý phiên bản lược đồ."""

    @abstractmethod
    def add(self, schema_version: SchemaVersion) -> SchemaVersion:
        ...

    @abstractmethod
    def list_for_dataset(self, dataset_id: int) -> List[SchemaVersion]:
        ...

    @abstractmethod
    def get_by_version(self, dataset_id: int, version: int) -> Optional[SchemaVersion]:
        ...


class ScheduledTaskRepository(ABC):
    """Repository cho UC-019: Cấu hình tác vụ điều phối."""

    @abstractmethod
    def add(self, task: ScheduledTask) -> ScheduledTask:
        ...

    @abstractmethod
    def get_by_id(self, task_id: int) -> Optional[ScheduledTask]:
        ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[ScheduledTask]:
        ...

    @abstractmethod
    def list(
        self,
        dataset_id: Optional[int] = None,
        only_enabled: bool = False,
    ) -> List[ScheduledTask]:
        ...

    @abstractmethod
    def update(self, task: ScheduledTask) -> ScheduledTask:
        ...


class IngestionRunRepository(ABC):
    """Repository cho UC-020: Xem lịch đầy đủ dữ liệu + lịch sử chạy
    (bảng nghiệp vụ "ingestion.runs")."""

    @abstractmethod
    def add(self, run: IngestionRun) -> IngestionRun:
        ...

    @abstractmethod
    def get_by_id(self, run_id: int) -> Optional[IngestionRun]:
        ...

    @abstractmethod
    def update(self, run: IngestionRun) -> IngestionRun:
        ...

    @abstractmethod
    def list(
        self,
        dataset_id: Optional[int] = None,
        scheduled_task_id: Optional[int] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[IngestionRun]:
        """Lọc theo dataset/tác vụ điều phối/trạng thái/khoảng thời gian
        (`date_from`/`date_to` so sánh trên `started_at`, định dạng
        ISO-8601, dùng cho cả lịch sử chạy lẫn heatmap lịch dữ liệu)."""
        ...

    @abstractmethod
    def find_active_retry(self, run_id: int) -> Optional[IngestionRun]:
        """UC-021: tìm 1 phiên RETRY đang RUNNING gắn `retry_of_run_id ==
        run_id` (nếu có). Dùng làm khoá chống trùng khi kích hoạt Bộ điều
        phối chạy lại — không cho phép 2 lượt chạy lại cùng lúc cho cùng 1
        phiên gốc."""
        ...

    @abstractmethod
    def list_retries(self, run_id: int) -> List[IngestionRun]:
        """UC-021: liệt kê toàn bộ các phiên đã từng chạy lại (RETRY) của
        1 phiên gốc `run_id`, mới nhất trước — dùng để xem lịch sử chạy lại."""
        ...


class IngestionRetryExecutor(ABC):
    """Cổng kích hoạt Bộ điều phối (Orchestrator) chạy lại 1 phiên ingest lỗi
    (UC-021). Triển khai thật sẽ gọi API/queue của Bộ điều phối để thực thi
    lại pipeline ingest cho `dataset_id` của phiên gốc; ở đây chỉ khai báo
    hợp đồng, xem `app/infrastructure/retry_executor.py` cho bản NoOp
    dùng cho dev/test."""

    @abstractmethod
    def execute_retry(self, original_run: IngestionRun) -> dict:
        """Thực thi lại phiên ingest cho phiên gốc `original_run`. Trả về
        dict gồm: status (SUCCESS/FAILED/PARTIAL), records_read,
        records_loaded, records_failed, control_totals (dict), error_message."""
        ...
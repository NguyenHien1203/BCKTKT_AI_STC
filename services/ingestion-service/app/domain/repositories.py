"""Repository interfaces (ports) — implement ở infrastructure layer."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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
    TabmisIntakeRowError,
    TabmisIntakeSession,
    TemplateValidationResult,
    VanBanIntake,
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

class FileStorage(ABC):
    """Cổng lưu trữ tệp nhị phân (UC-022 lưu tệp gốc TABMIS vào MinIO).

    Implement thật (MinIO qua thư viện `minio`) hoặc giả (lưu đĩa cục bộ
    cho dev/test) đặt ở `infrastructure/file_storage.py` — domain/
    application không phụ thuộc trực tiếp vào MinIO SDK.
    """

    @abstractmethod
    def upload(self, key: str, content: bytes, content_type: str) -> None:
        ...

    @abstractmethod
    def download(self, key: str) -> bytes:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...


class ExcelTemplateValidator(ABC):
    """Cổng sinh biểu mẫu Excel chuẩn + kiểm tra tệp tải lên đúng biểu mẫu
    (UC-022). Implement thật dùng `openpyxl` — xem
    `infrastructure/template_validator.py`.
    """

    @abstractmethod
    def build_template(self, columns: List[str]) -> bytes:
        """Sinh nội dung tệp .xlsx với dòng tiêu đề là `columns`."""
        ...

    @abstractmethod
    def validate(self, content: bytes, expected_columns: List[str]) -> TemplateValidationResult:
        """Đọc dòng tiêu đề + đếm số dòng dữ liệu của tệp `content`, so
        sánh với `expected_columns` (lấy từ lược đồ dataset)."""
        ...

    @abstractmethod
    def validate_rows(
        self,
        content: bytes,
        schema_fields: List[Dict[str, Any]],
        critical_field_names: List[str],
    ) -> List[Dict[str, Any]]:
        """UC-023 bước 2: đọc từng dòng dữ liệu của tệp `content` (bỏ dòng
        tiêu đề), đối chiếu từng ô với lược đồ dataset (`schema_fields`,
        mỗi phần tử `{"name","data_type",...}`) + danh sách trường bắt
        buộc `critical_field_names` (UC-018 bước 3). Trả về danh sách dict
        `{"row_number": int, "field_name": str, "message": str}` mô tả
        từng dòng/trường sai (thiếu trường bắt buộc hoặc sai kiểu dữ liệu).
        Chỉ nên gọi khi `validate()` ở trên đã xác định tệp đúng biểu mẫu
        (đủ cột)."""
        ...


class TabmisIntakeSessionRepository(ABC):
    """Repository cho UC-022: Tiếp nhận file thủ công TABMIS (upload)."""

    @abstractmethod
    def add(self, session: TabmisIntakeSession) -> TabmisIntakeSession:
        ...

    @abstractmethod
    def update(self, session: TabmisIntakeSession) -> TabmisIntakeSession:
        """UC-023 bước 3: cập nhật phiên tiếp nhận sau khi sửa + tải lại
        tệp đã chỉnh (hệ thống kiểm tra lại)."""
        ...

    @abstractmethod
    def get_by_id(self, session_id: int) -> Optional[TabmisIntakeSession]:
        ...

    @abstractmethod
    def list(
        self,
        dataset_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[TabmisIntakeSession]:
        ...


class TabmisIntakeRowErrorRepository(ABC):
    """Repository cho UC-023: các dòng sai của 1 phiên tiếp nhận TABMIS."""

    @abstractmethod
    def replace_for_session(
        self, session_id: int, errors: List[TabmisIntakeRowError]
    ) -> List[TabmisIntakeRowError]:
        """Xoá toàn bộ lỗi dòng cũ của `session_id` (nếu có, vd sau khi tải
        lại tệp đã sửa) rồi lưu danh sách lỗi dòng mới."""
        ...

    @abstractmethod
    def list_for_session(self, session_id: int) -> List[TabmisIntakeRowError]:
        ...


class VanBanIntakeRepository(ABC):
    """Repository cho UC-024: Tiếp nhận thủ công văn bản từ QLVBĐH (bảng
    `staging.stg_van_ban`)."""

    @abstractmethod
    def add(self, intake: VanBanIntake) -> VanBanIntake:
        ...

    @abstractmethod
    def get_by_id(self, intake_id: int) -> Optional[VanBanIntake]:
        ...

    @abstractmethod
    def get_by_so_ky_hieu(
        self, data_source_id: int, so_ky_hieu: str
    ) -> Optional[VanBanIntake]:
        """Dùng để khử trùng lặp (bước 3, UC-024): tìm văn bản đã tiếp nhận
        trước đó của cùng nguồn dữ liệu với cùng `so_ky_hieu`."""
        ...

    @abstractmethod
    def list(
        self,
        data_source_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[VanBanIntake]:
        ...


class EventPublisher(ABC):
    """Cổng phát sự kiện bất đồng bộ (UC-024 bước 4: kích hoạt sự kiện
    `ocr.requested`; xem ARCHITECTURE.md mục 3 — giao tiếp bất đồng bộ qua
    RabbitMQ/Celery giữa `ingestion-service` và `data-quality-service`).

    Implement thật (RabbitMQ) hoặc giả (ghi log cho dev/test) đặt ở
    `infrastructure/event_publisher.py` — domain/application không phụ
    thuộc trực tiếp vào thư viện message broker.
    """

    @abstractmethod
    def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        ...
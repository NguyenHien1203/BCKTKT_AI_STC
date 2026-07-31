class DomainError(Exception):
    """Base class cho lỗi nghiệp vụ."""

    code = "DOMAIN_ERROR"


class DataSourceCodeAlreadyExists(DomainError):
    code = "DATA_SOURCE_CODE_EXISTS"

    def __init__(self, code_value: str):
        super().__init__(f"Mã nguồn '{code_value}' đã tồn tại")


class DataSourceNotFound(DomainError):
    code = "DATA_SOURCE_NOT_FOUND"

    def __init__(self, data_source_id: int):
        super().__init__(f"Không tìm thấy nguồn dữ liệu id={data_source_id}")


class InvalidDataSource(DomainError):
    code = "INVALID_DATA_SOURCE"

    def __init__(self, message: str):
        super().__init__(message)


class ConnectorCodeAlreadyExists(DomainError):
    code = "CONNECTOR_CODE_EXISTS"

    def __init__(self, code_value: str):
        super().__init__(f"Mã bộ kết nối '{code_value}' đã tồn tại")


class ConnectorNotFound(DomainError):
    code = "CONNECTOR_NOT_FOUND"

    def __init__(self, connector_id: int):
        super().__init__(f"Không tìm thấy bộ kết nối id={connector_id}")


class ConnectorInterfaceInvalid(DomainError):
    code = "CONNECTOR_INTERFACE_INVALID"

    def __init__(self, entry_point: str):
        super().__init__(
            f"Kiểm tra giao diện thất bại cho mô-đun plugin '{entry_point}' — "
            "entry_point phải theo định dạng 'package.module:ClassName'"
        )


class SourceConnectionNotFound(DomainError):
    code = "SOURCE_CONNECTION_NOT_FOUND"

    def __init__(self, connection_id: int):
        super().__init__(f"Không tìm thấy cấu hình kết nối id={connection_id}")


class InvalidSourceConnection(DomainError):
    code = "INVALID_SOURCE_CONNECTION"

    def __init__(self, message: str):
        super().__init__(message)


class CredentialAssetNotFound(DomainError):
    code = "CREDENTIAL_ASSET_NOT_FOUND"

    def __init__(self, asset_id: int):
        super().__init__(f"Không tìm thấy certificate/API key id={asset_id}")


class InvalidCredentialAsset(DomainError):
    code = "INVALID_CREDENTIAL_ASSET"

    def __init__(self, message: str):
        super().__init__(message)

class DatasetCodeAlreadyExists(DomainError):
    code = "DATASET_CODE_EXISTS"

    def __init__(self, code_value: str, data_source_id: int):
        super().__init__(
            f"Mã tập dữ liệu '{code_value}' đã tồn tại cho nguồn dữ liệu id={data_source_id}"
        )


class DatasetNotFound(DomainError):
    code = "DATASET_NOT_FOUND"

    def __init__(self, dataset_id: int):
        super().__init__(f"Không tìm thấy tập dữ liệu id={dataset_id}")


class InvalidDataset(DomainError):
    code = "INVALID_DATASET"

    def __init__(self, message: str):
        super().__init__(message)


class SchemaVersionNotFound(DomainError):
    code = "SCHEMA_VERSION_NOT_FOUND"

    def __init__(self, dataset_id: int, version: int):
        super().__init__(
            f"Không tìm thấy phiên bản lược đồ version={version} của tập dữ liệu id={dataset_id}"
        )


class ScheduledTaskCodeAlreadyExists(DomainError):
    code = "SCHEDULED_TASK_CODE_EXISTS"

    def __init__(self, code_value: str):
        super().__init__(f"Mã tác vụ điều phối '{code_value}' đã tồn tại")


class ScheduledTaskNotFound(DomainError):
    code = "SCHEDULED_TASK_NOT_FOUND"

    def __init__(self, task_id: int):
        super().__init__(f"Không tìm thấy tác vụ điều phối id={task_id}")


class InvalidScheduledTask(DomainError):
    code = "INVALID_SCHEDULED_TASK"

    def __init__(self, message: str):
        super().__init__(message)


class IngestionRunNotFound(DomainError):
    code = "INGESTION_RUN_NOT_FOUND"

    def __init__(self, run_id: int):
        super().__init__(f"Không tìm thấy phiên ingest id={run_id}")


class InvalidIngestionRun(DomainError):
    code = "INVALID_INGESTION_RUN"

    def __init__(self, message: str):
        super().__init__(message)


class IngestionRunNotFailed(DomainError):
    """UC-021: chỉ được chạy lại phiên đang ở trạng thái FAILED."""

    code = "INGESTION_RUN_NOT_FAILED"

    def __init__(self, run_id: int, status: str):
        super().__init__(
            f"Phiên id={run_id} đang ở trạng thái '{status}', chỉ được chạy lại "
            "phiên ở trạng thái FAILED"
        )


class IngestionRunRetryInProgress(DomainError):
    """UC-021: khoá chống trùng — không cho phép kích hoạt chạy lại khi đã có
    1 phiên chạy lại (RETRY) khác của cùng phiên gốc đang RUNNING."""

    code = "INGESTION_RUN_RETRY_IN_PROGRESS"

    def __init__(self, run_id: int, active_retry_run_id: int):
        super().__init__(
            f"Phiên id={run_id} đã có 1 lượt chạy lại (id={active_retry_run_id}) "
            "đang thực thi — vui lòng đợi hoàn tất trước khi chạy lại tiếp"
        )

class DatasetSourceSystemMismatch(DomainError):
    """UC-022: dataset dùng để tiếp nhận TABMIS phải thuộc nguồn có
    `source_system == 'TABMIS'`."""

    code = "DATASET_SOURCE_SYSTEM_MISMATCH"

    def __init__(self, dataset_id: int, expected_source_system: str):
        super().__init__(
            f"Tập dữ liệu id={dataset_id} không thuộc hệ thống nguồn "
            f"'{expected_source_system}'"
        )


class InvalidTabmisIntakeUpload(DomainError):
    code = "INVALID_TABMIS_INTAKE_UPLOAD"

    def __init__(self, message: str):
        super().__init__(message)


class TabmisIntakeSessionNotFound(DomainError):
    code = "TABMIS_INTAKE_SESSION_NOT_FOUND"

    def __init__(self, session_id: int):
        super().__init__(f"Không tìm thấy phiên tiếp nhận TABMIS id={session_id}")


class DataSourceSystemMismatch(DomainError):
    """UC-024: nguồn dữ liệu dùng để tiếp nhận văn bản phải thuộc hệ thống
    nguồn `QLVBDH`."""

    code = "DATA_SOURCE_SYSTEM_MISMATCH"

    def __init__(self, data_source_id: int, expected_source_system: str):
        super().__init__(
            f"Nguồn dữ liệu id={data_source_id} không thuộc hệ thống nguồn "
            f"'{expected_source_system}'"
        )


class InvalidVanBanIntakeUpload(DomainError):
    code = "INVALID_VAN_BAN_INTAKE_UPLOAD"

    def __init__(self, message: str):
        super().__init__(message)


class VanBanIntakeNotFound(DomainError):
    code = "VAN_BAN_INTAKE_NOT_FOUND"

    def __init__(self, intake_id: int):
        super().__init__(f"Không tìm thấy văn bản tiếp nhận id={intake_id}")


class IncrementalSyncSourceSystemNotSupported(DomainError):
    """UC-025: chỉ áp dụng đồng bộ tăng dần cho các nguồn MISA/QL_GIA/PMSTT."""

    code = "INCREMENTAL_SYNC_SOURCE_SYSTEM_NOT_SUPPORTED"

    def __init__(self, source_system: str, supported: tuple):
        super().__init__(
            f"Đồng bộ tăng dần từ API/DB không áp dụng cho hệ thống nguồn "
            f"'{source_system}', chỉ áp dụng cho {supported}"
        )


class IncrementalSyncConnectionNotConfigured(DomainError):
    """UC-025: chưa cấu hình kết nối API/DB cho nguồn (vd MISA khi nhà cung
    cấp chưa cho phép kết nối API)."""

    code = "INCREMENTAL_SYNC_CONNECTION_NOT_CONFIGURED"

    def __init__(self, data_source_id: int):
        super().__init__(
            f"Nguồn dữ liệu id={data_source_id} chưa có cấu hình kết nối "
            "API/DB đang hoạt động (nhà cung cấp chưa cho phép kết nối hoặc "
            "chưa cấu hình ở UC-017) — không thể đồng bộ tăng dần"
        )


class IncrementalSyncAlreadyRunning(DomainError):
    """UC-025: khoá chống trùng — không cho phép 2 phiên đồng bộ tăng dần
    cùng chạy song song cho cùng 1 tập dữ liệu."""

    code = "INCREMENTAL_SYNC_ALREADY_RUNNING"

    def __init__(self, dataset_id: int, running_run_id: int):
        super().__init__(
            f"Tập dữ liệu id={dataset_id} đang có 1 phiên đồng bộ tăng dần "
            f"khác (id={running_run_id}) chạy — vui lòng đợi hoàn tất"
        )


class SchemaNotRegisteredForCheck(DomainError):
    """UC-026: chưa đăng ký lược đồ nào vào Schema Registry (UC-018 bước 4)
    nên chưa có gì để so sánh."""

    code = "SCHEMA_NOT_REGISTERED_FOR_CHECK"

    def __init__(self, dataset_id: int):
        super().__init__(
            f"Tập dữ liệu id={dataset_id} chưa đăng ký lược đồ nào vào "
            "Schema Registry (UC-018 bước 4) — không có lược đồ đã đăng ký "
            "để đối chiếu"
        )


class SchemaRegistryCheckNotFound(DomainError):
    code = "SCHEMA_REGISTRY_CHECK_NOT_FOUND"

    def __init__(self, check_id: int):
        super().__init__(f"Không tìm thấy lượt kiểm tra Schema Registry id={check_id}")


class InvalidSchemaRegistryCheck(DomainError):
    code = "INVALID_SCHEMA_REGISTRY_CHECK"

    def __init__(self, message: str):
        super().__init__(message)

class IntakeReconciliationNotFound(DomainError):
    code = "INTAKE_RECONCILIATION_NOT_FOUND"

    def __init__(self, reconciliation_id: int):
        super().__init__(f"Khong tim thay phien doi soat id={reconciliation_id}")


class InvalidIntakeReconciliation(DomainError):
    code = "INVALID_INTAKE_RECONCILIATION"

    def __init__(self, message: str):
        super().__init__(message)


class IntakeReconciliationAlreadyClosed(DomainError):
    """UC-027: phien doi soat da dong, khong the danh dau phat hien moi
    hoac dong lai lan nua."""

    code = "INTAKE_RECONCILIATION_ALREADY_CLOSED"

    def __init__(self, reconciliation_id: int):
        super().__init__(f"Phien doi soat id={reconciliation_id} da dong truoc do")


class IntakeReconciliationHasUnresolvedFindings(DomainError):
    """UC-027: chi duoc dong phien doi soat khi khong con phat hien
    thieu/sai nao o trang thai OPEN (dieu kien "dat yeu cau")."""

    code = "INTAKE_RECONCILIATION_HAS_UNRESOLVED_FINDINGS"

    def __init__(self, reconciliation_id: int, open_finding_count: int):
        super().__init__(
            f"Phien doi soat id={reconciliation_id} chua dat yeu cau: con "
            f"{open_finding_count} phat hien thieu/sai chua duoc xu ly xong"
        )


class IntakeReconciliationFindingNotFound(DomainError):
    code = "INTAKE_RECONCILIATION_FINDING_NOT_FOUND"

    def __init__(self, reconciliation_id: int, finding_index: int):
        super().__init__(
            f"Khong tim thay phat hien index={finding_index} trong phien doi soat "
            f"id={reconciliation_id}"
        )
"""Domain entities cho ingestion-service."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional


@dataclass
class DataSource:
    """Nguồn dữ liệu được đăng ký để tiếp nhận/đồng bộ (UC-015).

    `source_system` chỉ được là 1 trong 5 hệ thống nguồn theo BCKTKT:
    TABMIS, QLVBDH, MISA, QL_GIA, PMSTT. `code` là mã nguồn do Quản trị
    Tích hợp tự đặt, duy nhất toàn hệ thống.
    """

    SOURCE_SYSTEMS = ("TABMIS", "QLVBDH", "MISA", "QL_GIA", "PMSTT")
    SENSITIVITY_LEVELS = ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET")

    id: Optional[int]
    code: str
    name: str
    source_system: str
    provider: str
    owner: str
    sensitivity_level: str = "INTERNAL"
    is_active: bool = True

    def __post_init__(self) -> None:
        self._validate_code(self.code)
        self._validate_name(self.name)
        self._validate_source_system(self.source_system)
        self._validate_sensitivity_level(self.sensitivity_level)

    @staticmethod
    def _validate_code(code: str) -> None:
        if not code or not code.strip():
            raise ValueError("Mã nguồn không được để trống")

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Tên nguồn không được để trống")

    @classmethod
    def _validate_source_system(cls, source_system: str) -> None:
        if source_system not in cls.SOURCE_SYSTEMS:
            raise ValueError(
                f"Hệ thống nguồn '{source_system}' không hợp lệ, "
                f"phải là 1 trong {cls.SOURCE_SYSTEMS}"
            )

    @classmethod
    def _validate_sensitivity_level(cls, sensitivity_level: str) -> None:
        if sensitivity_level not in cls.SENSITIVITY_LEVELS:
            raise ValueError(f"Mức nhạy cảm '{sensitivity_level}' không hợp lệ")

    def update_info(self, provider: str, owner: str, sensitivity_level: str) -> None:
        """Sửa thông tin nguồn: nhà cung cấp, chủ sở hữu, mức nhạy cảm."""
        self._validate_sensitivity_level(sensitivity_level)
        if not provider or not provider.strip():
            raise ValueError("Nhà cung cấp không được để trống")
        if not owner or not owner.strip():
            raise ValueError("Chủ sở hữu không được để trống")
        self.provider = provider.strip()
        self.owner = owner.strip()
        self.sensitivity_level = sensitivity_level

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class Connector:
    """Bộ kết nối (plugin) trong thư viện bộ kết nối (UC-016).

    `connector_type` chỉ được là 1 trong 4 loại theo BCKTKT: FILE
    (tệp), REST_API, JDBC, SOAP. `entry_point` là đường dẫn mô-đun
    plugin (định dạng `package.module:ClassName`) — dùng để mô
    phỏng bước "hệ thống nạp mô-đun + kiểm tra giao diện" khi đăng
    ký bộ kết nối mới.
    """

    CONNECTOR_TYPES = ("FILE", "REST_API", "JDBC", "SOAP")
    INTERFACE_STATUSES = ("PASSED", "FAILED")

    id: Optional[int]
    code: str
    name: str
    connector_type: str
    version: str
    entry_point: str
    description: str = ""
    interface_status: str = "PASSED"
    is_active: bool = True
    restart_count: int = 0

    def __post_init__(self) -> None:
        self._validate_code(self.code)
        self._validate_name(self.name)
        self._validate_connector_type(self.connector_type)
        self._validate_version(self.version)

    @staticmethod
    def _validate_code(code: str) -> None:
        if not code or not code.strip():
            raise ValueError("Mã bộ kết nối không được để trống")

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Tên bộ kết nối không được để trống")

    @classmethod
    def _validate_connector_type(cls, connector_type: str) -> None:
        if connector_type not in cls.CONNECTOR_TYPES:
            raise ValueError(
                f"Loại bộ kết nối '{connector_type}' không hợp lệ, "
                f"phải là 1 trong {cls.CONNECTOR_TYPES}"
            )

    @staticmethod
    def _validate_version(version: str) -> None:
        if not version or not version.strip():
            raise ValueError("Phiên bản không được để trống")

    @staticmethod
    def check_interface(entry_point: str) -> bool:
        """Mô phỏng bước "nạp mô-đun + kiểm tra giao diện" khi đăng ký plugin.

        Giao diện hợp lệ khi `entry_point` theo định dạng
        `package.module:ClassName` (có dấu `.` phân tách module và
        dấu `:` phân tách tên lớp triển khai interface bộ kết nối).
        """
        if not entry_point or ":" not in entry_point:
            return False
        module_path, _, class_name = entry_point.partition(":")
        return bool(module_path.strip()) and "." in module_path and bool(class_name.strip())

    def update_version(self, new_version: str) -> None:
        """Cập nhật phiên bản bộ kết nối + tăng bộ đếm khởi động lại
        luân phiên tiến trình nhận sự kiện (rolling restart)."""
        self._validate_version(new_version)
        self.version = new_version.strip()
        self.restart_count += 1

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class SourceConnection:
    """Cấu hình kết nối tới nguồn dữ liệu (UC-017): API / DB / File.

    `config` chỉ chứa thông tin KHÔNG nhạy cảm (host, port, base_url,
    database, path...). Thông tin xác thực (username/password/api_key/
    token...) được mã hoá và lưu riêng ở `encrypted_credentials` (chuỗi
    đã mã hoá qua cổng `CredentialCrypto`) — domain layer không bao giờ
    giữ bản rõ (plaintext) sau khi mã hoá xong.
    """

    CONNECTION_TYPES = ("API", "DB", "FILE")
    TEST_STATUSES = ("UNTESTED", "SUCCESS", "FAILED")

    id: Optional[int]
    data_source_id: int
    connection_type: str
    config: Dict[str, Any] = field(default_factory=dict)
    encrypted_credentials: str = ""
    last_test_status: str = "UNTESTED"
    last_test_message: str = ""
    last_tested_at: Optional[str] = None
    is_active: bool = True

    def __post_init__(self) -> None:
        self._validate_data_source_id(self.data_source_id)
        self._validate_connection_type(self.connection_type)

    @staticmethod
    def _validate_data_source_id(data_source_id: int) -> None:
        if not data_source_id or data_source_id <= 0:
            raise ValueError("Phải chỉ định nguồn dữ liệu (data_source_id) hợp lệ")

    @classmethod
    def _validate_connection_type(cls, connection_type: str) -> None:
        if connection_type not in cls.CONNECTION_TYPES:
            raise ValueError(
                f"Loại kết nối '{connection_type}' không hợp lệ, "
                f"phải là 1 trong {cls.CONNECTION_TYPES}"
            )

    def record_test_result(self, success: bool, message: str, tested_at: str) -> None:
        """Ghi nhận kết quả sau khi hệ thống gọi thử kết nối."""
        self.last_test_status = "SUCCESS" if success else "FAILED"
        self.last_test_message = message
        self.last_tested_at = tested_at

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class CredentialAsset:
    """Certificate / API key gắn với 1 cấu hình kết nối (UC-017).

    Lưu lịch luân chuyển (`rotation_history`) mỗi lần certificate/API key
    được thay mới, phục vụ truy vết + làm căn cứ cảnh báo trước khi hết
    hạn (`expires_at`).
    """

    ASSET_TYPES = ("CERTIFICATE", "API_KEY")

    id: Optional[int]
    connection_id: int
    asset_type: str
    encrypted_value: str
    issued_at: str
    expires_at: str
    rotation_period_days: int = 90
    rotated_at: Optional[str] = None
    rotation_count: int = 0
    rotation_history: List[Dict[str, str]] = field(default_factory=list)
    is_active: bool = True

    def __post_init__(self) -> None:
        self._validate_connection_id(self.connection_id)
        self._validate_asset_type(self.asset_type)
        self._validate_expires_at(self.expires_at)

    @staticmethod
    def _validate_connection_id(connection_id: int) -> None:
        if not connection_id or connection_id <= 0:
            raise ValueError("Phải chỉ định cấu hình kết nối (connection_id) hợp lệ")

    @classmethod
    def _validate_asset_type(cls, asset_type: str) -> None:
        if asset_type not in cls.ASSET_TYPES:
            raise ValueError(
                f"Loại tài sản xác thực '{asset_type}' không hợp lệ, "
                f"phải là 1 trong {cls.ASSET_TYPES}"
            )

    @staticmethod
    def _validate_expires_at(expires_at: str) -> None:
        if not expires_at:
            raise ValueError("Ngày hết hạn (expires_at) không được để trống")
        try:
            datetime.fromisoformat(expires_at)
        except ValueError as exc:
            raise ValueError(
                "Ngày hết hạn (expires_at) phải theo định dạng ISO-8601"
            ) from exc

    def rotate(self, new_encrypted_value: str, new_expires_at: str, rotated_at: str) -> None:
        """Luân chuyển (rotate) certificate/API key: lưu bản cũ vào lịch sử
        luân chuyển rồi thay bằng bản mới."""
        self._validate_expires_at(new_expires_at)
        self.rotation_history.append(
            {"rotated_at": rotated_at, "previous_expires_at": self.expires_at}
        )
        self.encrypted_value = new_encrypted_value
        self.expires_at = new_expires_at
        self.rotated_at = rotated_at
        self.rotation_count += 1

    def days_until_expiry(self, now: datetime) -> int:
        """Số ngày còn lại tới khi hết hạn (âm nếu đã hết hạn)."""
        expires = datetime.fromisoformat(self.expires_at)
        if expires.tzinfo is None and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        elif expires.tzinfo is not None and now.tzinfo is None:
            expires = expires.replace(tzinfo=None)
        return (expires - now).days

    def is_expiring_within(self, days_ahead: int, now: datetime) -> bool:
        """True nếu còn hoạt động và sẽ hết hạn trong vòng `days_ahead` ngày tới."""
        return self.is_active and self.days_until_expiry(now) <= days_ahead

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True

@dataclass
class Dataset:
    """Tập dữ liệu (dataset) của 1 nguồn dữ liệu, kèm lược đồ (UC-018).

    Bước 1 luồng nghiệp vụ "Định nghĩa tập dữ liệu + lược đồ" tương ứng
    với việc khởi tạo entity này: `schema_fields` là danh sách trường của
    lược đồ, mỗi phần tử dạng
    `{"name": str, "data_type": str, "nullable": bool, "description": str}`.

    Bước 2 "Khai báo khoá chính + chiến lược phân mảnh" tương ứng
    `configure_partitioning()`.

    Bước 4 "Đăng ký vào Schema Registry" tương ứng `register_schema_version()`
    — chỉ được phép khi đã khai báo khoá chính (đã qua bước 2), và mỗi lần
    đăng ký hệ thống tăng `current_schema_version` thêm 1 (quản lý phiên bản
    lược đồ, xem thêm `SchemaVersion`).
    """

    DATA_TYPES = (
        "STRING",
        "INTEGER",
        "BIGINT",
        "DECIMAL",
        "BOOLEAN",
        "DATE",
        "DATETIME",
        "JSON",
    )
    PARTITION_STRATEGIES = ("NONE", "RANGE", "LIST", "HASH")

    id: Optional[int]
    data_source_id: int
    code: str
    name: str
    description: str = ""
    schema_fields: List[Dict[str, Any]] = field(default_factory=list)
    primary_key: List[str] = field(default_factory=list)
    partition_strategy: str = "NONE"
    partition_column: Optional[str] = None
    current_schema_version: int = 0
    is_active: bool = True

    def __post_init__(self) -> None:
        self._validate_data_source_id(self.data_source_id)
        self._validate_code(self.code)
        self._validate_name(self.name)
        self._validate_schema_fields(self.schema_fields)

    @staticmethod
    def _validate_data_source_id(data_source_id: int) -> None:
        if not data_source_id or data_source_id <= 0:
            raise ValueError("Phải chỉ định nguồn dữ liệu (data_source_id) hợp lệ")

    @staticmethod
    def _validate_code(code: str) -> None:
        if not code or not code.strip():
            raise ValueError("Mã tập dữ liệu không được để trống")

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Tên tập dữ liệu không được để trống")

    @classmethod
    def _validate_schema_fields(cls, schema_fields: List[Dict[str, Any]]) -> None:
        if not schema_fields:
            raise ValueError("Lược đồ (schema_fields) không được để trống")
        seen_names = set()
        for item in schema_fields:
            name = (item or {}).get("name", "")
            data_type = (item or {}).get("data_type", "")
            if not name or not str(name).strip():
                raise ValueError("Mỗi trường trong lược đồ phải có 'name'")
            if name in seen_names:
                raise ValueError(f"Trường '{name}' bị khai báo trùng lặp trong lược đồ")
            seen_names.add(name)
            if data_type not in cls.DATA_TYPES:
                raise ValueError(
                    f"Kiểu dữ liệu '{data_type}' của trường '{name}' không hợp lệ, "
                    f"phải là 1 trong {cls.DATA_TYPES}"
                )

    def field_names(self) -> set:
        return {item["name"] for item in self.schema_fields}

    def define_schema(self, schema_fields: List[Dict[str, Any]]) -> None:
        """Định nghĩa lại lược đồ (trước khi đăng ký phiên bản mới vào
        Schema Registry). Nếu khoá chính/cột phân mảnh hiện có không còn
        tồn tại trong lược đồ mới thì phải khai báo lại (bước 2)."""
        self._validate_schema_fields(schema_fields)
        self.schema_fields = schema_fields
        new_names = self.field_names()
        if not set(self.primary_key).issubset(new_names):
            self.primary_key = []
        if self.partition_column and self.partition_column not in new_names:
            self.partition_column = None
            self.partition_strategy = "NONE"

    def configure_partitioning(
        self,
        primary_key: List[str],
        partition_strategy: str,
        partition_column: Optional[str] = None,
    ) -> None:
        """Khai báo khoá chính + chiến lược phân mảnh (bước 2)."""
        if not primary_key:
            raise ValueError("Phải khai báo ít nhất 1 trường làm khoá chính")
        field_names = self.field_names()
        for pk_field in primary_key:
            if pk_field not in field_names:
                raise ValueError(
                    f"Trường khoá chính '{pk_field}' không tồn tại trong lược đồ"
                )
        if partition_strategy not in self.PARTITION_STRATEGIES:
            raise ValueError(
                f"Chiến lược phân mảnh '{partition_strategy}' không hợp lệ, "
                f"phải là 1 trong {self.PARTITION_STRATEGIES}"
            )
        if partition_strategy != "NONE":
            if not partition_column:
                raise ValueError(
                    "Phải chỉ định cột phân mảnh (partition_column) khi chiến lược "
                    "phân mảnh khác NONE"
                )
            if partition_column not in field_names:
                raise ValueError(
                    f"Cột phân mảnh '{partition_column}' không tồn tại trong lược đồ"
                )
        else:
            partition_column = None

        self.primary_key = list(primary_key)
        self.partition_strategy = partition_strategy
        self.partition_column = partition_column

    def register_schema_version(self) -> int:
        """Đăng ký vào Schema Registry: hệ thống tăng phiên bản lược đồ lên 1.

        Yêu cầu đã khai báo khoá chính (bước 2) trước khi đăng ký."""
        if not self.primary_key:
            raise ValueError(
                "Phải khai báo khoá chính + chiến lược phân mảnh trước khi "
                "đăng ký vào Schema Registry"
            )
        self.current_schema_version += 1
        return self.current_schema_version

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class CriticalField:
    """Trường bắt buộc (NOT NULL) của 1 tập dữ liệu (UC-018, bước 3).

    Lưu vào `metadata.critical_fields` theo yêu cầu nghiệp vụ (BCKTKT);
    trong triển khai hiện tại được lưu ở bảng `critical_fields` cùng
    schema Postgres với các bảng khác của `ingestion-service` — xem
    ADR-001 trong ARCHITECTURE.md (1 schema Postgres / service).
    """

    id: Optional[int]
    dataset_id: int
    field_name: str

    def __post_init__(self) -> None:
        if not self.dataset_id or self.dataset_id <= 0:
            raise ValueError("Phải chỉ định tập dữ liệu (dataset_id) hợp lệ")
        if not self.field_name or not self.field_name.strip():
            raise ValueError("Tên trường bắt buộc (field_name) không được để trống")


@dataclass
class SchemaVersion:
    """1 phiên bản lược đồ đã đăng ký vào Schema Registry (UC-018, bước 4).

    `schema_snapshot` lưu lại toàn bộ trạng thái lược đồ tại thời điểm
    đăng ký (schema_fields, primary_key, partition_strategy,
    partition_column, critical_fields) để tra cứu lịch sử phiên bản.
    """

    id: Optional[int]
    dataset_id: int
    version: int
    schema_snapshot: Dict[str, Any]
    registered_at: str

    def __post_init__(self) -> None:
        if not self.dataset_id or self.dataset_id <= 0:
            raise ValueError("Phải chỉ định tập dữ liệu (dataset_id) hợp lệ")
        if not self.version or self.version <= 0:
            raise ValueError("Phiên bản lược đồ (version) phải > 0")


@dataclass
class SchemaRegistryCheck:
    """1 lượt kiểm tra Schema Registry (UC-026): trước khi phân tích, so
    sánh lược đồ nguồn (`incoming_fields`, đọc được từ dữ liệu vừa tiếp
    nhận) với lược đồ đã đăng ký gần nhất của tập dữ liệu (`SchemaVersion`
    của UC-018 bước 4).

    Kết quả (`status`):
    - `COMPATIBLE`: lược đồ chỉ thay đổi bổ sung (thêm trường mới) — hệ
      thống chuyển tiếp (cho phép bước phân tích tiếp theo chạy) + ghi
      nhận thay đổi (`added_fields`).
    - `BREAKING`: lược đồ phá vỡ tương thích (xoá/mất trường đã đăng ký,
      hoặc đổi kiểu dữ liệu 1 trường đã có) — hệ thống DỪNG quy trình xử
      lý (`allowed=False`) + cảnh báo Quản trị Tích hợp.
    """

    STATUSES = ("COMPATIBLE", "BREAKING")

    id: Optional[int]
    dataset_id: int
    registered_version: int
    incoming_fields: List[Dict[str, Any]]
    status: str
    added_fields: List[str] = field(default_factory=list)
    removed_fields: List[str] = field(default_factory=list)
    changed_type_fields: List[Dict[str, str]] = field(default_factory=list)
    message: str = ""
    checked_at: str = ""
    ingestion_run_id: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.dataset_id or self.dataset_id <= 0:
            raise ValueError("Phải chỉ định tập dữ liệu (dataset_id) hợp lệ")
        if self.status not in self.STATUSES:
            raise ValueError(
                f"Trạng thái kiểm tra '{self.status}' không hợp lệ, phải là 1 "
                f"trong {self.STATUSES}"
            )

    @property
    def allowed(self) -> bool:
        """`True` nếu hệ thống được phép chuyển tiếp sang bước phân tích
        tiếp theo (lược đồ tương thích), `False` nếu phải dừng lại."""
        return self.status == "COMPATIBLE"


@dataclass
class TemplateValidationResult:
    """Kết quả kiểm tra 1 tệp Excel tải lên so với biểu mẫu chuẩn (UC-022).

    `found_columns` là các cột đọc được ở dòng tiêu đề của tệp; `missing_columns`
    là các cột bắt buộc theo lược đồ dataset nhưng không có trong tệp;
    `row_count` là số dòng dữ liệu (không tính dòng tiêu đề) — dùng làm 1 phần
    của tổng kiểm soát (control totals).
    """

    valid: bool
    message: str
    found_columns: List[str]
    missing_columns: List[str]
    row_count: int


@dataclass
class TabmisIntakeSession:
    """1 phiên tiếp nhận file thủ công TABMIS qua upload (UC-022).

    Luồng nghiệp vụ (docs/use_cases.json id=22):
    1. Cán bộ nộp file tải biểu mẫu Excel chuẩn (sinh từ lược đồ dataset
       TABMIS tương ứng) -> hệ thống trả về tệp biểu mẫu chuẩn.
    2. Cán bộ tải tệp đã điền lên -> hệ thống lưu tệp gốc (raw) vào MinIO,
       kiểm tra tệp đúng biểu mẫu (`TemplateValidationResult`) và tính tổng
       kiểm soát (control totals: số dòng đọc được, số cột khớp/thiếu...).
    3. Hệ thống tạo 1 phiên tiếp nhận mới (entity này).
    4. Hệ thống ghi 1 bản ghi tương ứng vào `ingestion.runs` — liên kết qua
       `ingestion_run_id`.

    `status` = "RECEIVED" khi tệp đúng biểu mẫu (đủ cột bắt buộc), hoặc
    "TEMPLATE_INVALID" khi tệp thiếu cột/không đọc được — trong cả 2
    trường hợp hệ thống vẫn tạo phiên + ghi `ingestion.runs` (trạng thái
    SUCCESS/FAILED tương ứng) để có thể tra cứu lại. UC-023 (Xem trạng
    thái + sửa lỗi intake TABMIS) sẽ mở rộng máy trạng thái này thêm các
    bước xem lỗi dòng dữ liệu + tải lại tệp đã sửa.
    """

    # UC-023 mở rộng máy trạng thái:
    # - RECEIVED: tệp đúng biểu mẫu, không có dòng nào sai.
    # - TEMPLATE_INVALID: tệp sai biểu mẫu (thiếu cột bắt buộc/không đọc được).
    # - ROW_ERRORS: tệp đúng biểu mẫu nhưng có ít nhất 1 dòng dữ liệu sai
    #   (thiếu trường bắt buộc hoặc sai kiểu dữ liệu) -> cần xem chi tiết lỗi
    #   dòng rồi sửa + tải lại tệp.
    # - CORRECTED: đã tải lại tệp đã sửa (bước 3 UC-023) và lần kiểm tra lại
    #   này không còn lỗi (biểu mẫu đúng + không còn dòng sai).
    STATUSES = ("RECEIVED", "TEMPLATE_INVALID", "ROW_ERRORS", "CORRECTED")

    # Máy trạng thái UC-023 bước 1 "Xem trạng thái tiếp nhận: hệ thống hiển
    # thị máy trạng thái" — với mỗi trạng thái, các hành động còn hợp lệ.
    STATE_TRANSITIONS: ClassVar[Dict[str, List[str]]] = {
        "TEMPLATE_INVALID": ["VIEW_ROW_ERRORS", "REUPLOAD"],
        "ROW_ERRORS": ["VIEW_ROW_ERRORS", "REUPLOAD"],
        "RECEIVED": ["REUPLOAD"],
        "CORRECTED": ["REUPLOAD"],
    }

    id: Optional[int]
    dataset_id: int
    file_name: str
    raw_object_key: str
    status: str
    control_totals: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    uploaded_by: str = ""
    uploaded_at: str = ""
    ingestion_run_id: Optional[int] = None

    def __post_init__(self) -> None:
        self._validate_dataset_id(self.dataset_id)
        self._validate_file_name(self.file_name)
        self._validate_raw_object_key(self.raw_object_key)
        self._validate_status(self.status)

    def allowed_actions(self) -> List[str]:
        """UC-023 bước 1: các hành động hợp lệ từ trạng thái hiện tại."""
        return self.STATE_TRANSITIONS.get(self.status, [])


    @staticmethod
    def _validate_dataset_id(dataset_id: int) -> None:
        if not dataset_id or dataset_id <= 0:
            raise ValueError("Phải chỉ định tập dữ liệu (dataset_id) hợp lệ")

    @staticmethod
    def _validate_file_name(file_name: str) -> None:
        if not file_name or not file_name.strip():
            raise ValueError("Tên tệp (file_name) không được để trống")

    @staticmethod
    def _validate_raw_object_key(raw_object_key: str) -> None:
        if not raw_object_key or not raw_object_key.strip():
            raise ValueError(
                "Đường dẫn lưu trữ tệp gốc trên MinIO (raw_object_key) không được để trống"
            )

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.STATUSES:
            raise ValueError(f"Trạng thái phiên tiếp nhận '{status}' không hợp lệ")


@dataclass
class TabmisIntakeRowError:
    """1 dòng dữ liệu sai trong 1 phiên tiếp nhận TABMIS (UC-023, bước 2
    "Xem chi tiết lỗi dòng: hệ thống hiển thị các dòng sai").

    `row_number` đếm từ 1, ứng với dòng dữ liệu trong tệp Excel (không tính
    dòng tiêu đề). `field_name` là tên cột (trường) bị sai theo lược đồ
    dataset; `message` mô tả lỗi (thiếu trường bắt buộc hoặc sai kiểu dữ
    liệu so với `data_type` khai báo ở UC-018).
    """

    id: Optional[int]
    session_id: int
    row_number: int
    field_name: str
    message: str

    def __post_init__(self) -> None:
        if not self.session_id or self.session_id <= 0:
            raise ValueError("Phải chỉ định phiên tiếp nhận (session_id) hợp lệ")
        if not self.row_number or self.row_number <= 0:
            raise ValueError("Số thứ tự dòng (row_number) phải > 0")
        if not self.field_name or not self.field_name.strip():
            raise ValueError("Tên trường (field_name) không được để trống")
        if not self.message or not self.message.strip():
            raise ValueError("Nội dung lỗi (message) không được để trống")


@dataclass
class VanBanIntake:
    """1 văn bản được tiếp nhận thủ công từ QLVBĐH theo định kỳ (UC-024),
    lưu vào `staging.stg_van_ban`.

    Luồng nghiệp vụ (docs/use_cases.json id=24):
    1. Cán bộ nộp văn bản tải biểu mẫu chuẩn và nhập siêu dữ liệu văn bản
       (số ký hiệu, loại văn bản, trích yếu, ngày ban hành, đơn vị ban
       hành) -> hệ thống lưu vào `staging.stg_van_ban`.
    2. Cán bộ tải tệp PDF/bản quét đính kèm -> hệ thống lưu vào MinIO
       (bucket `raw-documents`).
    3. Hệ thống khử trùng lặp theo `so_ky_hieu`: nếu đã tồn tại 1 văn bản
       khác cùng `so_ky_hieu` thì bỏ qua bản trùng (không tạo bản ghi mới,
       không lưu lại tệp, không phát sự kiện) -> trả về bản ghi đã có kèm
       `status = "DUPLICATE_SKIPPED"`.
    4. Nếu không trùng: hệ thống kích hoạt sự kiện `ocr.requested` (để
       data-quality-service UC-29+ nhận và OCR/phân tích văn bản) ->
       `status = "RECEIVED"`.
    """

    STATUSES = ("RECEIVED", "DUPLICATE_SKIPPED")

    id: Optional[int]
    data_source_id: int
    so_ky_hieu: str
    loai_van_ban: str
    trich_yeu: str
    ngay_ban_hanh: str
    don_vi_ban_hanh: str
    raw_object_key: str
    status: str = "RECEIVED"
    ocr_event_published: bool = False
    uploaded_by: str = ""
    uploaded_at: str = ""

    def __post_init__(self) -> None:
        self._validate_data_source_id(self.data_source_id)
        self._validate_so_ky_hieu(self.so_ky_hieu)
        self._validate_raw_object_key(self.raw_object_key)
        self._validate_status(self.status)

    @staticmethod
    def _validate_data_source_id(data_source_id: int) -> None:
        if not data_source_id or data_source_id <= 0:
            raise ValueError("Phải chỉ định nguồn dữ liệu (data_source_id) hợp lệ")

    @staticmethod
    def _validate_so_ky_hieu(so_ky_hieu: str) -> None:
        if not so_ky_hieu or not so_ky_hieu.strip():
            raise ValueError("Số ký hiệu văn bản (so_ky_hieu) không được để trống")

    @staticmethod
    def _validate_raw_object_key(raw_object_key: str) -> None:
        if not raw_object_key or not raw_object_key.strip():
            raise ValueError(
                "Đường dẫn lưu trữ tệp đính kèm trên MinIO (raw_object_key) không được để trống"
            )

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.STATUSES:
            raise ValueError(f"Trạng thái tiếp nhận văn bản '{status}' không hợp lệ")


@dataclass
class ScheduledTask:
    """Tác vụ điều phối (scheduler job) đồng bộ 1 tập dữ liệu (UC-019).

    Luồng nghiệp vụ:
    1. Cấu hình tác vụ điều phối (lịch cron, đầy đủ/tăng dần, chính sách
       thử lại) -> hệ thống lưu (`__post_init__` / `update_config`).
    2. Bật/tắt tác vụ điều phối -> hệ thống cập nhật trạng thái tác vụ
       điều phối (`enable`/`disable`).
    3. Hệ thống điều phối (Bộ điều phối, xem UC-025) cập nhật trạng thái
       thực thi tác vụ (`record_run_status`) mỗi khi chạy xong 1 phiên.

    `sync_mode` = "FULL" (đồng bộ đầy đủ) hoặc "INCREMENTAL" (đồng bộ
    tăng dần). `retry_backoff` quyết định cách tính khoảng chờ giữa các
    lần thử lại: NONE (không thử lại), FIXED (khoảng chờ cố định),
    EXPONENTIAL (tăng dần theo cấp số nhân).
    """

    SYNC_MODES = ("FULL", "INCREMENTAL")
    RETRY_BACKOFFS = ("NONE", "FIXED", "EXPONENTIAL")
    RUN_STATUSES = ("IDLE", "RUNNING", "SUCCESS", "FAILED")

    id: Optional[int]
    dataset_id: int
    code: str
    name: str
    sync_mode: str = "FULL"
    cron_expression: str = "0 0 * * *"
    retry_max_attempts: int = 3
    retry_delay_seconds: int = 60
    retry_backoff: str = "FIXED"
    is_enabled: bool = True
    status: str = "IDLE"
    last_run_at: Optional[str] = None
    last_run_message: str = ""

    def __post_init__(self) -> None:
        self._validate_dataset_id(self.dataset_id)
        self._validate_code(self.code)
        self._validate_name(self.name)
        self._validate_sync_mode(self.sync_mode)
        self._validate_cron_expression(self.cron_expression)
        self._validate_retry_policy(
            self.retry_max_attempts, self.retry_delay_seconds, self.retry_backoff
        )
        self._validate_status(self.status)

    @staticmethod
    def _validate_dataset_id(dataset_id: int) -> None:
        if not dataset_id or dataset_id <= 0:
            raise ValueError("Phải chỉ định tập dữ liệu (dataset_id) hợp lệ")

    @staticmethod
    def _validate_code(code: str) -> None:
        if not code or not code.strip():
            raise ValueError("Mã tác vụ điều phối không được để trống")

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Tên tác vụ điều phối không được để trống")

    @classmethod
    def _validate_sync_mode(cls, sync_mode: str) -> None:
        if sync_mode not in cls.SYNC_MODES:
            raise ValueError(
                f"Chế độ đồng bộ '{sync_mode}' không hợp lệ, "
                f"phải là 1 trong {cls.SYNC_MODES}"
            )

    @staticmethod
    def _validate_cron_expression(cron_expression: str) -> None:
        """Kiểm tra định dạng cron cơ bản: 5 trường cách nhau bởi khoảng
        trắng (phút giờ ngày tháng thứ). Không diễn giải ngữ nghĩa lịch,
        chỉ đảm bảo đúng cấu trúc trước khi lưu."""
        if not cron_expression or not cron_expression.strip():
            raise ValueError("Lịch cron không được để trống")
        parts = cron_expression.strip().split()
        if len(parts) != 5:
            raise ValueError(
                "Lịch cron không hợp lệ, phải có đúng 5 trường "
                "(phút giờ ngày-trong-tháng tháng ngày-trong-tuần), "
                f"nhận được '{cron_expression}'"
            )

    @classmethod
    def _validate_retry_policy(
        cls, retry_max_attempts: int, retry_delay_seconds: int, retry_backoff: str
    ) -> None:
        if retry_max_attempts < 0:
            raise ValueError("Số lần thử lại tối đa (retry_max_attempts) không được âm")
        if retry_delay_seconds < 0:
            raise ValueError("Khoảng chờ thử lại (retry_delay_seconds) không được âm")
        if retry_backoff not in cls.RETRY_BACKOFFS:
            raise ValueError(
                f"Chính sách thử lại '{retry_backoff}' không hợp lệ, "
                f"phải là 1 trong {cls.RETRY_BACKOFFS}"
            )

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.RUN_STATUSES:
            raise ValueError(f"Trạng thái '{status}' không hợp lệ")

    def update_config(
        self,
        sync_mode: str,
        cron_expression: str,
        retry_max_attempts: int,
        retry_delay_seconds: int,
        retry_backoff: str,
    ) -> None:
        """Cấu hình tác vụ điều phối: lịch cron, đầy đủ/tăng dần, chính
        sách thử lại. Hệ thống lưu."""
        self._validate_sync_mode(sync_mode)
        self._validate_cron_expression(cron_expression)
        self._validate_retry_policy(retry_max_attempts, retry_delay_seconds, retry_backoff)
        self.sync_mode = sync_mode
        self.cron_expression = cron_expression.strip()
        self.retry_max_attempts = retry_max_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.retry_backoff = retry_backoff

    def enable(self) -> None:
        """Bật tác vụ điều phối. Hệ thống cập nhật trạng thái tác vụ
        điều phối."""
        self.is_enabled = True

    def disable(self) -> None:
        """Tắt tác vụ điều phối. Hệ thống cập nhật trạng thái tác vụ
        điều phối."""
        self.is_enabled = False

    def record_run_status(self, status: str, message: str, run_at: str) -> None:
        """Hệ thống cập nhật trạng thái tác vụ điều phối sau khi Bộ điều
        phối thực thi 1 phiên (RUNNING/SUCCESS/FAILED)."""
        self._validate_status(status)
        self.status = status
        self.last_run_message = message
        self.last_run_at = run_at


@dataclass
class IngestionRun:
    """1 phiên chạy ingest (ingestion run) của 1 tập dữ liệu (UC-020,
    dùng bởi UC-021 chạy lại phiên lỗi và UC-025 đồng bộ tăng dần).

    Lưu vào bảng nghiệp vụ "ingestion.runs" (đặt tên `ingestion_runs`
    trong schema `staging` — xem ghi chú ADR-001 ở models.py). Mỗi phiên
    gắn với 1 `dataset_id` (bắt buộc), có thể gắn thêm 1 `scheduled_task_id`
    nếu phiên do Bộ điều phối tự động kích hoạt.

    Luồng nghiệp vụ UC-020:
    1. "Xem lịch sử chạy": hệ thống truy vấn danh sách các `IngestionRun`
       đã ghi nhận (lọc theo dataset/tác vụ/trạng thái/khoảng thời gian).
    2. "Xem lịch đầy đủ dữ liệu (kỳ thiếu dữ liệu)": hệ thống tổng hợp các
       phiên theo từng ngày trong khoảng thời gian để vẽ heatmap — ngày
       không có phiên nào SUCCESS được coi là "kỳ thiếu dữ liệu".
    3. "Xem chi tiết phiên cụ thể": hệ thống hiển thị `log_entries` +
       `control_totals` (tổng kiểm soát: số bản ghi đọc được/nạp thành
       công/lỗi, checksum...) của 1 `IngestionRun`.
    """

    TRIGGERS = ("MANUAL", "SCHEDULED", "RETRY")
    SYNC_MODES = ("FULL", "INCREMENTAL")
    STATUSES = ("RUNNING", "SUCCESS", "FAILED", "PARTIAL")
    LOG_LEVELS = ("INFO", "WARNING", "ERROR")

    id: Optional[int]
    dataset_id: int
    scheduled_task_id: Optional[int]
    trigger: str
    sync_mode: str
    started_at: str
    status: str = "RUNNING"
    finished_at: Optional[str] = None
    records_read: int = 0
    records_loaded: int = 0
    records_failed: int = 0
    control_totals: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    log_entries: List[Dict[str, str]] = field(default_factory=list)
    retry_of_run_id: Optional[int] = None
    """UC-021: nếu phiên này là 1 lần "chạy lại" của 1 phiên lỗi trước đó,
    trường này trỏ tới `id` của phiên gốc bị lỗi. `trigger` khi đó luôn là
    "RETRY". Dùng để: (1) hiển thị lịch sử chạy lại của 1 phiên, (2) làm
    khoá chống trùng — không cho phép có 2 phiên RETRY cùng đang RUNNING
    cho cùng 1 phiên gốc tại 1 thời điểm."""

    def __post_init__(self) -> None:
        self._validate_dataset_id(self.dataset_id)
        self._validate_trigger(self.trigger)
        self._validate_sync_mode(self.sync_mode)
        self._validate_status(self.status)
        if not self.started_at:
            raise ValueError("Thời điểm bắt đầu (started_at) không được để trống")
        if self.retry_of_run_id is not None and self.trigger != "RETRY":
            raise ValueError("Phiên gắn retry_of_run_id phải có trigger='RETRY'")

    @staticmethod
    def _validate_dataset_id(dataset_id: int) -> None:
        if not dataset_id or dataset_id <= 0:
            raise ValueError("Phải chỉ định tập dữ liệu (dataset_id) hợp lệ")

    @classmethod
    def _validate_trigger(cls, trigger: str) -> None:
        if trigger not in cls.TRIGGERS:
            raise ValueError(
                f"Kiểu kích hoạt phiên '{trigger}' không hợp lệ, "
                f"phải là 1 trong {cls.TRIGGERS}"
            )

    @classmethod
    def _validate_sync_mode(cls, sync_mode: str) -> None:
        if sync_mode not in cls.SYNC_MODES:
            raise ValueError(
                f"Chế độ đồng bộ '{sync_mode}' không hợp lệ, phải là 1 trong {cls.SYNC_MODES}"
            )

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.STATUSES:
            raise ValueError(f"Trạng thái phiên '{status}' không hợp lệ")

    @classmethod
    def _validate_log_level(cls, level: str) -> None:
        if level not in cls.LOG_LEVELS:
            raise ValueError(f"Mức log '{level}' không hợp lệ, phải là 1 trong {cls.LOG_LEVELS}")

    def append_log(self, level: str, message: str, timestamp: str) -> None:
        """Ghi thêm 1 dòng log vào phiên (dùng khi phiên đang RUNNING)."""
        self._validate_log_level(level)
        if not message or not message.strip():
            raise ValueError("Nội dung log (message) không được để trống")
        self.log_entries.append({"timestamp": timestamp, "level": level, "message": message})

    def complete(
        self,
        status: str,
        finished_at: str,
        records_read: int,
        records_loaded: int,
        records_failed: int,
        control_totals: Dict[str, Any],
        error_message: str = "",
    ) -> None:
        """Kết thúc phiên: hệ thống ghi nhận trạng thái cuối (SUCCESS/
        FAILED/PARTIAL) + tổng kiểm soát (control totals)."""
        if status not in ("SUCCESS", "FAILED", "PARTIAL"):
            raise ValueError(
                "Trạng thái kết thúc phiên phải là 1 trong (SUCCESS, FAILED, PARTIAL)"
            )
        if records_read < 0 or records_loaded < 0 or records_failed < 0:
            raise ValueError("Số bản ghi (records_*) không được âm")
        self.status = status
        self.finished_at = finished_at
        self.records_read = records_read
        self.records_loaded = records_loaded
        self.records_failed = records_failed
        self.control_totals = control_totals or {}
        self.error_message = error_message


@dataclass
class IncrementalRecord:
    """1 bản ghi mới/thay đổi mà bộ kết nối lấy được từ nguồn API/DB khi
    truy vấn tăng dần theo `updated_at` (UC-025, bước 2 "Bộ kết nối lấy dữ
    liệu mới/thay đổi").

    `record_id` là định danh bản ghi tại hệ thống nguồn (dùng để log/truy
    vết, KHÔNG dùng làm khoá chính ở kho tổng hợp — việc đó thuộc UC-029
    "Phân tích dữ liệu có cấu trúc" chạy sau khi nhận sự kiện
    `parsing.requested`). `updated_at` là mốc thời gian cập nhật tại nguồn
    (ISO-8601), dùng để tính điểm kiểm tra (checkpoint) mới cho lần đồng bộ
    tiếp theo. `payload` là dữ liệu thô (chưa phân tích/ánh xạ) của bản ghi.
    """

    record_id: str
    updated_at: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.record_id or not str(self.record_id).strip():
            raise ValueError("record_id không được để trống")
        if not self.updated_at or not str(self.updated_at).strip():
            raise ValueError("updated_at không được để trống")

@dataclass
class IntakeReconciliation:
    """1 phien doi soat cua 1 phien tiep nhan TABMIS (UC-027).

    Luong nghiep vu (docs/use_cases.json id=27), actor "Quan tri Tich hop,
    Phu trach Du lieu":
    1. "Chon phien can doi soat" -> he thong mo 1 `IntakeReconciliation`
       gan voi `session_id` (`TabmisIntakeSession` cua UC-022/023). Neu
       phien do da co 1 luot doi soat dang mo (`OPEN`) thi dung lai, khong
       tao trung.
    2. "He thong hien thi tong kiem soat" -> chup lai (snapshot)
       `control_totals` cua phien tiep nhan tai thoi diem mo doi soat, de
       Quan tri Tich hop/Phu trach Du lieu doi chieu so lieu.
    3. "Danh dau phat hien thieu/sai" -> `mark_finding()`: ghi nhan 1 phat
       hien (thieu du lieu `MISSING` hoac sai lech du lieu `INCORRECT`) so
       voi tong kiem soat.
    4. "He thong luu" -> phat hien duoc luu vao `findings` (persist o
       repository ngay sau khi goi `mark_finding()`).
    5. "Dong phien doi soat dat yeu cau" -> `close()`: chi cho phep dong
       khi KHONG con phat hien nao o trang thai `OPEN` (moi thieu/sai da
       duoc xu ly xong `RESOLVED`) -- day la dieu kien "dat yeu cau".
    6. "He thong cap nhat trang thai" -> `status` chuyen tu `OPEN` sang
       `CLOSED` (+ `closed_by`, `closed_at`, `close_note`).
    """

    STATUSES = ("OPEN", "CLOSED")
    FINDING_TYPES = ("MISSING", "INCORRECT")
    FINDING_STATUSES = ("OPEN", "RESOLVED")

    id: Optional[int]
    session_id: int
    status: str = "OPEN"
    control_totals: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    reconciled_by: str = ""
    opened_at: str = ""
    closed_by: str = ""
    closed_at: Optional[str] = None
    close_note: str = ""

    def __post_init__(self) -> None:
        self._validate_session_id(self.session_id)
        self._validate_status(self.status)

    @staticmethod
    def _validate_session_id(session_id: int) -> None:
        if not session_id or session_id <= 0:
            raise ValueError("Phai chi dinh phien tiep nhan (session_id) hop le")

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.STATUSES:
            raise ValueError(f"Trang thai phien doi soat '{status}' khong hop le")

    @property
    def is_open(self) -> bool:
        return self.status == "OPEN"

    def open_finding_count(self) -> int:
        """So phat hien thieu/sai chua duoc xu ly xong (`OPEN`)."""
        return len([f for f in self.findings if f.get("status") == "OPEN"])

    def mark_finding(
        self,
        finding_type: str,
        field_name: str,
        description: str,
        recorded_at: str,
    ) -> Dict[str, Any]:
        """Buoc 3-4: Danh dau phat hien thieu/sai -> he thong luu."""
        if not self.is_open:
            raise ValueError(
                f"Phien doi soat id={self.id} da dong, khong the danh dau phat hien moi"
            )
        if finding_type not in self.FINDING_TYPES:
            raise ValueError(
                f"Loai phat hien '{finding_type}' khong hop le, "
                f"phai la 1 trong {self.FINDING_TYPES}"
            )
        if not field_name or not field_name.strip():
            raise ValueError("Ten truong/muc phat hien (field_name) khong duoc de trong")
        if not description or not description.strip():
            raise ValueError("Noi dung phat hien (description) khong duoc de trong")
        finding = {
            "finding_type": finding_type,
            "field_name": field_name.strip(),
            "description": description.strip(),
            "status": "OPEN",
            "recorded_at": recorded_at,
            "resolved_at": None,
        }
        self.findings.append(finding)
        return finding

    def resolve_finding(self, finding_index: int, resolved_at: str) -> Dict[str, Any]:
        """Danh dau 1 phat hien da duoc xu ly xong (dieu kien de dong
        phien doi soat "dat yeu cau" o buoc 5)."""
        if finding_index < 0 or finding_index >= len(self.findings):
            raise ValueError(f"Khong tim thay phat hien thu tu index={finding_index}")
        finding = self.findings[finding_index]
        if finding.get("status") == "RESOLVED":
            raise ValueError(f"Phat hien index={finding_index} da duoc xu ly xong truoc do")
        finding["status"] = "RESOLVED"
        finding["resolved_at"] = resolved_at
        return finding

    def close(self, closed_by: str, close_note: str, closed_at: str) -> None:
        """Buoc 5-6: Dong phien doi soat dat yeu cau -> he thong cap nhat
        trang thai. Chi cho phep dong khi khong con phat hien nao `OPEN`."""
        if not self.is_open:
            raise ValueError(f"Phien doi soat id={self.id} da dong truoc do")
        if not closed_by or not closed_by.strip():
            raise ValueError("Phai cho biet nguoi dong phien doi soat (closed_by)")
        if self.open_finding_count() > 0:
            raise ValueError(
                "Phien doi soat chua dat yeu cau: con "
                f"{self.open_finding_count()} phat hien thieu/sai chua duoc xu ly xong"
            )
        self.status = "CLOSED"
        self.closed_by = closed_by.strip()
        self.closed_at = closed_at
        self.close_note = close_note or ""
@dataclass
class ReconciliationTicket:
    """1 ticket xử lý với chủ quản nguồn, phát sinh từ 1 phiên đối soát
    (`IntakeReconciliation`, UC-027) khi phát hiện thiếu/sai cần chủ quản
    nguồn xác nhận/xử lý (UC-028).

    Luồng nghiệp vụ (docs/use_cases.json id=28), actor "Quản trị Tích hợp":
    1. "Mở ticket xử lý với chủ quản nguồn" -> hệ thống lưu ticket +
       thông báo (mô phỏng bằng cờ `notified`).
    2. "Cập nhật tiến độ xử lý ticket" -> `add_progress()`: ghi 1 mốc tiến
       độ (`note`, `updated_by`), có thể kèm chuyển trạng thái
       OPEN -> IN_PROGRESS -> RESOLVED.
    3. "Hệ thống lưu lịch sử" -> mỗi lần cập nhật được lưu vào `history`.
    4. "Đóng ticket khi resolved" -> `close()`: chỉ cho phép đóng khi
       ticket đã ở trạng thái RESOLVED (đã xử lý xong với chủ quản nguồn).
    5. "Hệ thống cập nhật + ghi nhật ký" -> `status` chuyển sang `CLOSED`,
       kèm 1 mốc trong `history`.
    """

    STATUSES = ("OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED")

    id: Optional[int]
    reconciliation_id: int
    source_owner: str
    title: str
    description: str = ""
    status: str = "OPEN"
    history: List[Dict[str, Any]] = field(default_factory=list)
    opened_by: str = ""
    opened_at: str = ""
    notified: bool = False
    closed_by: str = ""
    closed_at: Optional[str] = None
    close_note: str = ""

    def __post_init__(self) -> None:
        self._validate_reconciliation_id(self.reconciliation_id)
        self._validate_source_owner(self.source_owner)
        self._validate_title(self.title)
        self._validate_status(self.status)

    @staticmethod
    def _validate_reconciliation_id(reconciliation_id: int) -> None:
        if not reconciliation_id or reconciliation_id <= 0:
            raise ValueError("Phải gắn ticket với 1 phiên đối soát (reconciliation_id) hợp lệ")

    @staticmethod
    def _validate_source_owner(source_owner: str) -> None:
        if not source_owner or not source_owner.strip():
            raise ValueError("Phải cho biết chủ quản nguồn (source_owner) xử lý ticket")

    @staticmethod
    def _validate_title(title: str) -> None:
        if not title or not title.strip():
            raise ValueError("Tiêu đề ticket (title) không được để trống")

    @classmethod
    def _validate_status(cls, status: str) -> None:
        if status not in cls.STATUSES:
            raise ValueError(f"Trạng thái ticket '{status}' không hợp lệ")

    @property
    def is_closed(self) -> bool:
        return self.status == "CLOSED"

    @property
    def is_resolved(self) -> bool:
        return self.status == "RESOLVED"

    def add_progress(
        self,
        note: str,
        updated_by: str,
        updated_at: str,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Bước 2-3: Cập nhật tiến độ xử lý ticket -> hệ thống lưu lịch sử.
        `status` (nếu có) chuyển trạng thái ticket sang OPEN/IN_PROGRESS/
        RESOLVED (không dùng để đóng ticket — dùng `close()` cho việc đó)."""
        if self.is_closed:
            raise ValueError(f"Ticket id={self.id} đã đóng, không thể cập nhật tiến độ")
        if not note or not note.strip():
            raise ValueError("Nội dung cập nhật tiến độ (note) không được để trống")
        if not updated_by or not updated_by.strip():
            raise ValueError("Phải cho biết người cập nhật tiến độ (updated_by)")
        if status is not None:
            if status not in ("OPEN", "IN_PROGRESS", "RESOLVED"):
                raise ValueError(
                    f"Trạng thái cập nhật '{status}' không hợp lệ, "
                    "phải là 1 trong ('OPEN', 'IN_PROGRESS', 'RESOLVED')"
                )
            self.status = status
        entry = {
            "note": note.strip(),
            "updated_by": updated_by.strip(),
            "status": self.status,
            "updated_at": updated_at,
        }
        self.history.append(entry)
        return entry

    def close(self, closed_by: str, close_note: str, closed_at: str) -> None:
        """Bước 4-5: Đóng ticket khi resolved -> hệ thống cập nhật trạng
        thái + ghi nhật ký. Chỉ cho phép đóng khi ticket đã RESOLVED."""
        if self.is_closed:
            raise ValueError(f"Ticket id={self.id} đã đóng trước đó")
        if not self.is_resolved:
            raise ValueError(
                f"Ticket id={self.id} chưa ở trạng thái RESOLVED, "
                "không thể đóng (cần cập nhật tiến độ sang RESOLVED trước)"
            )
        if not closed_by or not closed_by.strip():
            raise ValueError("Phải cho biết người đóng ticket (closed_by)")
        self.status = "CLOSED"
        self.closed_by = closed_by.strip()
        self.closed_at = closed_at
        self.close_note = (close_note or "").strip()
        self.history.append(
            {
                "note": self.close_note or "Đóng ticket",
                "updated_by": self.closed_by,
                "status": "CLOSED",
                "updated_at": closed_at,
            }
        )
        self.close_note = (close_note or "").strip()
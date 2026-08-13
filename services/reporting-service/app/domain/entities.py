"""Domain entities cho reporting-service.

UC-047 (Xem Bảng điều khiển điều hành): danh mục Bảng điều khiển được nhúng
từ Apache Superset + tuỳ chọn cá nhân "ghim bảng điều khiển yêu thích".

UC-049 (Chọn báo cáo theo mẫu + cấu hình bộ lọc): danh mục mẫu báo cáo
(report template) tra cứu từ Lớp ngữ nghĩa (chỉ tiêu UC-043) + trạng thái
bộ lọc (năm/đơn vị/lĩnh vực/kỳ) người dùng đã cấu hình cho từng mẫu, dùng
làm đầu vào cho UC-050 "Sinh + kết xuất báo cáo".
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Dashboard:
    """1 Bảng điều khiển trong danh mục, hiển thị (embed) từ Superset.

    `superset_dashboard_uid` là UID/slug của dashboard bên Superset, dùng để
    dựng `embed_url` (iframe nhúng). `category` tương ứng lĩnh vực nghiệp vụ
    (vd: "NGÂN SÁCH", "TÀI SẢN CÔNG", "ĐẦU TƯ CÔNG"...), dùng làm bộ lọc ở
    UC-048.
    """

    CATEGORIES = (
        "NGAN_SACH",
        "TAI_SAN_CONG",
        "DAU_TU_CONG",
        "GIA",
        "TONG_HOP",
    )

    id: Optional[int]
    code: str
    name: str
    description: str
    category: str
    superset_dashboard_uid: str
    embed_url: str
    is_active: bool = True
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        self._validate_code(self.code)
        self._validate_name(self.name)
        self._validate_category(self.category)
        self._validate_superset_uid(self.superset_dashboard_uid)

    @staticmethod
    def _validate_code(code: str) -> None:
        if not code or not code.strip():
            raise ValueError("Mã bảng điều khiển không được để trống")

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Tên bảng điều khiển không được để trống")

    @classmethod
    def _validate_category(cls, category: str) -> None:
        if category not in cls.CATEGORIES:
            raise ValueError(
                f"Lĩnh vực '{category}' không hợp lệ, phải là 1 trong {cls.CATEGORIES}"
            )

    @staticmethod
    def _validate_superset_uid(uid: str) -> None:
        if not uid or not uid.strip():
            raise ValueError("superset_dashboard_uid không được để trống")

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class DashboardKpi:
    """UC-048: 1 chỉ tiêu (KPI) thuộc 1 Bảng điều khiển — danh mục tối
    thiểu để hệ thống biết KPI nào có thể áp bộ lọc/xem chi tiết/so sánh
    cùng kỳ/giải thích bằng AI. Mã KPI (`code`) duy nhất trong phạm vi 1
    dashboard.
    """

    id: Optional[int]
    dashboard_id: int
    code: str
    name: str
    unit_of_measure: str
    higher_is_better: bool = True
    is_active: bool = True
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.code or not self.code.strip():
            raise ValueError("Mã KPI không được để trống")
        if not self.name or not self.name.strip():
            raise ValueError("Tên KPI không được để trống")

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class DashboardFilter:
    """UC-048 bước 1: bộ lọc áp cho Bảng điều khiển — năm, đơn vị, lĩnh vực.

    `org_unit_code`/`sector` có thể để trống (không lọc theo tiêu chí đó);
    `year` luôn bắt buộc vì mọi chỉ tiêu ngân sách/tài sản/giá đều gắn
    niên độ.
    """

    year: int
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None

    def __post_init__(self) -> None:
        if self.year < 1900 or self.year > 2100:
            raise ValueError("Năm áp bộ lọc không hợp lệ")


@dataclass
class KpiExplanation:
    """UC-048 bước cuối: kết quả "Yêu cầu AI giải thích KPI" — hệ thống gọi
    AI Bộ điều phối (ai-service) rồi lưu lại (append-only, phục vụ xem lại
    lịch sử giải thích đã yêu cầu cho 1 KPI theo từng bộ lọc)."""

    id: Optional[int]
    dashboard_id: int
    kpi_code: str
    year: int
    org_unit_code: Optional[str]
    sector: Optional[str]
    requested_by: int
    explanation: str
    model: str
    created_at: Optional[datetime] = None


@dataclass
class ReportTemplate:
    """UC-049: 1 mẫu báo cáo trong danh mục — mô tả cấu trúc cột (tra cứu
    từ Lớp ngữ nghĩa, xem UC-043) + các loại kỳ báo cáo mà mẫu này hỗ trợ.
    Dùng làm đầu vào cho bước "Sinh + kết xuất báo cáo" (UC-050).
    """

    CATEGORIES = Dashboard.CATEGORIES
    PERIOD_TYPES = ("THANG", "QUY", "NAM")

    id: Optional[int]
    code: str
    name: str
    description: str
    category: str
    columns: List[Dict[str, Any]] = field(default_factory=list)
    available_periods: List[str] = field(default_factory=lambda: ["NAM"])
    is_active: bool = True
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        self._validate_code(self.code)
        self._validate_name(self.name)
        self._validate_category(self.category)
        self._validate_columns(self.columns)
        self._validate_available_periods(self.available_periods)

    @staticmethod
    def _validate_code(code: str) -> None:
        if not code or not code.strip():
            raise ValueError("Mã mẫu báo cáo không được để trống")

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Tên mẫu báo cáo không được để trống")

    @classmethod
    def _validate_category(cls, category: str) -> None:
        if category not in cls.CATEGORIES:
            raise ValueError(
                f"Lĩnh vực '{category}' không hợp lệ, phải là 1 trong {cls.CATEGORIES}"
            )

    @staticmethod
    def _validate_columns(columns: List[Dict[str, Any]]) -> None:
        if not columns:
            raise ValueError("Mẫu báo cáo phải khai báo ít nhất 1 cột dữ liệu")
        for col in columns:
            if not isinstance(col, dict) or not str(col.get("field", "")).strip():
                raise ValueError("Mỗi cột phải có 'field' (tên trường) không rỗng")
            if not str(col.get("label", "")).strip():
                raise ValueError("Mỗi cột phải có 'label' (tiêu đề hiển thị) không rỗng")

    @classmethod
    def _validate_available_periods(cls, periods: List[str]) -> None:
        if not periods:
            raise ValueError("Mẫu báo cáo phải hỗ trợ ít nhất 1 loại kỳ báo cáo")
        for p in periods:
            if p not in cls.PERIOD_TYPES:
                raise ValueError(
                    f"Loại kỳ '{p}' không hợp lệ, phải là 1 trong {cls.PERIOD_TYPES}"
                )

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True


@dataclass
class ReportFilterConfig:
    """UC-049 bước 3: "Cấu hình bộ lọc (năm, đơn vị, lĩnh vực, kỳ)" — hệ
    thống lưu trạng thái theo từng người dùng cho từng mẫu báo cáo (1
    người dùng chỉ có 1 cấu hình đang lưu cho 1 mẫu — lưu lại đè lên cấu
    hình trước đó, giống bản nháp được ghi nhớ). UC-050 sẽ đọc lại cấu hình
    này để sinh báo cáo.
    """

    STATUSES = ("SAVED",)

    id: Optional[int]
    template_id: int
    user_id: int
    year: int
    period_type: str
    period_value: Optional[int] = None
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None
    status: str = "SAVED"
    saved_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.year < 1900 or self.year > 2100:
            raise ValueError("Năm áp bộ lọc không hợp lệ")
        if self.period_type not in ReportTemplate.PERIOD_TYPES:
            raise ValueError(
                f"Loại kỳ '{self.period_type}' không hợp lệ, phải là 1 trong "
                f"{ReportTemplate.PERIOD_TYPES}"
            )
        if self.period_type == "NAM":
            if self.period_value is not None:
                raise ValueError("Kỳ 'NAM' không cần giá trị kỳ (period_value phải để trống)")
        elif self.period_type == "THANG":
            if self.period_value is None or not (1 <= self.period_value <= 12):
                raise ValueError("Kỳ 'THANG' cần period_value từ 1 đến 12")
        elif self.period_type == "QUY":
            if self.period_value is None or not (1 <= self.period_value <= 4):
                raise ValueError("Kỳ 'QUY' cần period_value từ 1 đến 4")
        if self.status not in self.STATUSES:
            raise ValueError(f"Trạng thái '{self.status}' không hợp lệ")


@dataclass
class DashboardFavorite:
    """UC-047 bước cuối: "Ghim bảng điều khiển yêu thích" — hệ thống lưu vào
    tùy chọn cá nhân của người dùng (1 user có thể ghim nhiều dashboard,
    nhưng không ghim trùng 1 dashboard 2 lần)."""

    id: Optional[int]
    user_id: int
    dashboard_id: int
    pinned_at: Optional[datetime] = None


@dataclass
class GeneratedReportLog:
    """UC-050: Sinh + kết xuất báo cáo — nhật ký append-only mỗi lượt
    "Kết xuất PDF"/"Kết xuất Excel" (hệ thống trả file). Lưu lại đúng bộ
    lọc đã dùng (năm/đơn vị/lĩnh vực/kỳ) + số dòng dữ liệu kết xuất được,
    dùng để tra cứu lại lịch sử sinh báo cáo của người dùng."""

    FORMATS = ("PDF", "EXCEL")

    id: Optional[int]
    template_id: int
    user_id: int
    format: str
    year: int
    period_type: str
    period_value: Optional[int] = None
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None
    row_count: int = 0
    generated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.format not in self.FORMATS:
            raise ValueError(
                f"Định dạng kết xuất '{self.format}' không hợp lệ, phải là 1 trong {self.FORMATS}"
            )
        if self.year < 1900 or self.year > 2100:
            raise ValueError("Năm không hợp lệ")
        if self.period_type not in ReportTemplate.PERIOD_TYPES:
            raise ValueError(
                f"Loại kỳ '{self.period_type}' không hợp lệ, phải là 1 trong "
                f"{ReportTemplate.PERIOD_TYPES}"
            )

@dataclass
class ReportSchedule:
    """UC-051: "Cấu hình báo cáo theo lịch" — hệ thống lưu lịch (hàng
    ngày/hàng tuần/hàng tháng) để tự động sinh + gửi email báo cáo theo
    mẫu (UC-049/UC-050) cho danh sách người nhận (UC-051 bước cấu hình
    người nhận). Tác vụ định kỳ (cron) sẽ quét các lịch đang bật, tới hạn,
    rồi sinh + gửi email báo cáo — xem `ReportScheduleRunLog`.

    1 người dùng có thể có nhiều lịch cho cùng 1 mẫu báo cáo (khác giờ/tần
    suất), không giới hạn duy nhất như `ReportFilterConfig`.
    """

    FREQUENCIES = ("DAILY", "WEEKLY", "MONTHLY")
    FORMATS = ("PDF", "EXCEL")

    id: Optional[int]
    template_id: int
    user_id: int
    frequency: str
    time_of_day: str
    format: str = "PDF"
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    year: Optional[int] = None
    period_type: Optional[str] = None
    period_value: Optional[int] = None
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None
    is_active: bool = True
    last_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        self._validate_frequency(self.frequency)
        self._validate_format(self.format)
        self._validate_time_of_day(self.time_of_day)
        self._validate_period(self.year, self.period_type, self.period_value)
        if self.frequency == "WEEKLY":
            if self.day_of_week is None or not (0 <= self.day_of_week <= 6):
                raise ValueError(
                    "Lịch 'hàng tuần' cần day_of_week từ 0 (Thứ Hai) đến 6 (Chủ Nhật)"
                )
        elif self.day_of_week is not None:
            raise ValueError("Chỉ lịch 'hàng tuần' mới cần day_of_week")
        if self.frequency == "MONTHLY":
            if self.day_of_month is None or not (1 <= self.day_of_month <= 28):
                raise ValueError(
                    "Lịch 'hàng tháng' cần day_of_month từ 1 đến 28 "
                    "(giới hạn 28 để chạy đúng ở mọi tháng, kể cả tháng 2)"
                )
        elif self.day_of_month is not None:
            raise ValueError("Chỉ lịch 'hàng tháng' mới cần day_of_month")

    @classmethod
    def _validate_frequency(cls, frequency: str) -> None:
        if frequency not in cls.FREQUENCIES:
            raise ValueError(
                f"Tần suất lịch '{frequency}' không hợp lệ, phải là 1 trong {cls.FREQUENCIES}"
            )

    @classmethod
    def _validate_format(cls, fmt: str) -> None:
        if fmt not in cls.FORMATS:
            raise ValueError(
                f"Định dạng báo cáo '{fmt}' không hợp lệ, phải là 1 trong {cls.FORMATS}"
            )

    @staticmethod
    def _validate_time_of_day(time_of_day: str) -> None:
        if not time_of_day or not isinstance(time_of_day, str):
            raise ValueError("Giờ chạy (time_of_day) không được để trống")
        parts = time_of_day.split(":")
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            raise ValueError("Giờ chạy phải theo định dạng 'HH:MM' (vd: '07:30')")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Giờ chạy phải theo định dạng 'HH:MM' hợp lệ (00:00-23:59)")

    @staticmethod
    def _validate_period(
        year: Optional[int], period_type: Optional[str], period_value: Optional[int]
    ) -> None:
        """Bộ lọc dùng để sinh báo cáo theo lịch là tuỳ chọn — nếu để
        trống, mỗi lần chạy sẽ dùng lại cấu hình bộ lọc đã lưu ở UC-049
        (giống UC-050 khi không truyền bộ lọc trực tiếp)."""
        if year is None and period_type is None:
            return
        if year is None or period_type is None:
            raise ValueError(
                "Nếu khai báo bộ lọc riêng cho lịch thì phải truyền đủ cả year và period_type"
            )
        if year < 1900 or year > 2100:
            raise ValueError("Năm áp bộ lọc không hợp lệ")
        if period_type not in ReportTemplate.PERIOD_TYPES:
            raise ValueError(
                f"Loại kỳ '{period_type}' không hợp lệ, phải là 1 trong "
                f"{ReportTemplate.PERIOD_TYPES}"
            )

    def enable(self) -> None:
        self.is_active = True

    def disable(self) -> None:
        self.is_active = False

    def mark_run(self, run_at: datetime) -> None:
        self.last_run_at = run_at


@dataclass
class ReportScheduleRecipient:
    """UC-051 bước "Cấu hình người nhận (email)" — hệ thống lưu danh sách
    email nhận báo cáo cho 1 lịch (1 email không lặp lại trong cùng 1
    lịch)."""

    id: Optional[int]
    schedule_id: int
    email: str
    added_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        self._validate_email(self.email)

    @staticmethod
    def _validate_email(email: str) -> None:
        if not email or not email.strip():
            raise ValueError("Email người nhận không được để trống")
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError(f"Email người nhận '{email}' không hợp lệ")
        local, _, domain = email.partition("@")
        if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError(f"Email người nhận '{email}' không hợp lệ")


@dataclass
class ReportScheduleRunLog:
    """UC-051: nhật ký append-only mỗi lần "Tác vụ định kỳ (cron)" chạy —
    hệ thống tự động sinh + gửi email báo cáo theo lịch. Dùng để tra cứu
    lại các lần đã chạy (thành công/thất bại) của 1 lịch."""

    STATUSES = ("SUCCESS", "FAILED")

    id: Optional[int]
    schedule_id: int
    status: str
    recipients_count: int = 0
    row_count: int = 0
    message: str = ""
    run_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.status not in self.STATUSES:
            raise ValueError(
                f"Trạng thái '{self.status}' không hợp lệ, phải là 1 trong {self.STATUSES}"
            )

@dataclass
class DashboardAlertRule:
    """UC-052 bước 1: "Cấu hình ngưỡng cảnh báo trên KPI" — hệ thống lưu 1
    ngưỡng theo dõi cho 1 KPI thuộc 1 Bảng điều khiển (theo bộ lọc năm/đơn
    vị/lĩnh vực, giống `DashboardFilter` của UC-048). Khi giá trị KPI hiện
    tại (truy vấn lại qua Superset, tái dùng `SupersetDashboardQueryClient`
    của UC-048) vi phạm điều kiện `operator`/`threshold_value`, hệ thống
    coi là "vượt ngưỡng" và gửi cảnh báo qua các kênh đã cấu hình
    (`DashboardAlertChannel`, bước 2).
    """

    OPERATORS = (">", ">=", "<", "<=")

    id: Optional[int]
    dashboard_id: int
    kpi_code: str
    user_id: int
    operator: str
    threshold_value: float
    year: int
    org_unit_code: Optional[str] = None
    sector: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.operator not in self.OPERATORS:
            raise ValueError(
                f"Toán tử ngưỡng '{self.operator}' không hợp lệ, phải là 1 trong {self.OPERATORS}"
            )
        if self.threshold_value is None:
            raise ValueError("Ngưỡng cảnh báo (threshold_value) không được để trống")
        if self.year < 1900 or self.year > 2100:
            raise ValueError("Năm áp ngưỡng cảnh báo không hợp lệ")

    def is_breached(self, kpi_value: Optional[float]) -> bool:
        """Kiểm tra giá trị KPI hiện tại có "vượt ngưỡng" hay không, theo
        đúng `operator` đã cấu hình. Trả về False nếu không lấy được giá
        trị KPI (không đủ dữ liệu để kết luận vượt ngưỡng)."""
        if kpi_value is None:
            return False
        if self.operator == ">":
            return kpi_value > self.threshold_value
        if self.operator == ">=":
            return kpi_value >= self.threshold_value
        if self.operator == "<":
            return kpi_value < self.threshold_value
        return kpi_value <= self.threshold_value

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False


@dataclass
class DashboardAlertChannel:
    """UC-052 bước 2: "Chọn kênh nhận (email / Slack / Webhook)" — hệ
    thống lưu 1 kênh nhận cảnh báo cho 1 ngưỡng đã cấu hình. `destination`
    là địa chỉ email (EMAIL) hoặc URL webhook (SLACK dùng Slack Incoming
    Webhook URL, WEBHOOK dùng URL tuỳ ý nhận POST JSON).
    """

    CHANNEL_TYPES = ("EMAIL", "SLACK", "WEBHOOK")

    id: Optional[int]
    alert_rule_id: int
    channel_type: str
    destination: str
    is_active: bool = True
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.channel_type not in self.CHANNEL_TYPES:
            raise ValueError(
                f"Loại kênh '{self.channel_type}' không hợp lệ, phải là 1 trong {self.CHANNEL_TYPES}"
            )
        self._validate_destination(self.channel_type, self.destination)

    @staticmethod
    def _validate_destination(channel_type: str, destination: str) -> None:
        if not destination or not destination.strip():
            raise ValueError("Địa chỉ nhận cảnh báo (destination) không được để trống")
        if channel_type == "EMAIL":
            if "@" not in destination or destination.startswith("@") or destination.endswith("@"):
                raise ValueError(f"Email nhận cảnh báo '{destination}' không hợp lệ")
            local, _, domain = destination.partition("@")
            if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
                raise ValueError(f"Email nhận cảnh báo '{destination}' không hợp lệ")
        else:
            if not (destination.startswith("http://") or destination.startswith("https://")):
                raise ValueError(
                    f"URL webhook '{destination}' không hợp lệ — phải bắt đầu bằng http:// hoặc https://"
                )

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False


@dataclass
class DashboardAlertLog:
    """UC-052 bước 3: nhật ký append-only mỗi lần hệ thống phát hiện "vượt
    ngưỡng" và gửi cảnh báo qua 1 kênh — dùng để tra cứu lại lịch sử cảnh
    báo đã gửi (thành công/thất bại) của 1 ngưỡng."""

    STATUSES = ("SENT", "FAILED")

    id: Optional[int]
    alert_rule_id: int
    channel_id: int
    channel_type: str
    kpi_value: Optional[float]
    threshold_value: float
    operator: str
    status: str
    message: str = ""
    triggered_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.status not in self.STATUSES:
            raise ValueError(
                f"Trạng thái '{self.status}' không hợp lệ, phải là 1 trong {self.STATUSES}"
            )

# ---------- UC-053: Tra cứu dữ liệu văn bản ----------


@dataclass
class DocumentMetadata:
    """1 văn bản đã được lập chỉ mục vào OpenSearch để tra cứu (UC-053).

    Nguồn gốc dữ liệu: văn bản được tiếp nhận qua `ingestion-service`
    (UC-024 `VanBanIntake`, lưu tệp PDF/bản quét vào MinIO bucket
    `raw-documents`) — CÙNG tên trường `so_ky_hieu`/`loai_van_ban`/
    `trich_yeu`/`ngay_ban_hanh`/`don_vi_ban_hanh`/`raw_object_key` để lập
    chỉ mục nhất quán. `sensitivity_level` + `don_vi_ban_hanh_unit_id` dùng
    để "lọc theo quyền" ở bước tra cứu, đối chiếu với
    `UserPermissionContext` (UC-04, `auth-identity-service`).
    """

    SENSITIVITY_LEVELS = ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET")

    id: str
    so_ky_hieu: str
    loai_van_ban: str
    trich_yeu: str
    ngay_ban_hanh: str  # "YYYY-MM-DD"
    don_vi_ban_hanh: str
    raw_object_key: str
    don_vi_ban_hanh_unit_id: Optional[int] = None
    sensitivity_level: str = "INTERNAL"
    file_content_type: str = "application/pdf"
    indexed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValueError("Mã định danh văn bản (id) không được để trống")
        if not self.so_ky_hieu or not self.so_ky_hieu.strip():
            raise ValueError("Số ký hiệu văn bản không được để trống")
        if not self.loai_van_ban or not self.loai_van_ban.strip():
            raise ValueError("Loại văn bản không được để trống")
        if not self.don_vi_ban_hanh or not self.don_vi_ban_hanh.strip():
            raise ValueError("Đơn vị ban hành không được để trống")
        if not self.raw_object_key or not self.raw_object_key.strip():
            raise ValueError("Đường dẫn tệp (raw_object_key) không được để trống")
        self._validate_date(self.ngay_ban_hanh, "Ngày ban hành")
        if self.sensitivity_level not in self.SENSITIVITY_LEVELS:
            raise ValueError(
                f"Mức nhạy cảm '{self.sensitivity_level}' không hợp lệ, "
                f"phải là 1 trong {self.SENSITIVITY_LEVELS}"
            )

    @staticmethod
    def _validate_date(value: str, field_label: str) -> None:
        if not value:
            raise ValueError(f"{field_label} không được để trống")
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"{field_label} '{value}' phải theo định dạng YYYY-MM-DD")


@dataclass
class DocumentSearchQuery:
    """Bước 1 UC-053: "Nhập từ khoá + bộ lọc (cơ quan, ngày, loại văn bản)"."""

    keyword: Optional[str] = None
    co_quan: Optional[str] = None
    loai_van_ban: Optional[str] = None
    ngay_from: Optional[str] = None
    ngay_to: Optional[str] = None
    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("Số trang (page) phải >= 1")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("Kích thước trang (page_size) phải trong khoảng 1-100")
        if self.ngay_from:
            DocumentMetadata._validate_date(self.ngay_from, "Ngày ban hành từ")
        if self.ngay_to:
            DocumentMetadata._validate_date(self.ngay_to, "Ngày ban hành đến")
        if self.ngay_from and self.ngay_to and self.ngay_from > self.ngay_to:
            raise ValueError("Ngày ban hành từ phải trước hoặc bằng ngày ban hành đến")


@dataclass
class DocumentSearchResultItem:
    """1 dòng kết quả tra cứu (bước 2: "Hệ thống hiển thị")."""

    id: str
    so_ky_hieu: str
    loai_van_ban: str
    trich_yeu: str
    ngay_ban_hanh: str
    don_vi_ban_hanh: str
    sensitivity_level: str
    score: float = 0.0


@dataclass
class DocumentSearchPage:
    items: List[DocumentSearchResultItem]
    total: int
    page: int
    page_size: int


@dataclass
class DocumentAccessContext:
    """Ngữ cảnh quyền của người dùng dùng để "lọc theo quyền" ở UC-053 —
    ánh xạ trực tiếp từ `UserPermissionContext` (UC-04, `auth-identity-service`).
    """

    permitted_domains: List[str]
    permitted_unit_id: Optional[int] = None
    sensitivity_level: str = "INTERNAL"


# ---------- UC-055: Tra cứu dữ liệu giá ----------


@dataclass
class PriceRecord:
    """1 dòng dữ liệu giá trong kho chuẩn hoá `curated.dm_gia` (giá mặt
    hàng theo địa bàn + kỳ — nguồn từ hệ thống Quản lý giá QL_GIA/khảo sát
    thị trường, đã qua UC-029..041)."""

    id: Optional[int]
    mat_hang_code: str
    mat_hang_name: str
    dia_ban_code: str
    dia_ban_name: str
    ky: str  # kỳ báo cáo, định dạng "YYYY-MM"
    gia: float
    don_vi_tinh: str = ""
    nguon: str = ""
    published_at: Optional[str] = None

    _KY_LEN = 7  # "YYYY-MM"

    def __post_init__(self) -> None:
        if not self.mat_hang_code or not self.mat_hang_code.strip():
            raise ValueError("Mã mặt hàng (mat_hang_code) không được để trống")
        if not self.dia_ban_code or not self.dia_ban_code.strip():
            raise ValueError("Mã địa bàn (dia_ban_code) không được để trống")
        self._validate_ky(self.ky)
        if self.gia < 0:
            raise ValueError("Giá (gia) không được âm")

    @staticmethod
    def _validate_ky(value: str) -> None:
        if not value or len(value) != 7 or value[4] != "-":
            raise ValueError(f"Kỳ '{value}' phải theo định dạng YYYY-MM")
        try:
            year, month = int(value[:4]), int(value[5:7])
        except ValueError:
            raise ValueError(f"Kỳ '{value}' phải theo định dạng YYYY-MM")
        if month < 1 or month > 12:
            raise ValueError(f"Kỳ '{value}' có tháng không hợp lệ (01-12)")


@dataclass
class PriceSearchQuery:
    """Bước 1 UC-055: "Nhập bộ lọc (mặt hàng, địa bàn, kỳ)"."""

    mat_hang: Optional[str] = None
    dia_ban: Optional[str] = None
    ky_from: Optional[str] = None
    ky_to: Optional[str] = None
    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("Số trang (page) phải >= 1")
        if self.page_size < 1 or self.page_size > 200:
            raise ValueError("Kích thước trang (page_size) phải trong khoảng 1-200")
        if self.ky_from:
            PriceRecord._validate_ky(self.ky_from)
        if self.ky_to:
            PriceRecord._validate_ky(self.ky_to)
        if self.ky_from and self.ky_to and self.ky_from > self.ky_to:
            raise ValueError("Kỳ bắt đầu (ky_from) phải trước hoặc bằng kỳ kết thúc (ky_to)")


@dataclass
class PriceSearchPage:
    """Bước 2: "Hiển thị giá theo bảng"."""

    items: List[PriceRecord]
    total: int
    page: int
    page_size: int


@dataclass
class PriceTrendPoint:
    """1 điểm trên biểu đồ xu hướng giá (bước 3-4: "Hiển thị biểu đồ xu
    hướng giá theo thời gian -> Hệ thống hiển thị line chart")."""

    ky: str
    gia_trung_binh: float
    so_ban_ghi: int


@dataclass
class PriceTrend:
    mat_hang: Optional[str]
    dia_ban: Optional[str]
    points: List[PriceTrendPoint]


# ==================== UC-056: Tra cứu dữ liệu ngân sách ====================


@dataclass
class NganSachRecord:
    """1 dòng số liệu ngân sách trong kho chuẩn hoá `curated.dm_ngan_sach`
    (thu/chi/tạm ứng theo đơn vị + khoản mục + kỳ — kỳ ngân sách theo năm,
    định dạng \"YYYY\")."""

    id: Optional[int]
    don_vi_code: str
    don_vi_ten: str
    khoan_muc_code: str
    khoan_muc_ten: str
    ky: str  # kỳ ngân sách, định dạng năm "YYYY"
    thu: float = 0.0
    chi: float = 0.0
    tam_ung: float = 0.0
    don_vi_tinh: str = ""
    nguon: str = ""
    published_at: Optional[str] = None

    _KY_LEN = 4  # "YYYY"

    def __post_init__(self) -> None:
        if not self.don_vi_code or not self.don_vi_code.strip():
            raise ValueError("Mã đơn vị (don_vi_code) không được để trống")
        if not self.khoan_muc_code or not self.khoan_muc_code.strip():
            raise ValueError("Mã khoản mục (khoan_muc_code) không được để trống")
        self._validate_ky(self.ky)
        if self.thu < 0:
            raise ValueError("Số thu (thu) không được âm")
        if self.chi < 0:
            raise ValueError("Số chi (chi) không được âm")
        if self.tam_ung < 0:
            raise ValueError("Số tạm ứng (tam_ung) không được âm")

    @staticmethod
    def _validate_ky(value: str) -> None:
        if not value or len(value) != 4 or not value.isdigit():
            raise ValueError(f"Kỳ '{value}' phải theo định dạng năm YYYY")


@dataclass
class NganSachSearchQuery:
    """Bước 1 UC-056: \"Nhập bộ lọc (đơn vị, khoản mục, kỳ)\"."""

    don_vi: Optional[str] = None
    khoan_muc: Optional[str] = None
    ky_from: Optional[str] = None
    ky_to: Optional[str] = None
    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("Số trang (page) phải >= 1")
        if self.page_size < 1 or self.page_size > 200:
            raise ValueError("Kích thước trang (page_size) phải trong khoảng 1-200")
        if self.ky_from:
            NganSachRecord._validate_ky(self.ky_from)
        if self.ky_to:
            NganSachRecord._validate_ky(self.ky_to)
        if self.ky_from and self.ky_to and self.ky_from > self.ky_to:
            raise ValueError("Kỳ bắt đầu (ky_from) phải trước hoặc bằng kỳ kết thúc (ky_to)")


@dataclass
class NganSachSearchPage:
    """Bước 2-3: \"Hệ thống truy vấn curated.dm_ngan_sach -> Hiển thị số
    liệu thu/chi/tạm ứng\"."""

    items: List[NganSachRecord]
    total: int
    page: int
    page_size: int


@dataclass
class NganSachDetailQuery:
    """Bước 4 UC-056: \"Xem chi tiết theo đơn vị/khoản mục\" — bắt buộc
    chọn đúng 1 đơn vị + 1 khoản mục để hệ thống re-query."""

    don_vi_code: str
    khoan_muc_code: str

    def __post_init__(self) -> None:
        if not self.don_vi_code or not self.don_vi_code.strip():
            raise ValueError("Đơn vị (don_vi_code) không được để trống")
        if not self.khoan_muc_code or not self.khoan_muc_code.strip():
            raise ValueError("Khoản mục (khoan_muc_code) không được để trống")


@dataclass
class NganSachDetail:
    """Bước 5: \"Hệ thống re-query\" -> kết quả chi tiết theo đơn vị/khoản
    mục — toàn bộ các kỳ + tổng hợp thu/chi/tạm ứng."""

    don_vi_code: str
    khoan_muc_code: str
    items: List[NganSachRecord]
    tong_thu: float
    tong_chi: float
    tong_tam_ung: float


# ==================== UC-057: Hiển thị độ mới dữ liệu ====================

# Ngưỡng (giờ) để coi 1 nguồn là "chậm trễ" nếu last_sync quá cũ — dùng để
# suy ra trạng thái hiển thị (bước 1 "ô thông tin độ mới dữ liệu"/bước 2
# "bảng chi tiết"), KHÔNG lưu vào DB (suy ra tại thời điểm đọc).
DATA_FRESHNESS_STALE_THRESHOLD_HOURS = 24


@dataclass
class DataFreshnessRecord:
    """1 dòng độ mới dữ liệu theo nguồn trong view `curated.data_freshness`
    (docs/use_cases.json id 57) — `last_sync` (lần đồng bộ gần nhất) + độ
    đầy đủ (tỉ lệ số bản ghi đã nhận được / số bản ghi kỳ vọng) của 1
    nguồn dữ liệu (vd TABMIS, QL_GIA, QL_TAI_SAN...)."""

    id: Optional[int]
    nguon_code: str
    nguon_ten: str
    last_sync: str  # ISO-8601 datetime UTC
    expected_record_count: int = 0
    actual_record_count: int = 0
    updated_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.nguon_code or not self.nguon_code.strip():
            raise ValueError("Mã nguồn (nguon_code) không được để trống")
        if not self.nguon_ten or not self.nguon_ten.strip():
            raise ValueError("Tên nguồn (nguon_ten) không được để trống")
        if not self.last_sync or not self.last_sync.strip():
            raise ValueError("Thời điểm đồng bộ gần nhất (last_sync) không được để trống")
        if self.expected_record_count < 0:
            raise ValueError("Số bản ghi kỳ vọng (expected_record_count) không được âm")
        if self.actual_record_count < 0:
            raise ValueError("Số bản ghi thực nhận (actual_record_count) không được âm")

    @property
    def completeness_percent(self) -> float:
        """Độ đầy đủ (%) = số bản ghi thực nhận / số bản ghi kỳ vọng.

        Không kỳ vọng bản ghi nào (`expected_record_count == 0`) thì coi
        như đầy đủ 100% nếu có ít nhất 1 bản ghi thực nhận, ngược lại 0%.
        """
        if self.expected_record_count <= 0:
            return 100.0 if self.actual_record_count > 0 else 0.0
        pct = (self.actual_record_count / self.expected_record_count) * 100
        return round(min(pct, 100.0), 2)

    def is_stale(self, now: datetime, threshold_hours: int = DATA_FRESHNESS_STALE_THRESHOLD_HOURS) -> bool:
        """Nguồn được coi là "chậm trễ" nếu `last_sync` quá `threshold_hours`
        giờ so với `now`."""
        try:
            last_sync_dt = datetime.fromisoformat(self.last_sync.replace("Z", "+00:00"))
        except ValueError:
            return True
        if last_sync_dt.tzinfo is None:
            last_sync_dt = last_sync_dt.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return (now - last_sync_dt) > timedelta(hours=threshold_hours)


@dataclass
class DataFreshnessSummary:
    """Bước 1 UC-057: \"Xem ô thông tin độ mới dữ liệu trên Bảng điều
    khiển\" — tổng quan toàn hệ thống suy ra từ `curated.data_freshness`."""

    total_sources: int
    stale_sources: int
    average_completeness_percent: float
    latest_last_sync: Optional[str]
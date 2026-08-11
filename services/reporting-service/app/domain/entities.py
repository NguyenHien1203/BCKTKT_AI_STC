"""Domain entities cho reporting-service.

UC-047 (Xem Bảng điều khiển điều hành): danh mục Bảng điều khiển được nhúng
từ Apache Superset + tuỳ chọn cá nhân "ghim bảng điều khiển yêu thích".

UC-049 (Chọn báo cáo theo mẫu + cấu hình bộ lọc): danh mục mẫu báo cáo
(report template) tra cứu từ Lớp ngữ nghĩa (chỉ tiêu UC-043) + trạng thái
bộ lọc (năm/đơn vị/lĩnh vực/kỳ) người dùng đã cấu hình cho từng mẫu, dùng
làm đầu vào cho UC-050 "Sinh + kết xuất báo cáo".
"""
from dataclasses import dataclass, field
from datetime import datetime
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
"""Domain entities cho reporting-service.

UC-047 (Xem Bảng điều khiển điều hành): danh mục Bảng điều khiển được nhúng
từ Apache Superset + tuỳ chọn cá nhân "ghim bảng điều khiển yêu thích".
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


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
class DashboardFavorite:
    """UC-047 bước cuối: "Ghim bảng điều khiển yêu thích" — hệ thống lưu vào
    tùy chọn cá nhân của người dùng (1 user có thể ghim nhiều dashboard,
    nhưng không ghim trùng 1 dashboard 2 lần)."""

    id: Optional[int]
    user_id: int
    dashboard_id: int
    pinned_at: Optional[datetime] = None
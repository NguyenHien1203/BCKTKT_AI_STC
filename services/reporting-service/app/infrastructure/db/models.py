import os
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.session import Base

# Schema "reporting" chỉ áp dụng khi chạy trên Postgres (theo ARCHITECTURE.md:
# database-per-schema). SQLite không hỗ trợ schema nên bỏ qua khi dev/test.
_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reporting_service_dev.db")
_SCHEMA = "reporting" if not _DATABASE_URL.startswith("sqlite") else None

class DashboardModel(Base):
    """UC-047: danh mục Bảng điều khiển điều hành (nhúng từ Superset)."""

    __tablename__ = "dashboards"
    __table_args__ = (
        UniqueConstraint("code", name="uq_reporting_dashboards_code"),
        {"schema": _SCHEMA} if _SCHEMA else {},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    superset_dashboard_uid: Mapped[str] = mapped_column(String(255), nullable=False)
    embed_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class DashboardKpiModel(Base):
    """UC-048: danh mục chỉ tiêu (KPI) thuộc 1 Bảng điều khiển."""

    __tablename__ = "dashboard_kpis"
    __table_args__ = (
        UniqueConstraint(
            "dashboard_id", "code", name="uq_reporting_dashboard_kpis_dashboard_code"
        ),
        {"schema": _SCHEMA} if _SCHEMA else {},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}dashboards.id"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    higher_is_better: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class KpiExplanationModel(Base):
    """UC-048: lịch sử (append-only) "Yêu cầu AI giải thích KPI"."""

    __tablename__ = "kpi_explanations"
    __table_args__ = ({"schema": _SCHEMA} if _SCHEMA else {},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}dashboards.id"),
        nullable=False,
        index=True,
    )
    kpi_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    org_unit_code: Mapped[str] = mapped_column(String(50), nullable=True)
    sector: Mapped[str] = mapped_column(String(30), nullable=True)
    requested_by: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ReportTemplateModel(Base):
    """UC-049: danh mục mẫu báo cáo. `columns`/`available_periods` lưu
    dạng JSON text (SQLite/Postgres đều hỗ trợ Text, không cần kiểu JSON
    riêng theo Postgres)."""

    __tablename__ = "report_templates"
    __table_args__ = (
        UniqueConstraint("code", name="uq_reporting_report_templates_code"),
        {"schema": _SCHEMA} if _SCHEMA else {},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    columns_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    available_periods_json: Mapped[str] = mapped_column(Text, nullable=False, default='["NAM"]')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ReportFilterConfigModel(Base):
    """UC-049 bước 3: trạng thái bộ lọc đã lưu theo mẫu báo cáo + người
    dùng — 1 người dùng chỉ có 1 bản ghi cho 1 mẫu (unique constraint)."""

    __tablename__ = "report_filter_configs"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "user_id",
            name="uq_reporting_report_filter_configs_template_user",
        ),
        {"schema": _SCHEMA} if _SCHEMA else {},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}report_templates.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)
    period_value: Mapped[int] = mapped_column(Integer, nullable=True)
    org_unit_code: Mapped[str] = mapped_column(String(50), nullable=True)
    sector: Mapped[str] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SAVED")
    saved_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class DashboardFavoriteModel(Base):
    """UC-047: tuỳ chọn cá nhân "ghim bảng điều khiển yêu thích"."""

    __tablename__ = "dashboard_favorites"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "dashboard_id", name="uq_reporting_dashboard_favorites_user_dashboard"
        ),
        {"schema": _SCHEMA} if _SCHEMA else {},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    dashboard_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}dashboards.id"),
        nullable=False,
        index=True,
    )
    pinned_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class GeneratedReportLogModel(Base):
    """UC-050: nhật ký append-only mỗi lượt kết xuất báo cáo (PDF/Excel)."""

    __tablename__ = "generated_report_logs"
    __table_args__ = ({"schema": _SCHEMA} if _SCHEMA else {},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}report_templates.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)
    period_value: Mapped[int] = mapped_column(Integer, nullable=True)
    org_unit_code: Mapped[str] = mapped_column(String(50), nullable=True)
    sector: Mapped[str] = mapped_column(String(30), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

class ReportScheduleModel(Base):
    """UC-051: lịch cấu hình để tự động sinh + gửi email báo cáo theo
    lịch (hàng ngày/hàng tuần/hàng tháng)."""

    __tablename__ = "report_schedules"
    __table_args__ = ({"schema": _SCHEMA} if _SCHEMA else {},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}report_templates.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    frequency: Mapped[str] = mapped_column(String(10), nullable=False)
    time_of_day: Mapped[str] = mapped_column(String(5), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False, default="PDF")
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=True)
    day_of_month: Mapped[int] = mapped_column(Integer, nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=True)
    period_type: Mapped[str] = mapped_column(String(10), nullable=True)
    period_value: Mapped[int] = mapped_column(Integer, nullable=True)
    org_unit_code: Mapped[str] = mapped_column(String(50), nullable=True)
    sector: Mapped[str] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ReportScheduleRecipientModel(Base):
    """UC-051 bước "Cấu hình người nhận (email)"."""

    __tablename__ = "report_schedule_recipients"
    __table_args__ = (
        UniqueConstraint(
            "schedule_id", "email", name="uq_reporting_schedule_recipients_schedule_email"
        ),
        {"schema": _SCHEMA} if _SCHEMA else {},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}report_schedules.id"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ReportScheduleRunLogModel(Base):
    """UC-051: nhật ký append-only mỗi lần tác vụ định kỳ (cron) chạy sinh
    + gửi email báo cáo theo lịch."""

    __tablename__ = "report_schedule_run_logs"
    __table_args__ = ({"schema": _SCHEMA} if _SCHEMA else {},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}report_schedules.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    recipients_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    run_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

class DashboardAlertRuleModel(Base):
    """UC-052 bước 1: ngưỡng cảnh báo đã cấu hình cho 1 KPI thuộc 1 Bảng
    điều khiển."""

    __tablename__ = "dashboard_alert_rules"
    __table_args__ = ({"schema": _SCHEMA} if _SCHEMA else {},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}dashboards.id"),
        nullable=False,
        index=True,
    )
    kpi_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(2), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    org_unit_code: Mapped[str] = mapped_column(String(50), nullable=True)
    sector: Mapped[str] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class DashboardAlertChannelModel(Base):
    """UC-052 bước 2: kênh nhận cảnh báo (email/Slack/Webhook) của 1 ngưỡng."""

    __tablename__ = "dashboard_alert_channels"
    __table_args__ = ({"schema": _SCHEMA} if _SCHEMA else {},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_rule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}dashboard_alert_rules.id"),
        nullable=False,
        index=True,
    )
    channel_type: Mapped[str] = mapped_column(String(10), nullable=False)
    destination: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class DashboardAlertLogModel(Base):
    """UC-052 bước 3: nhật ký append-only mỗi lần hệ thống gửi cảnh báo do
    vượt ngưỡng."""

    __tablename__ = "dashboard_alert_logs"
    __table_args__ = ({"schema": _SCHEMA} if _SCHEMA else {},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_rule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}dashboard_alert_rules.id"),
        nullable=False,
        index=True,
    )
    channel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{_SCHEMA + '.' if _SCHEMA else ''}dashboard_alert_channels.id"),
        nullable=False,
        index=True,
    )
    channel_type: Mapped[str] = mapped_column(String(10), nullable=False)
    kpi_value: Mapped[float] = mapped_column(Float, nullable=True)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    operator: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

# ==================== UC-054: Tra cứu dữ liệu tài sản ====================

# Schema "curated" — bảng chiều (dimension) tài sản `dm_tai_san` KHÔNG
# thuộc sở hữu của reporting-service (được nạp bởi tiến trình công bố dữ
# liệu chuẩn hoá, tương tự curated.dm_records của data-quality-service UC-041),
# nhưng reporting-service ĐỌC trực tiếp qua CÙNG 1 CSDL Postgres dùng chung
# ("financial_dw", xem ARCHITECTURE.md mục 2 + docker-compose.yml). Model
# này khai báo migration riêng (0007_uc054_create_dm_tai_san.py) để service
# có thể khởi tạo/seed bảng khi chưa có pipeline công bố dữ liệu thật nối
# vào.
_CURATED_SCHEMA = "curated" if not _DATABASE_URL.startswith("sqlite") else None


class TaiSanModel(Base):
    """UC-054: bảng chiều tài sản công trong kho dữ liệu chuẩn hoá
    `curated.dm_tai_san`."""

    __tablename__ = "dm_tai_san"
    __table_args__ = (
        UniqueConstraint("ma_tai_san", name="uq_curated_dm_tai_san_ma_tai_san"),
        {"schema": _CURATED_SCHEMA} if _CURATED_SCHEMA else {},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ma_tai_san: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ten_tai_san: Mapped[str] = mapped_column(String(255), nullable=False)
    don_vi_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    don_vi_ten: Mapped[str] = mapped_column(String(255), nullable=False)
    nhom_tai_san_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    nhom_tai_san_ten: Mapped[str] = mapped_column(String(255), nullable=False)
    trang_thai: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    nguyen_gia: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    gia_tri_con_lai: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ngay_dua_vao_su_dung: Mapped[str] = mapped_column(String(10), nullable=True)
    nam_tai_chinh: Mapped[int] = mapped_column(Integer, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(Text, nullable=False, default="")
    published_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

# ---------- UC-055: Tra cứu dữ liệu giá ----------

# Bảng `dm_gia` sống trong schema `curated` (khác schema `reporting` của
# các bảng trên) vì đây là dữ liệu data mart giá đã chuẩn hoá — đúng tên
# nghiệp vụ "curated.dm_gia" ghi trong flow UC-055 (docs/use_cases.json id
# 55). Cùng 1 instance Postgres (ADR-001) với data-quality-service, khác
# schema. SQLite dev/test không hỗ trợ schema nên bỏ qua (giống `_SCHEMA`).
_SCHEMA_CURATED = "curated" if not _DATABASE_URL.startswith("sqlite") else None


class DmGiaModel(Base):
    """UC-055: 1 dòng dữ liệu giá mặt hàng theo địa bàn + kỳ trong kho
    chuẩn hoá `curated.dm_gia`."""

    __tablename__ = "dm_gia"
    __table_args__ = ({"schema": _SCHEMA_CURATED} if _SCHEMA_CURATED else {},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mat_hang_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    mat_hang_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dia_ban_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    dia_ban_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ky: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # "YYYY-MM"
    gia: Mapped[float] = mapped_column(Float, nullable=False)
    don_vi_tinh: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    nguon: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    published_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

# ---------- UC-056: Tra cứu dữ liệu ngân sách ----------

# Bảng `dm_ngan_sach` cũng sống trong schema `curated` (đúng tên nghiệp vụ
# "curated.dm_ngan_sach" ghi trong flow UC-056, docs/use_cases.json id 56),
# cùng 1 instance Postgres (ADR-001), cùng tinh thần với `DmGiaModel`
# (UC-055) — SQLite dev/test không hỗ trợ schema nên bỏ qua.
_SCHEMA_CURATED_NGAN_SACH = "curated" if not _DATABASE_URL.startswith("sqlite") else None


class DmNganSachModel(Base):
    """UC-056: 1 dòng số liệu ngân sách (thu/chi/tạm ứng) theo đơn vị +
    khoản mục + kỳ trong kho chuẩn hoá `curated.dm_ngan_sach`."""

    __tablename__ = "dm_ngan_sach"
    __table_args__ = ({"schema": _SCHEMA_CURATED_NGAN_SACH} if _SCHEMA_CURATED_NGAN_SACH else {},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    don_vi_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    don_vi_ten: Mapped[str] = mapped_column(String(255), nullable=False)
    khoan_muc_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    khoan_muc_ten: Mapped[str] = mapped_column(String(255), nullable=False)
    ky: Mapped[str] = mapped_column(String(4), nullable=False, index=True)  # "YYYY"
    thu: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    chi: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tam_ung: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    don_vi_tinh: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    nguon: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    published_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
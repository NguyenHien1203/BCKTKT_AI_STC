import os
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
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
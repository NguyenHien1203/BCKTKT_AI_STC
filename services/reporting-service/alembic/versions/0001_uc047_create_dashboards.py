"""UC-047: create reporting schema, dashboards + dashboard_favorites tables
(Xem Bảng điều khiển điều hành)

Revision ID: 0001
Revises:
Create Date: 2026-08-07

"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS reporting")

    op.create_table(
        "dashboards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("superset_dashboard_uid", sa.String(length=255), nullable=False),
        sa.Column("embed_url", sa.String(length=1000), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_dashboards_code", "dashboards", ["code"], schema="reporting"
    )
    op.create_index(
        "ix_reporting_dashboards_category", "dashboards", ["category"], schema="reporting"
    )

    op.create_table(
        "dashboard_favorites",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "dashboard_id",
            sa.Integer(),
            sa.ForeignKey("reporting.dashboards.id"),
            nullable=False,
        ),
        sa.Column(
            "pinned_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "dashboard_id", name="uq_reporting_dashboard_favorites_user_dashboard"
        ),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_dashboard_favorites_user_id",
        "dashboard_favorites",
        ["user_id"],
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_dashboard_favorites_dashboard_id",
        "dashboard_favorites",
        ["dashboard_id"],
        schema="reporting",
    )

    # Seed danh mục Bảng điều khiển mẫu (Superset) — để UC-047 có dữ liệu
    # xem/ghim ngay sau khi khởi tạo, không phải chờ 1 UC quản lý danh mục
    # riêng (chưa có trong BCKTKT). Có thể sửa/xoá qua API POST /dashboards
    # (đăng ký) và POST /dashboards/{id}/deactivate.
    dashboards_table = sa.table(
        "dashboards",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("superset_dashboard_uid", sa.String),
        sa.column("embed_url", sa.String),
        sa.column("is_active", sa.Boolean),
        schema="reporting",
    )
    superset_base_url = "http://localhost:8088/superset/dashboard"
    op.bulk_insert(
        dashboards_table,
        [
            {
                "code": "DB-NGAN-SACH-TONG-HOP",
                "name": "Tổng hợp Ngân sách tỉnh",
                "description": "Bảng điều khiển tổng hợp thu/chi ngân sách theo đơn vị, niên độ.",
                "category": "NGAN_SACH",
                "superset_dashboard_uid": "ngan-sach-tong-hop",
                "embed_url": f"{superset_base_url}/ngan-sach-tong-hop/?standalone=1",
                "is_active": True,
            },
            {
                "code": "DB-TAI-SAN-CONG",
                "name": "Quản lý Tài sản công",
                "description": "Theo dõi giá trị, tình trạng, phân bổ tài sản công toàn tỉnh.",
                "category": "TAI_SAN_CONG",
                "superset_dashboard_uid": "tai-san-cong",
                "embed_url": f"{superset_base_url}/tai-san-cong/?standalone=1",
                "is_active": True,
            },
            {
                "code": "DB-DAU-TU-CONG",
                "name": "Tiến độ Đầu tư công",
                "description": "Bảng điều khiển tiến độ giải ngân các dự án đầu tư công.",
                "category": "DAU_TU_CONG",
                "superset_dashboard_uid": "dau-tu-cong",
                "embed_url": f"{superset_base_url}/dau-tu-cong/?standalone=1",
                "is_active": True,
            },
            {
                "code": "DB-GIA-THI-TRUONG",
                "name": "Diễn biến Giá thị trường",
                "description": "Theo dõi chỉ số giá các mặt hàng thiết yếu theo khu vực.",
                "category": "GIA",
                "superset_dashboard_uid": "gia-thi-truong",
                "embed_url": f"{superset_base_url}/gia-thi-truong/?standalone=1",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reporting_dashboard_favorites_dashboard_id",
        table_name="dashboard_favorites",
        schema="reporting",
    )
    op.drop_index(
        "ix_reporting_dashboard_favorites_user_id",
        table_name="dashboard_favorites",
        schema="reporting",
    )
    op.drop_table("dashboard_favorites", schema="reporting")
    op.drop_index(
        "ix_reporting_dashboards_category", table_name="dashboards", schema="reporting"
    )
    op.drop_index("ix_reporting_dashboards_code", table_name="dashboards", schema="reporting")
    op.drop_table("dashboards", schema="reporting")
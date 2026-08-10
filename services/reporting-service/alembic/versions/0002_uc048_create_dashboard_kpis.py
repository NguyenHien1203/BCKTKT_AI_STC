"""UC-048: create dashboard_kpis + kpi_explanations tables
(Áp bộ lọc + xem chi tiết Bảng điều khiển)

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-10

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_kpis",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dashboard_id",
            sa.Integer(),
            sa.ForeignKey("reporting.dashboards.id"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit_of_measure", sa.String(length=50), nullable=False, server_default=""),
        sa.Column(
            "higher_is_better", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "dashboard_id", "code", name="uq_reporting_dashboard_kpis_dashboard_code"
        ),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_dashboard_kpis_dashboard_id",
        "dashboard_kpis",
        ["dashboard_id"],
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_dashboard_kpis_code", "dashboard_kpis", ["code"], schema="reporting"
    )

    op.create_table(
        "kpi_explanations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dashboard_id",
            sa.Integer(),
            sa.ForeignKey("reporting.dashboards.id"),
            nullable=False,
        ),
        sa.Column("kpi_code", sa.String(length=50), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("org_unit_code", sa.String(length=50), nullable=True),
        sa.Column("sector", sa.String(length=30), nullable=True),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_kpi_explanations_dashboard_id",
        "kpi_explanations",
        ["dashboard_id"],
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_kpi_explanations_kpi_code",
        "kpi_explanations",
        ["kpi_code"],
        schema="reporting",
    )

    # Seed KPI mẫu cho 4 dashboard đã seed ở migration 0001 — để UC-048 có
    # dữ liệu áp bộ lọc/xem chi tiết ngay sau khi khởi tạo. Có thể sửa/thêm
    # qua API POST /dashboards/{id}/kpis.
    conn = op.get_bind()
    dashboard_kpis_table = sa.table(
        "dashboard_kpis",
        sa.column("dashboard_id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("unit_of_measure", sa.String),
        sa.column("higher_is_better", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        schema="reporting",
    )
    dashboards_table = sa.table(
        "dashboards",
        sa.column("id", sa.Integer),
        sa.column("code", sa.String),
        schema="reporting",
    )
    rows = conn.execute(
        sa.select(dashboards_table.c.id, dashboards_table.c.code)
    ).fetchall()
    seed_by_dashboard_code = {
        "DB-NGAN-SACH-TONG-HOP": [
            ("THU_NGAN_SACH", "Tổng thu ngân sách", "tỷ đồng", True),
            ("CHI_NGAN_SACH", "Tổng chi ngân sách", "tỷ đồng", False),
        ],
        "DB-TAI-SAN-CONG": [
            ("GIA_TRI_TAI_SAN", "Tổng giá trị tài sản công", "tỷ đồng", True),
        ],
        "DB-DAU-TU-CONG": [
            ("TY_LE_GIAI_NGAN", "Tỷ lệ giải ngân đầu tư công", "%", True),
        ],
        "DB-GIA-THI-TRUONG": [
            ("CHI_SO_GIA", "Chỉ số giá tiêu dùng", "điểm", False),
        ],
    }
    seed_rows = []
    for dashboard_id, dashboard_code in rows:
        for code, name, unit, higher_is_better in seed_by_dashboard_code.get(
            dashboard_code, []
        ):
            seed_rows.append(
                {
                    "dashboard_id": dashboard_id,
                    "code": code,
                    "name": name,
                    "unit_of_measure": unit,
                    "higher_is_better": higher_is_better,
                    "is_active": True,
                }
            )
    if seed_rows:
        op.bulk_insert(dashboard_kpis_table, seed_rows)


def downgrade() -> None:
    op.drop_index(
        "ix_reporting_kpi_explanations_kpi_code",
        table_name="kpi_explanations",
        schema="reporting",
    )
    op.drop_index(
        "ix_reporting_kpi_explanations_dashboard_id",
        table_name="kpi_explanations",
        schema="reporting",
    )
    op.drop_table("kpi_explanations", schema="reporting")

    op.drop_index(
        "ix_reporting_dashboard_kpis_code", table_name="dashboard_kpis", schema="reporting"
    )
    op.drop_index(
        "ix_reporting_dashboard_kpis_dashboard_id",
        table_name="dashboard_kpis",
        schema="reporting",
    )
    op.drop_table("dashboard_kpis", schema="reporting")
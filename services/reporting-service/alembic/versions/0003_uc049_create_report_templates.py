"""UC-049: create report_templates + report_filter_configs tables
(Chọn báo cáo theo mẫu + cấu hình bộ lọc)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-10

"""
import json

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("columns_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "available_periods_json", sa.Text(), nullable=False, server_default='["NAM"]'
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("code", name="uq_reporting_report_templates_code"),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_report_templates_code",
        "report_templates",
        ["code"],
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_report_templates_category",
        "report_templates",
        ["category"],
        schema="reporting",
    )

    op.create_table(
        "report_filter_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("reporting.report_templates.id"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("period_type", sa.String(length=10), nullable=False),
        sa.Column("period_value", sa.Integer(), nullable=True),
        sa.Column("org_unit_code", sa.String(length=50), nullable=True),
        sa.Column("sector", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="SAVED"),
        sa.Column(
            "saved_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "template_id",
            "user_id",
            name="uq_reporting_report_filter_configs_template_user",
        ),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_report_filter_configs_template_id",
        "report_filter_configs",
        ["template_id"],
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_report_filter_configs_user_id",
        "report_filter_configs",
        ["user_id"],
        schema="reporting",
    )

    # Seed vài mẫu báo cáo mẫu — để UC-049 có dữ liệu ngay sau khi khởi
    # tạo. Có thể sửa/thêm qua API POST /report-templates.
    conn = op.get_bind()
    report_templates_table = sa.table(
        "report_templates",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("category", sa.String),
        sa.column("columns_json", sa.Text),
        sa.column("available_periods_json", sa.Text),
        sa.column("is_active", sa.Boolean),
        schema="reporting",
    )
    seed_rows = [
        {
            "code": "RPT-NGAN-SACH-TONG-HOP",
            "name": "Báo cáo tổng hợp thu chi ngân sách",
            "description": "Báo cáo tổng hợp số liệu thu/chi ngân sách theo đơn vị và kỳ.",
            "category": "NGAN_SACH",
            "columns_json": json.dumps(
                [
                    {"field": "don_vi", "label": "Đơn vị", "data_type": "STRING"},
                    {"field": "khoan_muc", "label": "Khoản mục", "data_type": "STRING"},
                    {"field": "du_toan", "label": "Dự toán (triệu đồng)", "data_type": "DECIMAL"},
                    {
                        "field": "thuc_hien",
                        "label": "Thực hiện (triệu đồng)",
                        "data_type": "DECIMAL",
                    },
                    {"field": "ty_le", "label": "Tỉ lệ thực hiện (%)", "data_type": "DECIMAL"},
                ],
                ensure_ascii=False,
            ),
            "available_periods_json": json.dumps(["THANG", "QUY", "NAM"]),
            "is_active": True,
        },
        {
            "code": "RPT-TAI-SAN-CONG",
            "name": "Báo cáo tổng hợp tài sản công",
            "description": "Báo cáo tổng hợp giá trị/tình trạng tài sản công theo đơn vị.",
            "category": "TAI_SAN_CONG",
            "columns_json": json.dumps(
                [
                    {"field": "don_vi", "label": "Đơn vị", "data_type": "STRING"},
                    {"field": "nhom_tai_san", "label": "Nhóm tài sản", "data_type": "STRING"},
                    {
                        "field": "nguyen_gia",
                        "label": "Nguyên giá (triệu đồng)",
                        "data_type": "DECIMAL",
                    },
                    {
                        "field": "gia_tri_con_lai",
                        "label": "Giá trị còn lại (triệu đồng)",
                        "data_type": "DECIMAL",
                    },
                ],
                ensure_ascii=False,
            ),
            "available_periods_json": json.dumps(["QUY", "NAM"]),
            "is_active": True,
        },
        {
            "code": "RPT-DAU-TU-CONG",
            "name": "Báo cáo tiến độ giải ngân đầu tư công",
            "description": "Báo cáo tổng hợp tiến độ giải ngân vốn đầu tư công theo dự án/đơn vị.",
            "category": "DAU_TU_CONG",
            "columns_json": json.dumps(
                [
                    {"field": "don_vi", "label": "Chủ đầu tư", "data_type": "STRING"},
                    {"field": "du_an", "label": "Dự án", "data_type": "STRING"},
                    {
                        "field": "ke_hoach_von",
                        "label": "Kế hoạch vốn (triệu đồng)",
                        "data_type": "DECIMAL",
                    },
                    {
                        "field": "giai_ngan",
                        "label": "Giải ngân (triệu đồng)",
                        "data_type": "DECIMAL",
                    },
                    {"field": "ty_le_giai_ngan", "label": "Tỉ lệ giải ngân (%)", "data_type": "DECIMAL"},
                ],
                ensure_ascii=False,
            ),
            "available_periods_json": json.dumps(["THANG", "QUY", "NAM"]),
            "is_active": True,
        },
    ]
    op.bulk_insert(report_templates_table, seed_rows)


def downgrade() -> None:
    op.drop_index(
        "ix_reporting_report_filter_configs_user_id",
        table_name="report_filter_configs",
        schema="reporting",
    )
    op.drop_index(
        "ix_reporting_report_filter_configs_template_id",
        table_name="report_filter_configs",
        schema="reporting",
    )
    op.drop_table("report_filter_configs", schema="reporting")

    op.drop_index(
        "ix_reporting_report_templates_category",
        table_name="report_templates",
        schema="reporting",
    )
    op.drop_index(
        "ix_reporting_report_templates_code",
        table_name="report_templates",
        schema="reporting",
    )
    op.drop_table("report_templates", schema="reporting")
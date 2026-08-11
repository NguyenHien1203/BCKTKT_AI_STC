"""UC-050: create generated_report_logs table
(Sinh + kết xuất báo cáo)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generated_report_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("reporting.report_templates.id"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(length=10), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("period_type", sa.String(length=10), nullable=False),
        sa.Column("period_value", sa.Integer(), nullable=True),
        sa.Column("org_unit_code", sa.String(length=50), nullable=True),
        sa.Column("sector", sa.String(length=30), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "generated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_generated_report_logs_template_id",
        "generated_report_logs",
        ["template_id"],
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_generated_report_logs_user_id",
        "generated_report_logs",
        ["user_id"],
        schema="reporting",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reporting_generated_report_logs_user_id",
        table_name="generated_report_logs",
        schema="reporting",
    )
    op.drop_index(
        "ix_reporting_generated_report_logs_template_id",
        table_name="generated_report_logs",
        schema="reporting",
    )
    op.drop_table("generated_report_logs", schema="reporting")
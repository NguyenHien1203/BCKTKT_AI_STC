"""UC-051: create report_schedules / report_schedule_recipients /
report_schedule_run_logs tables (Cấu hình báo cáo theo lịch)

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_schedules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("reporting.report_templates.id"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.String(length=10), nullable=False),
        sa.Column("time_of_day", sa.String(length=5), nullable=False),
        sa.Column("format", sa.String(length=10), nullable=False, server_default="PDF"),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("period_type", sa.String(length=10), nullable=True),
        sa.Column("period_value", sa.Integer(), nullable=True),
        sa.Column("org_unit_code", sa.String(length=50), nullable=True),
        sa.Column("sector", sa.String(length=30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_report_schedules_template_id",
        "report_schedules",
        ["template_id"],
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_report_schedules_user_id",
        "report_schedules",
        ["user_id"],
        schema="reporting",
    )

    op.create_table(
        "report_schedule_recipients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "schedule_id",
            sa.Integer(),
            sa.ForeignKey("reporting.report_schedules.id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "added_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "schedule_id",
            "email",
            name="uq_reporting_schedule_recipients_schedule_email",
        ),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_schedule_recipients_schedule_id",
        "report_schedule_recipients",
        ["schedule_id"],
        schema="reporting",
    )

    op.create_table(
        "report_schedule_run_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "schedule_id",
            sa.Integer(),
            sa.ForeignKey("reporting.report_schedules.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("recipients_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "run_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_schedule_run_logs_schedule_id",
        "report_schedule_run_logs",
        ["schedule_id"],
        schema="reporting",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reporting_schedule_run_logs_schedule_id",
        table_name="report_schedule_run_logs",
        schema="reporting",
    )
    op.drop_table("report_schedule_run_logs", schema="reporting")

    op.drop_index(
        "ix_reporting_schedule_recipients_schedule_id",
        table_name="report_schedule_recipients",
        schema="reporting",
    )
    op.drop_table("report_schedule_recipients", schema="reporting")

    op.drop_index(
        "ix_reporting_report_schedules_user_id",
        table_name="report_schedules",
        schema="reporting",
    )
    op.drop_index(
        "ix_reporting_report_schedules_template_id",
        table_name="report_schedules",
        schema="reporting",
    )
    op.drop_table("report_schedules", schema="reporting")
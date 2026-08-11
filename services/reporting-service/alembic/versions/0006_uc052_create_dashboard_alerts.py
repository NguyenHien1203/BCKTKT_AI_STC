"""UC-052: create dashboard_alert_rules / dashboard_alert_channels /
dashboard_alert_logs tables (Đăng ký nhận cảnh báo dashboard)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dashboard_id",
            sa.Integer(),
            sa.ForeignKey("reporting.dashboards.id"),
            nullable=False,
        ),
        sa.Column("kpi_code", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("operator", sa.String(length=2), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("org_unit_code", sa.String(length=50), nullable=True),
        sa.Column("sector", sa.String(length=30), nullable=True),
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
        "ix_reporting_dashboard_alert_rules_dashboard_id",
        "dashboard_alert_rules",
        ["dashboard_id"],
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_dashboard_alert_rules_kpi_code",
        "dashboard_alert_rules",
        ["kpi_code"],
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_dashboard_alert_rules_user_id",
        "dashboard_alert_rules",
        ["user_id"],
        schema="reporting",
    )

    op.create_table(
        "dashboard_alert_channels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "alert_rule_id",
            sa.Integer(),
            sa.ForeignKey("reporting.dashboard_alert_rules.id"),
            nullable=False,
        ),
        sa.Column("channel_type", sa.String(length=10), nullable=False),
        sa.Column("destination", sa.String(length=500), nullable=False),
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
        "ix_reporting_dashboard_alert_channels_alert_rule_id",
        "dashboard_alert_channels",
        ["alert_rule_id"],
        schema="reporting",
    )

    op.create_table(
        "dashboard_alert_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "alert_rule_id",
            sa.Integer(),
            sa.ForeignKey("reporting.dashboard_alert_rules.id"),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            sa.Integer(),
            sa.ForeignKey("reporting.dashboard_alert_channels.id"),
            nullable=False,
        ),
        sa.Column("channel_type", sa.String(length=10), nullable=False),
        sa.Column("kpi_value", sa.Float(), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("operator", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "triggered_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_dashboard_alert_logs_alert_rule_id",
        "dashboard_alert_logs",
        ["alert_rule_id"],
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_dashboard_alert_logs_channel_id",
        "dashboard_alert_logs",
        ["channel_id"],
        schema="reporting",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reporting_dashboard_alert_logs_channel_id",
        table_name="dashboard_alert_logs",
        schema="reporting",
    )
    op.drop_index(
        "ix_reporting_dashboard_alert_logs_alert_rule_id",
        table_name="dashboard_alert_logs",
        schema="reporting",
    )
    op.drop_table("dashboard_alert_logs", schema="reporting")

    op.drop_index(
        "ix_reporting_dashboard_alert_channels_alert_rule_id",
        table_name="dashboard_alert_channels",
        schema="reporting",
    )
    op.drop_table("dashboard_alert_channels", schema="reporting")

    op.drop_index(
        "ix_reporting_dashboard_alert_rules_user_id",
        table_name="dashboard_alert_rules",
        schema="reporting",
    )
    op.drop_index(
        "ix_reporting_dashboard_alert_rules_kpi_code",
        table_name="dashboard_alert_rules",
        schema="reporting",
    )
    op.drop_index(
        "ix_reporting_dashboard_alert_rules_dashboard_id",
        table_name="dashboard_alert_rules",
        schema="reporting",
    )
    op.drop_table("dashboard_alert_rules", schema="reporting")
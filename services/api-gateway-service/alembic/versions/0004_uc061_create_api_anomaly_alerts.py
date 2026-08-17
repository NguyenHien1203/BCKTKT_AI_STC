"""UC-061: create api_anomaly_alerts table
(Theo dõi mức sử dụng API + chỉ số — bước 3: lịch sử cảnh báo Alertmanager)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-14

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_anomaly_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fingerprint", sa.String(length=128), nullable=False, unique=True),
        sa.Column("alert_name", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("consumer_code", sa.String(length=100), nullable=True),
        sa.Column("endpoint_path", sa.String(length=500), nullable=True),
        sa.Column("labels_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("annotations_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_anomaly_alerts_fingerprint",
        "api_anomaly_alerts",
        ["fingerprint"],
        unique=True,
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_anomaly_alerts_alert_name",
        "api_anomaly_alerts",
        ["alert_name"],
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_anomaly_alerts_severity",
        "api_anomaly_alerts",
        ["severity"],
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_anomaly_alerts_status",
        "api_anomaly_alerts",
        ["status"],
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_anomaly_alerts_consumer_code",
        "api_anomaly_alerts",
        ["consumer_code"],
        schema="gateway",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_gateway_api_anomaly_alerts_consumer_code",
        table_name="api_anomaly_alerts",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_api_anomaly_alerts_status",
        table_name="api_anomaly_alerts",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_api_anomaly_alerts_severity",
        table_name="api_anomaly_alerts",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_api_anomaly_alerts_alert_name",
        table_name="api_anomaly_alerts",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_api_anomaly_alerts_fingerprint",
        table_name="api_anomaly_alerts",
        schema="gateway",
    )
    op.drop_table("api_anomaly_alerts", schema="gateway")
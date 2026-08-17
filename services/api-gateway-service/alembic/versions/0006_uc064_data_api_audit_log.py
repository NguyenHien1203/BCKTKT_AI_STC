"""UC-064: create schema audit + audit_log table, add api_keys.service_tier_code
(Cung cấp Data API cho IOC — kiểm tra khoá API + phạm vi + giới hạn tần
suất, ghi nhật ký lời gọi API vào audit.audit_log)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-17

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # UC-064: mã gói dịch vụ (ServiceTier.code, UC-060) áp giới hạn tần
    # suất khi khoá gọi Data API. NULL -> mặc định dùng gói "FREE".
    op.add_column(
        "api_keys",
        sa.Column("service_tier_code", sa.String(length=20), nullable=True),
        schema="gateway",
    )

    # Schema "audit" DÙNG CHUNG cho mọi loại API (Data/Search/QA/Metadata)
    # do api-gateway-service cung cấp — KHÁC schema "gateway" ở trên.
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("api_type", sa.String(length=20), nullable=False),
        sa.Column("endpoint_path", sa.String(length=500), nullable=False),
        sa.Column("consumer_code", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("api_key_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("request_params", sa.Text(), nullable=False, server_default=""),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("consumer_ip", sa.String(length=64), nullable=True),
        sa.Column("called_at", sa.DateTime(), nullable=True),
        schema="audit",
    )
    op.create_index(
        "ix_audit_audit_log_api_type", "audit_log", ["api_type"], schema="audit"
    )
    op.create_index(
        "ix_audit_audit_log_consumer_code", "audit_log", ["consumer_code"], schema="audit"
    )
    op.create_index(
        "ix_audit_audit_log_status", "audit_log", ["status"], schema="audit"
    )
    op.create_index(
        "ix_audit_audit_log_api_key_id", "audit_log", ["api_key_id"], schema="audit"
    )
    op.create_index(
        "ix_audit_audit_log_called_at", "audit_log", ["called_at"], schema="audit"
    )


def downgrade() -> None:
    op.drop_index("ix_audit_audit_log_called_at", table_name="audit_log", schema="audit")
    op.drop_index("ix_audit_audit_log_api_key_id", table_name="audit_log", schema="audit")
    op.drop_index("ix_audit_audit_log_status", table_name="audit_log", schema="audit")
    op.drop_index("ix_audit_audit_log_consumer_code", table_name="audit_log", schema="audit")
    op.drop_index("ix_audit_audit_log_api_type", table_name="audit_log", schema="audit")
    op.drop_table("audit_log", schema="audit")
    op.drop_column("api_keys", "service_tier_code", schema="gateway")
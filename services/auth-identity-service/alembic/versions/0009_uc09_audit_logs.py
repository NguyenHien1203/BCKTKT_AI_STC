"""UC-09: audit_logs (nhật ký truy cập và thao tác)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-28

"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("ip_address", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="SUCCESS"),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="identity",
    )
    op.create_index(
        "ix_identity_audit_logs_username", "audit_logs", ["username"], schema="identity"
    )
    op.create_index(
        "ix_identity_audit_logs_created_at", "audit_logs", ["created_at"], schema="identity"
    )


def downgrade() -> None:
    op.drop_index("ix_identity_audit_logs_created_at", table_name="audit_logs", schema="identity")
    op.drop_index("ix_identity_audit_logs_username", table_name="audit_logs", schema="identity")
    op.drop_table("audit_logs", schema="identity")
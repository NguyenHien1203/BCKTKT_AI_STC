"""UC-10: ai_audit_logs (Quản trị AI Audit Log)

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-28

"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trace_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("response", sa.Text(), nullable=False, server_default=""),
        sa.Column("sources", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("permission_snapshot", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("prompt_version", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="identity",
    )
    op.create_index(
        "ix_identity_ai_audit_logs_trace_id", "ai_audit_logs", ["trace_id"], schema="identity"
    )
    op.create_index(
        "ix_identity_ai_audit_logs_username", "ai_audit_logs", ["username"], schema="identity"
    )
    op.create_index(
        "ix_identity_ai_audit_logs_created_at", "ai_audit_logs", ["created_at"], schema="identity"
    )


def downgrade() -> None:
    op.drop_index("ix_identity_ai_audit_logs_created_at", table_name="ai_audit_logs", schema="identity")
    op.drop_index("ix_identity_ai_audit_logs_username", table_name="ai_audit_logs", schema="identity")
    op.drop_index("ix_identity_ai_audit_logs_trace_id", table_name="ai_audit_logs", schema="identity")
    op.drop_table("ai_audit_logs", schema="identity")
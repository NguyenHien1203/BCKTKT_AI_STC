"""UC-06: system_configs (cấu hình hệ thống chung)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-27

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "request_timeout_seconds", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column("max_upload_size_mb", sa.Integer(), nullable=False, server_default="50"),
        sa.Column(
            "default_language", sa.String(length=10), nullable=False, server_default="vi"
        ),
        sa.Column("updated_at", sa.String(length=40), nullable=False, server_default=""),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_table("system_configs", schema="identity")
"""add external_id column to users (đồng bộ IdP — Keycloak)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-27

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("external_id", sa.String(length=100), nullable=False, server_default=""),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_column("users", "external_id", schema="identity")

"""UC-015: create staging schema and sources table (Đăng ký và quản lý nguồn dữ liệu)

Revision ID: 0001
Revises:
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS staging")
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_system", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("owner", sa.String(length=255), nullable=False, server_default=""),
        sa.Column(
            "sensitivity_level",
            sa.String(length=20),
            nullable=False,
            server_default="INTERNAL",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema="staging",
    )
    op.create_index(
        "ix_staging_sources_code", "sources", ["code"], schema="staging"
    )
    op.create_index(
        "ix_staging_sources_source_system",
        "sources",
        ["source_system"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_sources_source_system", table_name="sources", schema="staging"
    )
    op.drop_index("ix_staging_sources_code", table_name="sources", schema="staging")
    op.drop_table("sources", schema="staging")
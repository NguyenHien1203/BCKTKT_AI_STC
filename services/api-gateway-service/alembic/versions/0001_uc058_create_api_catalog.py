"""UC-058: create gateway schema, api_catalog_entries + api_catalog_version_history
tables (Quản lý danh mục API)

Revision ID: 0001
Revises:
Create Date: 2026-08-13

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS gateway")

    op.create_table(
        "api_catalog_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=100), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("api_type", sa.String(length=20), nullable=False),
        sa.Column("endpoint_path", sa.String(length=500), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="PUBLISHED",
        ),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sunset_date", sa.Date(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("unpublished_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_catalog_entries_code",
        "api_catalog_entries",
        ["code"],
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_catalog_entries_api_type",
        "api_catalog_entries",
        ["api_type"],
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_catalog_entries_status",
        "api_catalog_entries",
        ["status"],
        schema="gateway",
    )

    op.create_table(
        "api_catalog_version_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entry_id",
            sa.Integer(),
            sa.ForeignKey("gateway.api_catalog_entries.id"),
            nullable=False,
        ),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("sunset_date", sa.Date(), nullable=True),
        sa.Column("change_note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_api_catalog_version_history_entry_id",
        "api_catalog_version_history",
        ["entry_id"],
        schema="gateway",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_gateway_api_catalog_version_history_entry_id",
        table_name="api_catalog_version_history",
        schema="gateway",
    )
    op.drop_table("api_catalog_version_history", schema="gateway")

    op.drop_index(
        "ix_gateway_api_catalog_entries_status",
        table_name="api_catalog_entries",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_api_catalog_entries_api_type",
        table_name="api_catalog_entries",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_api_catalog_entries_code",
        table_name="api_catalog_entries",
        schema="gateway",
    )
    op.drop_table("api_catalog_entries", schema="gateway")
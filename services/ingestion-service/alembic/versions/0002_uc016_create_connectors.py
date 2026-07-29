"""UC-016: create connectors table (Quản lý thư viện bộ kết nối)

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connectors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("connector_type", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("entry_point", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
        sa.Column(
            "interface_status",
            sa.String(length=20),
            nullable=False,
            server_default="PASSED",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("restart_count", sa.Integer(), nullable=False, server_default="0"),
        schema="staging",
    )
    op.create_index(
        "ix_staging_connectors_code", "connectors", ["code"], schema="staging"
    )
    op.create_index(
        "ix_staging_connectors_connector_type",
        "connectors",
        ["connector_type"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_connectors_connector_type", table_name="connectors", schema="staging"
    )
    op.drop_index("ix_staging_connectors_code", table_name="connectors", schema="staging")
    op.drop_table("connectors", schema="staging")
"""UC-017: create source_connections + credential_assets tables (Cấu hình kết nối nguồn)

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_connections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "data_source_id",
            sa.Integer(),
            sa.ForeignKey("staging.sources.id"),
            nullable=False,
        ),
        sa.Column("connection_type", sa.String(length=20), nullable=False),
        sa.Column("config", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "last_test_status", sa.String(length=20), nullable=False, server_default="UNTESTED"
        ),
        sa.Column("last_test_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_tested_at", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema="staging",
    )
    op.create_index(
        "ix_staging_source_connections_data_source_id",
        "source_connections",
        ["data_source_id"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_source_connections_connection_type",
        "source_connections",
        ["connection_type"],
        schema="staging",
    )

    op.create_table(
        "credential_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "connection_id",
            sa.Integer(),
            sa.ForeignKey("staging.source_connections.id"),
            nullable=False,
        ),
        sa.Column("asset_type", sa.String(length=20), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.String(length=40), nullable=False),
        sa.Column("expires_at", sa.String(length=40), nullable=False),
        sa.Column("rotation_period_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("rotated_at", sa.String(length=40), nullable=True),
        sa.Column("rotation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rotation_history", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema="staging",
    )
    op.create_index(
        "ix_staging_credential_assets_connection_id",
        "credential_assets",
        ["connection_id"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_credential_assets_asset_type",
        "credential_assets",
        ["asset_type"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_credential_assets_expires_at",
        "credential_assets",
        ["expires_at"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_credential_assets_expires_at", table_name="credential_assets", schema="staging"
    )
    op.drop_index(
        "ix_staging_credential_assets_asset_type", table_name="credential_assets", schema="staging"
    )
    op.drop_index(
        "ix_staging_credential_assets_connection_id",
        table_name="credential_assets",
        schema="staging",
    )
    op.drop_table("credential_assets", schema="staging")

    op.drop_index(
        "ix_staging_source_connections_connection_type",
        table_name="source_connections",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_source_connections_data_source_id",
        table_name="source_connections",
        schema="staging",
    )
    op.drop_table("source_connections", schema="staging")
"""UC-035: create asset_group_catalog + asset_group_catalog_versions +
asset_depreciation_rates (Quản lý danh mục nhóm tài sản)

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_group_catalog",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("regulation", sa.String(length=20), nullable=False),
        sa.Column("useful_life_years", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("effective_from", sa.String(length=40), nullable=True),
        sa.Column("effective_to", sa.String(length=40), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_unique_constraint(
        "uq_curated_asset_group_catalog_code",
        "asset_group_catalog",
        ["code"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_asset_group_catalog_code", "asset_group_catalog", ["code"], schema="curated"
    )
    op.create_index(
        "ix_curated_asset_group_catalog_regulation",
        "asset_group_catalog",
        ["regulation"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_asset_group_catalog_status",
        "asset_group_catalog",
        ["status"],
        schema="curated",
    )

    op.create_table(
        "asset_group_catalog_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("curated.asset_group_catalog.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("regulation", sa.String(length=20), nullable=False),
        sa.Column("useful_life_years", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_asset_group_catalog_versions_group_id",
        "asset_group_catalog_versions",
        ["group_id"],
        schema="curated",
    )

    op.create_table(
        "asset_depreciation_rates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "asset_group_id",
            sa.Integer(),
            sa.ForeignKey("curated.asset_group_catalog.id"),
            nullable=False,
        ),
        sa.Column("depreciation_rate_percent", sa.Float(), nullable=False),
        sa.Column("useful_life_years", sa.Integer(), nullable=True),
        sa.Column("effective_from", sa.String(length=40), nullable=True),
        sa.Column("effective_to", sa.String(length=40), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("declared_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_asset_depreciation_rates_asset_group_id",
        "asset_depreciation_rates",
        ["asset_group_id"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_asset_depreciation_rates_asset_group_id",
        table_name="asset_depreciation_rates",
        schema="curated",
    )
    op.drop_table("asset_depreciation_rates", schema="curated")

    op.drop_index(
        "ix_curated_asset_group_catalog_versions_group_id",
        table_name="asset_group_catalog_versions",
        schema="curated",
    )
    op.drop_table("asset_group_catalog_versions", schema="curated")

    op.drop_index(
        "ix_curated_asset_group_catalog_status",
        table_name="asset_group_catalog",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_asset_group_catalog_regulation",
        table_name="asset_group_catalog",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_asset_group_catalog_code", table_name="asset_group_catalog", schema="curated"
    )
    op.drop_constraint(
        "uq_curated_asset_group_catalog_code",
        "asset_group_catalog",
        schema="curated",
        type_="unique",
    )
    op.drop_table("asset_group_catalog", schema="curated")
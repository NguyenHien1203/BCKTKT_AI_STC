"""UC-033: create org_unit_catalog + org_unit_catalog_versions (Quản lý
danh mục đơn vị)

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_unit_catalog",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit_type", sa.String(length=20), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("effective_from", sa.String(length=40), nullable=True),
        sa.Column("effective_to", sa.String(length=40), nullable=True),
        sa.Column("lifecycle_action", sa.String(length=20), nullable=True),
        sa.Column("lifecycle_note", sa.Text(), nullable=True),
        sa.Column("split_from_id", sa.Integer(), nullable=True),
        sa.Column("merged_from_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_unique_constraint(
        "uq_curated_org_unit_catalog_code", "org_unit_catalog", ["code"], schema="curated"
    )
    op.create_index(
        "ix_curated_org_unit_catalog_code", "org_unit_catalog", ["code"], schema="curated"
    )
    op.create_index(
        "ix_curated_org_unit_catalog_parent_id",
        "org_unit_catalog",
        ["parent_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_org_unit_catalog_status", "org_unit_catalog", ["status"], schema="curated"
    )

    op.create_table(
        "org_unit_catalog_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "unit_id",
            sa.Integer(),
            sa.ForeignKey("curated.org_unit_catalog.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit_type", sa.String(length=20), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("effective_from", sa.String(length=40), nullable=True),
        sa.Column("effective_to", sa.String(length=40), nullable=True),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_org_unit_catalog_versions_unit_id",
        "org_unit_catalog_versions",
        ["unit_id"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_org_unit_catalog_versions_unit_id",
        table_name="org_unit_catalog_versions",
        schema="curated",
    )
    op.drop_table("org_unit_catalog_versions", schema="curated")

    op.drop_index(
        "ix_curated_org_unit_catalog_status", table_name="org_unit_catalog", schema="curated"
    )
    op.drop_index(
        "ix_curated_org_unit_catalog_parent_id", table_name="org_unit_catalog", schema="curated"
    )
    op.drop_index(
        "ix_curated_org_unit_catalog_code", table_name="org_unit_catalog", schema="curated"
    )
    op.drop_constraint(
        "uq_curated_org_unit_catalog_code",
        "org_unit_catalog",
        schema="curated",
        type_="unique",
    )
    op.drop_table("org_unit_catalog", schema="curated")
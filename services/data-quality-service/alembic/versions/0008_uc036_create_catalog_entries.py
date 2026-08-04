"""UC-036: create catalog_entries + catalog_entry_versions +
catalog_change_requests (Quản lý danh mục mặt hàng, loại văn bản, nguồn vốn)

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("catalog_type", sa.String(length=30), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("effective_from", sa.String(length=40), nullable=True),
        sa.Column("effective_to", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_unique_constraint(
        "uq_curated_catalog_entries_code_catalog_type",
        "catalog_entries",
        ["code", "catalog_type"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_catalog_entries_catalog_type",
        "catalog_entries",
        ["catalog_type"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_catalog_entries_code", "catalog_entries", ["code"], schema="curated"
    )
    op.create_index(
        "ix_curated_catalog_entries_status", "catalog_entries", ["status"], schema="curated"
    )

    op.create_table(
        "catalog_entry_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entry_id",
            sa.Integer(),
            sa.ForeignKey("curated.catalog_entries.id"),
            nullable=False,
        ),
        sa.Column("catalog_type", sa.String(length=30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_catalog_entry_versions_entry_id",
        "catalog_entry_versions",
        ["entry_id"],
        schema="curated",
    )

    op.create_table(
        "catalog_change_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entry_id",
            sa.Integer(),
            sa.ForeignKey("curated.catalog_entries.id"),
            nullable=False,
        ),
        sa.Column("catalog_type", sa.String(length=30), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("proposed_name", sa.String(length=255), nullable=True),
        sa.Column("proposed_unit", sa.String(length=50), nullable=True),
        sa.Column("proposed_description", sa.Text(), nullable=True),
        sa.Column("proposed_status", sa.String(length=20), nullable=True),
        sa.Column("proposed_is_sensitive", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_catalog_change_requests_entry_id",
        "catalog_change_requests",
        ["entry_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_catalog_change_requests_catalog_type",
        "catalog_change_requests",
        ["catalog_type"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_catalog_change_requests_status",
        "catalog_change_requests",
        ["status"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_catalog_change_requests_status",
        table_name="catalog_change_requests",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_catalog_change_requests_catalog_type",
        table_name="catalog_change_requests",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_catalog_change_requests_entry_id",
        table_name="catalog_change_requests",
        schema="curated",
    )
    op.drop_table("catalog_change_requests", schema="curated")

    op.drop_index(
        "ix_curated_catalog_entry_versions_entry_id",
        table_name="catalog_entry_versions",
        schema="curated",
    )
    op.drop_table("catalog_entry_versions", schema="curated")

    op.drop_index(
        "ix_curated_catalog_entries_status", table_name="catalog_entries", schema="curated"
    )
    op.drop_index(
        "ix_curated_catalog_entries_code", table_name="catalog_entries", schema="curated"
    )
    op.drop_index(
        "ix_curated_catalog_entries_catalog_type", table_name="catalog_entries", schema="curated"
    )
    op.drop_constraint(
        "uq_curated_catalog_entries_code_catalog_type",
        "catalog_entries",
        schema="curated",
        type_="unique",
    )
    op.drop_table("catalog_entries", schema="curated")
"""UC-034: create budget_item_catalog + budget_item_catalog_versions +
budget_item_change_requests (Quản lý danh mục khoản mục NSNN)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "budget_item_catalog",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("budget_year", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
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
        "uq_curated_budget_item_catalog_code_year",
        "budget_item_catalog",
        ["code", "budget_year"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_budget_item_catalog_code", "budget_item_catalog", ["code"], schema="curated"
    )
    op.create_index(
        "ix_curated_budget_item_catalog_budget_year",
        "budget_item_catalog",
        ["budget_year"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_budget_item_catalog_parent_id",
        "budget_item_catalog",
        ["parent_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_budget_item_catalog_status",
        "budget_item_catalog",
        ["status"],
        schema="curated",
    )

    op.create_table(
        "budget_item_catalog_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("curated.budget_item_catalog.id"),
            nullable=False,
        ),
        sa.Column("budget_year", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_budget_item_catalog_versions_item_id",
        "budget_item_catalog_versions",
        ["item_id"],
        schema="curated",
    )

    op.create_table(
        "budget_item_change_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("curated.budget_item_catalog.id"),
            nullable=False,
        ),
        sa.Column("budget_year", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("proposed_name", sa.String(length=255), nullable=True),
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
        "ix_curated_budget_item_change_requests_item_id",
        "budget_item_change_requests",
        ["item_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_budget_item_change_requests_status",
        "budget_item_change_requests",
        ["status"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_budget_item_change_requests_status",
        table_name="budget_item_change_requests",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_budget_item_change_requests_item_id",
        table_name="budget_item_change_requests",
        schema="curated",
    )
    op.drop_table("budget_item_change_requests", schema="curated")

    op.drop_index(
        "ix_curated_budget_item_catalog_versions_item_id",
        table_name="budget_item_catalog_versions",
        schema="curated",
    )
    op.drop_table("budget_item_catalog_versions", schema="curated")

    op.drop_index(
        "ix_curated_budget_item_catalog_status",
        table_name="budget_item_catalog",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_budget_item_catalog_parent_id",
        table_name="budget_item_catalog",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_budget_item_catalog_budget_year",
        table_name="budget_item_catalog",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_budget_item_catalog_code", table_name="budget_item_catalog", schema="curated"
    )
    op.drop_constraint(
        "uq_curated_budget_item_catalog_code_year",
        "budget_item_catalog",
        schema="curated",
        type_="unique",
    )
    op.drop_table("budget_item_catalog", schema="curated")
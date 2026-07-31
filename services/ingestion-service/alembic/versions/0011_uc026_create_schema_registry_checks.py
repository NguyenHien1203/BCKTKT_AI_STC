"""UC-026: create schema_registry_checks table (Kiểm tra Schema Registry)

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-31

"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schema_registry_checks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("staging.dataset_catalog.id"),
            nullable=False,
        ),
        sa.Column("registered_version", sa.Integer(), nullable=False),
        sa.Column("incoming_fields", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("added_fields", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("removed_fields", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("changed_type_fields", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("checked_at", sa.String(length=40), nullable=False),
        sa.Column(
            "ingestion_run_id",
            sa.Integer(),
            sa.ForeignKey("staging.ingestion_runs.id"),
            nullable=True,
        ),
        schema="staging",
    )
    op.create_index(
        "ix_staging_schema_registry_checks_dataset_id",
        "schema_registry_checks",
        ["dataset_id"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_schema_registry_checks_status",
        "schema_registry_checks",
        ["status"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_schema_registry_checks_ingestion_run_id",
        "schema_registry_checks",
        ["ingestion_run_id"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_schema_registry_checks_ingestion_run_id",
        table_name="schema_registry_checks",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_schema_registry_checks_status",
        table_name="schema_registry_checks",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_schema_registry_checks_dataset_id",
        table_name="schema_registry_checks",
        schema="staging",
    )
    op.drop_table("schema_registry_checks", schema="staging")
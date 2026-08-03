"""UC-031: create mapping tables (Ánh xạ trường sang dạng chuẩn)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-01

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mapping_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("field_name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rule_type", sa.String(length=20), nullable=False),
        sa.Column("catalog_map_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("normalize_case", sa.String(length=10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_mapping_rules_dataset_id", "mapping_rules", ["dataset_id"], schema="curated"
    )
    op.create_index(
        "ix_curated_mapping_rules_field_name", "mapping_rules", ["field_name"], schema="curated"
    )
    op.create_index(
        "ix_curated_mapping_rules_is_active", "mapping_rules", ["is_active"], schema="curated"
    )

    op.create_table(
        "mapping_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("parsing_job_id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="RECEIVED"),
        sa.Column("records_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_mapped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unmapped_values_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("log_entries_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("received_at", sa.String(length=40), nullable=False),
        sa.Column("completed_at", sa.String(length=40), nullable=True),
        schema="curated",
    )
    op.create_index(
        "ix_curated_mapping_jobs_parsing_job_id",
        "mapping_jobs",
        ["parsing_job_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_mapping_jobs_dataset_id", "mapping_jobs", ["dataset_id"], schema="curated"
    )
    op.create_index(
        "ix_curated_mapping_jobs_status", "mapping_jobs", ["status"], schema="curated"
    )

    op.create_table(
        "mapping_rejections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "mapping_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.mapping_jobs.id"),
            nullable=False,
        ),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("rejected_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_mapping_rejections_mapping_job_id",
        "mapping_rejections",
        ["mapping_job_id"],
        schema="curated",
    )

    op.create_table(
        "unmapped_value_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "mapping_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.mapping_jobs.id"),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=255), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_unmapped_value_queue_mapping_job_id",
        "unmapped_value_queue",
        ["mapping_job_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_unmapped_value_queue_dataset_id",
        "unmapped_value_queue",
        ["dataset_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_unmapped_value_queue_status",
        "unmapped_value_queue",
        ["status"],
        schema="curated",
    )

    op.create_table(
        "mapped_standard_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "mapping_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.mapping_jobs.id"),
            nullable=False,
        ),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("standardized_fields_json", sa.Text(), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_mapped_standard_records_mapping_job_id",
        "mapped_standard_records",
        ["mapping_job_id"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_mapped_standard_records_mapping_job_id",
        table_name="mapped_standard_records",
        schema="curated",
    )
    op.drop_table("mapped_standard_records", schema="curated")

    op.drop_index(
        "ix_curated_unmapped_value_queue_status", table_name="unmapped_value_queue", schema="curated"
    )
    op.drop_index(
        "ix_curated_unmapped_value_queue_dataset_id",
        table_name="unmapped_value_queue",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_unmapped_value_queue_mapping_job_id",
        table_name="unmapped_value_queue",
        schema="curated",
    )
    op.drop_table("unmapped_value_queue", schema="curated")

    op.drop_index(
        "ix_curated_mapping_rejections_mapping_job_id",
        table_name="mapping_rejections",
        schema="curated",
    )
    op.drop_table("mapping_rejections", schema="curated")

    op.drop_index("ix_curated_mapping_jobs_status", table_name="mapping_jobs", schema="curated")
    op.drop_index(
        "ix_curated_mapping_jobs_dataset_id", table_name="mapping_jobs", schema="curated"
    )
    op.drop_index(
        "ix_curated_mapping_jobs_parsing_job_id", table_name="mapping_jobs", schema="curated"
    )
    op.drop_table("mapping_jobs", schema="curated")

    op.drop_index(
        "ix_curated_mapping_rules_is_active", table_name="mapping_rules", schema="curated"
    )
    op.drop_index(
        "ix_curated_mapping_rules_field_name", table_name="mapping_rules", schema="curated"
    )
    op.drop_index(
        "ix_curated_mapping_rules_dataset_id", table_name="mapping_rules", schema="curated"
    )
    op.drop_table("mapping_rules", schema="curated")
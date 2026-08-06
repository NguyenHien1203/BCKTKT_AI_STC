"""UC-041: create curated_publish_jobs + dm_records + curated_batch_summaries +
curated_dataset_freshness (Công bố vào kho chuẩn hoá + batch_summary)

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "curated_publish_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "quality_check_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.quality_check_jobs.id"),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("mapping_job_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="uc039_quality_check"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="RECEIVED"),
        sa.Column("records_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("batch_summary_id", sa.Integer(), nullable=True),
        sa.Column(
            "published_event_published", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("log_entries_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("received_at", sa.String(length=40), nullable=False),
        sa.Column("completed_at", sa.String(length=40), nullable=True),
        schema="curated",
    )
    op.create_index(
        "ix_curated_curated_publish_jobs_quality_check_job_id",
        "curated_publish_jobs",
        ["quality_check_job_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_curated_publish_jobs_dataset_id",
        "curated_publish_jobs",
        ["dataset_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_curated_publish_jobs_status",
        "curated_publish_jobs",
        ["status"],
        schema="curated",
    )

    op.create_table(
        "dm_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("standardized_fields_json", sa.Text(), nullable=False),
        sa.Column("publish_status", sa.String(length=20), nullable=False, server_default="approved"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("curated_publish_job_id", sa.Integer(), nullable=True),
        sa.Column("quality_check_job_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="uc039_quality_check"),
        sa.Column("first_published_at", sa.String(length=40), nullable=False),
        sa.Column("last_published_at", sa.String(length=40), nullable=False),
        sa.UniqueConstraint("dataset_id", "row_index", name="uq_dm_records_dataset_row"),
        schema="curated",
    )
    op.create_index(
        "ix_curated_dm_records_dataset_id", "dm_records", ["dataset_id"], schema="curated"
    )
    op.create_index(
        "ix_curated_dm_records_publish_status",
        "dm_records",
        ["publish_status"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_dm_records_curated_publish_job_id",
        "dm_records",
        ["curated_publish_job_id"],
        schema="curated",
    )

    op.create_table(
        "curated_batch_summaries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "curated_publish_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.curated_publish_jobs.id"),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("quality_check_job_id", sa.Integer(), nullable=False),
        sa.Column("mapping_job_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="uc039_quality_check"),
        sa.Column("records_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_curated_batch_summaries_publish_job_id",
        "curated_batch_summaries",
        ["curated_publish_job_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_curated_batch_summaries_dataset_id",
        "curated_batch_summaries",
        ["dataset_id"],
        schema="curated",
    )

    op.create_table(
        "curated_dataset_freshness",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("last_batch_summary_id", sa.Integer(), nullable=True),
        sa.Column("last_published_at", sa.String(length=40), nullable=False),
        sa.Column("total_published_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        sa.UniqueConstraint("dataset_id", name="uq_curated_dataset_freshness_dataset"),
        schema="curated",
    )


def downgrade() -> None:
    op.drop_table("curated_dataset_freshness", schema="curated")

    op.drop_index(
        "ix_curated_curated_batch_summaries_dataset_id",
        table_name="curated_batch_summaries",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_curated_batch_summaries_publish_job_id",
        table_name="curated_batch_summaries",
        schema="curated",
    )
    op.drop_table("curated_batch_summaries", schema="curated")

    op.drop_index("ix_curated_dm_records_curated_publish_job_id", table_name="dm_records", schema="curated")
    op.drop_index("ix_curated_dm_records_publish_status", table_name="dm_records", schema="curated")
    op.drop_index("ix_curated_dm_records_dataset_id", table_name="dm_records", schema="curated")
    op.drop_table("dm_records", schema="curated")

    op.drop_index(
        "ix_curated_curated_publish_jobs_status",
        table_name="curated_publish_jobs",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_curated_publish_jobs_dataset_id",
        table_name="curated_publish_jobs",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_curated_publish_jobs_quality_check_job_id",
        table_name="curated_publish_jobs",
        schema="curated",
    )
    op.drop_table("curated_publish_jobs", schema="curated")
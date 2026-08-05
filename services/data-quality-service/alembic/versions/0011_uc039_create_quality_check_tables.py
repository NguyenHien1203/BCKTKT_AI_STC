"""UC-039: create quality_check_jobs + quality_check_rule_results +
quality_published_records + quality_exception_queue (Chạy kiểm tra
chất lượng dữ liệu)

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_check_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "mapping_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.mapping_jobs.id"),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="RECEIVED"),
        sa.Column("pass_threshold", sa.Float(), nullable=False, server_default="0"),
        sa.Column("records_checked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rule_type_scores_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("published_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exception_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "publish_event_published", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "exception_event_published", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("log_entries_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("received_at", sa.String(length=40), nullable=False),
        sa.Column("completed_at", sa.String(length=40), nullable=True),
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_check_jobs_mapping_job_id",
        "quality_check_jobs",
        ["mapping_job_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_check_jobs_dataset_id",
        "quality_check_jobs",
        ["dataset_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_check_jobs_status",
        "quality_check_jobs",
        ["status"],
        schema="curated",
    )

    op.create_table(
        "quality_check_rule_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "quality_check_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.quality_check_jobs.id"),
            nullable=False,
        ),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        sa.Column("rule_type", sa.String(length=20), nullable=False),
        sa.Column("field_names_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("total_checked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pass_rate", sa.Float(), nullable=False, server_default="100"),
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_check_rule_results_job_id",
        "quality_check_rule_results",
        ["quality_check_job_id"],
        schema="curated",
    )

    op.create_table(
        "quality_published_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "quality_check_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.quality_check_jobs.id"),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("standardized_fields_json", sa.Text(), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_published_records_job_id",
        "quality_published_records",
        ["quality_check_job_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_published_records_dataset_id",
        "quality_published_records",
        ["dataset_id"],
        schema="curated",
    )

    op.create_table(
        "quality_exception_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "quality_check_job_id",
            sa.Integer(),
            sa.ForeignKey("curated.quality_check_jobs.id"),
            nullable=False,
        ),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("standardized_fields_json", sa.Text(), nullable=False),
        sa.Column("failed_rules_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_exception_queue_job_id",
        "quality_exception_queue",
        ["quality_check_job_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_exception_queue_dataset_id",
        "quality_exception_queue",
        ["dataset_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_quality_exception_queue_status",
        "quality_exception_queue",
        ["status"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_quality_exception_queue_status",
        table_name="quality_exception_queue",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_quality_exception_queue_dataset_id",
        table_name="quality_exception_queue",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_quality_exception_queue_job_id",
        table_name="quality_exception_queue",
        schema="curated",
    )
    op.drop_table("quality_exception_queue", schema="curated")

    op.drop_index(
        "ix_curated_quality_published_records_dataset_id",
        table_name="quality_published_records",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_quality_published_records_job_id",
        table_name="quality_published_records",
        schema="curated",
    )
    op.drop_table("quality_published_records", schema="curated")

    op.drop_index(
        "ix_curated_quality_check_rule_results_job_id",
        table_name="quality_check_rule_results",
        schema="curated",
    )
    op.drop_table("quality_check_rule_results", schema="curated")

    op.drop_index(
        "ix_curated_quality_check_jobs_status",
        table_name="quality_check_jobs",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_quality_check_jobs_dataset_id",
        table_name="quality_check_jobs",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_quality_check_jobs_mapping_job_id",
        table_name="quality_check_jobs",
        schema="curated",
    )
    op.drop_table("quality_check_jobs", schema="curated")
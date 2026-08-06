"""UC-043: create semantic_indicators + semantic_indicator_versions +
indicator_test_runs + indicator_audit_logs (Định nghĩa chỉ tiêu trong
Lớp ngữ nghĩa)

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "semantic_indicators",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_unique_constraint(
        "uq_semantic_indicators_name",
        "semantic_indicators",
        ["name"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_semantic_indicators_domain",
        "semantic_indicators",
        ["domain"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_semantic_indicators_status",
        "semantic_indicators",
        ["status"],
        schema="curated",
    )

    op.create_table(
        "semantic_indicator_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "indicator_id",
            sa.Integer(),
            sa.ForeignKey("curated.semantic_indicators.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.String(length=255), nullable=True),
        sa.Column("changed_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_semantic_indicator_versions_indicator_id",
        "semantic_indicator_versions",
        ["indicator_id"],
        schema="curated",
    )

    op.create_table(
        "indicator_test_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "indicator_id",
            sa.Integer(),
            sa.ForeignKey("curated.semantic_indicators.id"),
            nullable=False,
        ),
        sa.Column("expression_snapshot", sa.Text(), nullable=False),
        sa.Column("sample_rows_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result_value", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("tested_by", sa.String(length=255), nullable=True),
        sa.Column("tested_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_indicator_test_runs_indicator_id",
        "indicator_test_runs",
        ["indicator_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_indicator_test_runs_status",
        "indicator_test_runs",
        ["status"],
        schema="curated",
    )

    op.create_table(
        "indicator_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "indicator_id",
            sa.Integer(),
            sa.ForeignKey("curated.semantic_indicators.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_indicator_audit_logs_indicator_id",
        "indicator_audit_logs",
        ["indicator_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_indicator_audit_logs_action",
        "indicator_audit_logs",
        ["action"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_indicator_audit_logs_action",
        table_name="indicator_audit_logs",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_indicator_audit_logs_indicator_id",
        table_name="indicator_audit_logs",
        schema="curated",
    )
    op.drop_table("indicator_audit_logs", schema="curated")

    op.drop_index(
        "ix_curated_indicator_test_runs_status",
        table_name="indicator_test_runs",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_indicator_test_runs_indicator_id",
        table_name="indicator_test_runs",
        schema="curated",
    )
    op.drop_table("indicator_test_runs", schema="curated")

    op.drop_index(
        "ix_curated_semantic_indicator_versions_indicator_id",
        table_name="semantic_indicator_versions",
        schema="curated",
    )
    op.drop_table("semantic_indicator_versions", schema="curated")

    op.drop_index(
        "ix_curated_semantic_indicators_status",
        table_name="semantic_indicators",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_semantic_indicators_domain",
        table_name="semantic_indicators",
        schema="curated",
    )
    op.drop_constraint(
        "uq_semantic_indicators_name",
        "semantic_indicators",
        schema="curated",
        type_="unique",
    )
    op.drop_table("semantic_indicators", schema="curated")
"""UC-044: Phê duyệt chỉ tiêu -- thêm cột indicator_status_snapshot vào
indicator_test_runs (UC-043) + tạo bảng indicator_approval_decisions

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "indicator_test_runs",
        sa.Column("indicator_status_snapshot", sa.String(length=20), nullable=True),
        schema="curated",
    )

    op.create_table(
        "indicator_approval_decisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "indicator_id",
            sa.Integer(),
            sa.ForeignKey("curated.semantic_indicators.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("decided_by", sa.String(length=255), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("comparison_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="curated",
    )
    op.create_index(
        "ix_curated_indicator_approval_decisions_indicator_id",
        "indicator_approval_decisions",
        ["indicator_id"],
        schema="curated",
    )
    op.create_index(
        "ix_curated_indicator_approval_decisions_action",
        "indicator_approval_decisions",
        ["action"],
        schema="curated",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curated_indicator_approval_decisions_action",
        table_name="indicator_approval_decisions",
        schema="curated",
    )
    op.drop_index(
        "ix_curated_indicator_approval_decisions_indicator_id",
        table_name="indicator_approval_decisions",
        schema="curated",
    )
    op.drop_table("indicator_approval_decisions", schema="curated")

    op.drop_column("indicator_test_runs", "indicator_status_snapshot", schema="curated")
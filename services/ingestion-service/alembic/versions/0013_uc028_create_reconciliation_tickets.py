"""UC-028: create reconciliation_tickets table (Xử lý ticket đối soát với chủ quản nguồn)

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-31

"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_tickets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "reconciliation_id",
            sa.Integer(),
            sa.ForeignKey("staging.intake_reconciliations.id"),
            nullable=False,
        ),
        sa.Column("source_owner", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("history", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("opened_by", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("opened_at", sa.String(length=40), nullable=False),
        sa.Column("notified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("closed_by", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("closed_at", sa.String(length=40), nullable=True),
        sa.Column("close_note", sa.Text(), nullable=False, server_default=""),
        schema="staging",
    )
    op.create_index(
        "ix_staging_reconciliation_tickets_reconciliation_id",
        "reconciliation_tickets",
        ["reconciliation_id"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_reconciliation_tickets_status",
        "reconciliation_tickets",
        ["status"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_reconciliation_tickets_status",
        table_name="reconciliation_tickets",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_reconciliation_tickets_reconciliation_id",
        table_name="reconciliation_tickets",
        schema="staging",
    )
    op.drop_table("reconciliation_tickets", schema="staging")
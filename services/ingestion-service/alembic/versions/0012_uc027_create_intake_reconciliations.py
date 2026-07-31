"""UC-027: create intake_reconciliations table (Đối soát phiên intake)

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-31

"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intake_reconciliations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("staging.tabmis_intake_sessions.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("control_totals", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("findings", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("reconciled_by", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("opened_at", sa.String(length=40), nullable=False),
        sa.Column("closed_by", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("closed_at", sa.String(length=40), nullable=True),
        sa.Column("close_note", sa.Text(), nullable=False, server_default=""),
        schema="staging",
    )
    op.create_index(
        "ix_staging_intake_reconciliations_session_id",
        "intake_reconciliations",
        ["session_id"],
        schema="staging",
    )
    op.create_index(
        "ix_staging_intake_reconciliations_status",
        "intake_reconciliations",
        ["status"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_intake_reconciliations_status",
        table_name="intake_reconciliations",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_intake_reconciliations_session_id",
        table_name="intake_reconciliations",
        schema="staging",
    )
    op.drop_table("intake_reconciliations", schema="staging")
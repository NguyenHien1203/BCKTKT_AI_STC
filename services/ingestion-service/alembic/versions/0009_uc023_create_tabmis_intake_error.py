"""UC-023: create tabmis_intake_row_errors table (Xem trạng thái + sửa lỗi intake TABMIS)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tabmis_intake_row_errors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("staging.tabmis_intake_sessions.id"),
            nullable=False,
        ),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        schema="staging",
    )
    op.create_index(
        "ix_staging_tabmis_intake_row_errors_session_id",
        "tabmis_intake_row_errors",
        ["session_id"],
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_tabmis_intake_row_errors_session_id",
        table_name="tabmis_intake_row_errors",
        schema="staging",
    )
    op.drop_table("tabmis_intake_row_errors", schema="staging")
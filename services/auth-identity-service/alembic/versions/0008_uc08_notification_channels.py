"""UC-08: notification_channels (cấu hình kênh thông báo SMTP/SMS/Webhook)

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-27

"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_channels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("channel_type", sa.String(length=20), nullable=False, unique=True),
        sa.Column("config", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_test_at", sa.String(length=40), nullable=True),
        sa.Column("last_test_message", sa.Text(), nullable=False, server_default=""),
        schema="identity",
    )
    op.create_index(
        "ix_identity_notification_channels_channel_type",
        "notification_channels",
        ["channel_type"],
        schema="identity",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_notification_channels_channel_type",
        table_name="notification_channels",
        schema="identity",
    )
    op.drop_table("notification_channels", schema="identity")
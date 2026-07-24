"""UC-03 (vòng đời người dùng) + UC-12 (đăng nhập/đăng xuất)

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-24

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=False, server_default=""),
        schema="identity",
    )
    op.add_column(
        "users",
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="identity",
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("token", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="identity",
    )
    op.create_index(
        "ix_identity_user_sessions_token", "user_sessions", ["token"], schema="identity"
    )
    op.create_index(
        "ix_identity_user_sessions_user_id", "user_sessions", ["user_id"], schema="identity"
    )

    op.create_table(
        "org_unit_assignment_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
        ),
        sa.Column("old_org_unit_id", sa.Integer(), nullable=True),
        sa.Column("new_org_unit_id", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.String(length=40), nullable=False),
        schema="identity",
    )
    op.create_index(
        "ix_identity_org_unit_assignment_history_user_id",
        "org_unit_assignment_history",
        ["user_id"],
        schema="identity",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_org_unit_assignment_history_user_id",
        table_name="org_unit_assignment_history",
        schema="identity",
    )
    op.drop_table("org_unit_assignment_history", schema="identity")

    op.drop_index(
        "ix_identity_user_sessions_user_id", table_name="user_sessions", schema="identity"
    )
    op.drop_index("ix_identity_user_sessions_token", table_name="user_sessions", schema="identity")
    op.drop_table("user_sessions", schema="identity")

    op.drop_column("users", "is_locked", schema="identity")
    op.drop_column("users", "password_hash", schema="identity")

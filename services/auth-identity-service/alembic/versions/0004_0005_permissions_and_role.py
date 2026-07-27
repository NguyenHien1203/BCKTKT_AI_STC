"""UC-05 (roles) + UC-04 (user_permission_contexts)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-27

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("permissions", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        schema="identity",
    )
    op.create_index("ix_identity_roles_code", "roles", ["code"], schema="identity")

    op.create_table(
        "user_permission_contexts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("role_code", sa.String(length=50), nullable=False),
        sa.Column("permitted_domains", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("permitted_unit_id", sa.Integer(), nullable=True),
        sa.Column(
            "sensitivity_level", sa.String(length=20), nullable=False, server_default="INTERNAL"
        ),
        schema="identity",
    )
    op.create_index(
        "ix_identity_user_permission_contexts_user_id",
        "user_permission_contexts",
        ["user_id"],
        schema="identity",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_user_permission_contexts_user_id",
        table_name="user_permission_contexts",
        schema="identity",
    )
    op.drop_table("user_permission_contexts", schema="identity")
    op.drop_index("ix_identity_roles_code", table_name="roles", schema="identity")
    op.drop_table("roles", schema="identity")
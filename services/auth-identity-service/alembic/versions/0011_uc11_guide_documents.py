"""UC-11: guide_documents, guide_document_versions (Quản trị tài liệu hướng dẫn sử dụng)

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-28

"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guide_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("file_key", sa.String(length=500), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("uploaded_by", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        schema="identity",
    )

    op.create_table(
        "guide_document_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("identity.guide_documents.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("file_key", sa.String(length=500), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        schema="identity",
    )
    op.create_index(
        "ix_identity_guide_document_versions_document_id",
        "guide_document_versions",
        ["document_id"],
        schema="identity",
    )
    op.create_index(
        "ix_identity_guide_document_versions_created_at",
        "guide_document_versions",
        ["created_at"],
        schema="identity",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_guide_document_versions_created_at",
        table_name="guide_document_versions",
        schema="identity",
    )
    op.drop_index(
        "ix_identity_guide_document_versions_document_id",
        table_name="guide_document_versions",
        schema="identity",
    )
    op.drop_table("guide_document_versions", schema="identity")
    op.drop_table("guide_documents", schema="identity")
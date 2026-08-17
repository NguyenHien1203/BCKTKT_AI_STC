"""UC-062: create mtls_certificates + certificate_revocation_entries tables
(Quản lý chứng thư / mTLS cho đơn vị khai thác — kho tin cậy + CRL)

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-17

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mtls_certificates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("consumer_code", sa.String(length=100), nullable=False),
        sa.Column("consumer_name", sa.String(length=255), nullable=False),
        sa.Column("common_name", sa.String(length=255), nullable=False),
        sa.Column("serial_number", sa.String(length=128), nullable=False, unique=True),
        sa.Column("pem_certificate", sa.Text(), nullable=False),
        sa.Column("fingerprint_sha256", sa.String(length=128), nullable=False),
        sa.Column("not_before", sa.DateTime(), nullable=False),
        sa.Column("not_after", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("registered_at", sa.DateTime(), nullable=True),
        sa.Column("rotated_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "previous_certificate_id",
            sa.Integer(),
            sa.ForeignKey("gateway.mtls_certificates.id"),
            nullable=True,
        ),
        sa.Column(
            "rotated_to_id",
            sa.Integer(),
            sa.ForeignKey("gateway.mtls_certificates.id"),
            nullable=True,
        ),
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_mtls_certificates_consumer_code",
        "mtls_certificates",
        ["consumer_code"],
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_mtls_certificates_serial_number",
        "mtls_certificates",
        ["serial_number"],
        unique=True,
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_mtls_certificates_fingerprint_sha256",
        "mtls_certificates",
        ["fingerprint_sha256"],
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_mtls_certificates_status",
        "mtls_certificates",
        ["status"],
        schema="gateway",
    )

    op.create_table(
        "certificate_revocation_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "certificate_id",
            sa.Integer(),
            sa.ForeignKey("gateway.mtls_certificates.id"),
            nullable=False,
        ),
        sa.Column("consumer_code", sa.String(length=100), nullable=False),
        sa.Column("serial_number", sa.String(length=128), nullable=False, unique=True),
        sa.Column("fingerprint_sha256", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_certificate_revocation_entries_certificate_id",
        "certificate_revocation_entries",
        ["certificate_id"],
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_certificate_revocation_entries_consumer_code",
        "certificate_revocation_entries",
        ["consumer_code"],
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_certificate_revocation_entries_serial_number",
        "certificate_revocation_entries",
        ["serial_number"],
        unique=True,
        schema="gateway",
    )
    op.create_index(
        "ix_gateway_certificate_revocation_entries_fingerprint_sha256",
        "certificate_revocation_entries",
        ["fingerprint_sha256"],
        schema="gateway",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_gateway_certificate_revocation_entries_fingerprint_sha256",
        table_name="certificate_revocation_entries",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_certificate_revocation_entries_serial_number",
        table_name="certificate_revocation_entries",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_certificate_revocation_entries_consumer_code",
        table_name="certificate_revocation_entries",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_certificate_revocation_entries_certificate_id",
        table_name="certificate_revocation_entries",
        schema="gateway",
    )
    op.drop_table("certificate_revocation_entries", schema="gateway")

    op.drop_index(
        "ix_gateway_mtls_certificates_status",
        table_name="mtls_certificates",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_mtls_certificates_fingerprint_sha256",
        table_name="mtls_certificates",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_mtls_certificates_serial_number",
        table_name="mtls_certificates",
        schema="gateway",
    )
    op.drop_index(
        "ix_gateway_mtls_certificates_consumer_code",
        table_name="mtls_certificates",
        schema="gateway",
    )
    op.drop_table("mtls_certificates", schema="gateway")
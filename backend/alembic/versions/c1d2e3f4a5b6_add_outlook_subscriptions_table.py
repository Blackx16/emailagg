"""Add outlook_subscriptions table

Revision ID: c1d2e3f4a5b6
Revises: b5f2c7d9a101
Create Date: 2026-07-07 03:31:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b5f2c7d9a101"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Create the Postgres ENUM type explicitly (required before the column can reference it)
    outlook_subscription_status_enum = sa.Enum(
        "active", "expired", "failed", "cancelled",
        name="outlook_subscription_status_enum",
    )
    outlook_subscription_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "outlook_subscriptions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "mail_account_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mail_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subscription_id", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "resource",
            sa.String(255),
            nullable=False,
            server_default="me/mailFolders/inbox/messages",
        ),
        # Fernet-encrypted random client_state secret — never stored as plaintext
        sa.Column("client_state_encrypted", sa.Text(), nullable=False),
        sa.Column("expiration_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "expired", "failed", "cancelled", name="outlook_subscription_status_enum"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("renewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )

    # Index on mail_account_id for FK-side joins
    op.create_index(
        "ix_outlook_subscriptions_mail_account_id",
        "outlook_subscriptions",
        ["mail_account_id"],
    )

    # Partial index: only active subscriptions need fast expiry lookups for renewal
    op.create_index(
        "ix_outlook_subscriptions_expiration_active",
        "outlook_subscriptions",
        ["expiration_datetime"],
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("ix_outlook_subscriptions_expiration_active", table_name="outlook_subscriptions")
    op.drop_index("ix_outlook_subscriptions_mail_account_id", table_name="outlook_subscriptions")
    op.drop_table("outlook_subscriptions")
    # Postgres does NOT auto-drop enum types when a table is dropped —
    # must be done explicitly to allow clean re-upgrade.
    op.execute("DROP TYPE IF EXISTS outlook_subscription_status_enum")

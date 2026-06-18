"""alter forward_enabled default to true

Revision ID: f6a9b4d8c7e3
Revises: e0a0ad9a1987
Create Date: 2026-06-18 15:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a9b4d8c7e3'
down_revision: Union[str, None] = 'e0a0ad9a1987'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('mail_accounts', 'forward_enabled', server_default=sa.text('true'))


def downgrade() -> None:
    op.alter_column('mail_accounts', 'forward_enabled', server_default=sa.text('false'))

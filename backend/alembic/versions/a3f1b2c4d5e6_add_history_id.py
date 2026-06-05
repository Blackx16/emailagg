"""add history_id to mail_accounts

Revision ID: a3f1b2c4d5e6
Revises: 40cb5140c653
Create Date: 2026-06-06 02:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f1b2c4d5e6'
down_revision: Union[str, None] = '40cb5140c653'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mail_accounts', sa.Column('history_id', sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column('mail_accounts', 'history_id')

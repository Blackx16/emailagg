"""add body_html and body_text columns to emails

Revision ID: d4e5f6a7b8c9
Revises: f6a9b4d8c7e3
Create Date: 2026-07-07 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('emails', sa.Column('body_html', sa.Text(), nullable=True))
    op.add_column('emails', sa.Column('body_text', sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column('emails', 'body_text')
    op.drop_column('emails', 'body_html')

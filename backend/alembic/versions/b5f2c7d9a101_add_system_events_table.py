"""add system_events table

Revision ID: b5f2c7d9a101
Revises: f6a9b4d8c7e3
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b5f2c7d9a101'
down_revision: Union[str, None] = 'f6a9b4d8c7e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('system_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('service', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), server_default='info', nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('worker', sa.String(length=100), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('metadata_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_events_event_type'), 'system_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_system_events_service'), 'system_events', ['service'], unique=False)
    op.create_index(op.f('ix_system_events_severity'), 'system_events', ['severity'], unique=False)
    op.create_index(op.f('ix_system_events_timestamp'), 'system_events', ['timestamp'], unique=False)
    op.create_index(op.f('ix_system_events_user_id'), 'system_events', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_system_events_user_id'), table_name='system_events')
    op.drop_index(op.f('ix_system_events_timestamp'), table_name='system_events')
    op.drop_index(op.f('ix_system_events_severity'), table_name='system_events')
    op.drop_index(op.f('ix_system_events_service'), table_name='system_events')
    op.drop_index(op.f('ix_system_events_event_type'), table_name='system_events')
    op.drop_table('system_events')

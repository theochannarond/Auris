"""add transcriptions table

Revision ID: a1c4f7e93b02
Revises: 032384d2b5e5
Create Date: 2026-07-30 17:12:04.118305

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1c4f7e93b02'
down_revision: Union[str, None] = '032384d2b5e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('transcriptions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('meeting_id', sa.UUID(), nullable=False),
    sa.Column('audio_file_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=True),
    sa.Column('language', sa.String(length=10), nullable=True),
    sa.Column('model', sa.String(length=50), nullable=True),
    sa.Column('processing_ms', sa.Integer(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['audio_file_id'], ['audio_files.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transcriptions_meeting_id', 'transcriptions', ['meeting_id'])


def downgrade() -> None:
    op.drop_index('ix_transcriptions_meeting_id', table_name='transcriptions')
    op.drop_table('transcriptions')

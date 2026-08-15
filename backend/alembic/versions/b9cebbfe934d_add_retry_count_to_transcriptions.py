"""add retry_count to transcriptions

Revision ID: b9cebbfe934d
Revises: 47068897e2b0
Create Date: 2026-08-13 19:48:48.971524

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b9cebbfe934d'
down_revision: Union[str, None] = '47068897e2b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'transcriptions',
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    op.drop_column('transcriptions', 'retry_count')
"""add vexa identifiers to meetings

Revision ID: c4e17a9b30f2
Revises: 0b9a80712785
Create Date: 2026-08-30 12:10:00.000000

Les webhooks Vexa transportent SON identifiant de réunion (un entier, ex. 27246)
et non nos UUID. Sans ces colonnes, un événement entrant ne peut être rattaché
à aucune réunion Auris — c'est ce qui manquait pour que le mode vidéo aboutisse.

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c4e17a9b30f2'
down_revision: Union[str, None] = '0b9a80712785'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('meetings', sa.Column('vexa_meeting_id', sa.Integer(), nullable=True))
    op.add_column('meetings', sa.Column('vexa_platform',   sa.String(length=30),  nullable=True))
    op.add_column('meetings', sa.Column('vexa_native_id',  sa.String(length=100), nullable=True))
    # Index : chaque webhook entrant fait une recherche sur cette colonne
    op.create_index('ix_meetings_vexa_meeting_id', 'meetings', ['vexa_meeting_id'])


def downgrade() -> None:
    op.drop_index('ix_meetings_vexa_meeting_id', table_name='meetings')
    op.drop_column('meetings', 'vexa_native_id')
    op.drop_column('meetings', 'vexa_platform')
    op.drop_column('meetings', 'vexa_meeting_id')

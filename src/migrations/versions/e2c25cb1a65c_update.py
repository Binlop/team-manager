"""update

Revision ID: e2c25cb1a65c
Revises: 351b463f80ae
Create Date: 2026-11-18 16:39:31.623232

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e2c25cb1a65c'
down_revision: Union[str, Sequence[str], None] = '351b463f80ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Таблица и связанные объекты: user_meetting -> user_meeting
    op.rename_table('user_meetting', 'user_meeting')
    op.execute('ALTER SEQUENCE user_meetting_id_seq RENAME TO user_meeting_id_seq')
    op.execute('ALTER INDEX user_meetting_pkey RENAME TO user_meeting_pkey')
    op.execute('ALTER TABLE user_meeting RENAME CONSTRAINT user_meetting_meeting_id_fkey TO user_meeting_meeting_id_fkey')
    op.execute('ALTER TABLE user_meeting RENAME CONSTRAINT user_meetting_user_id_fkey TO user_meeting_user_id_fkey')

    # Индекс по meeting_id остаётся, но с новым именем
    op.execute('ALTER INDEX ix_user_meetting_meeting_id RENAME TO ix_user_meeting_meeting_id')

    # Индекс по user_id больше не нужен: его покрывает uq_user_meeting (user_id, meeting_id)
    op.drop_index('ix_user_meetting_user_id', table_name='user_meeting')

    # uq_user_meeting уже называется правильно, трогать не нужно


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index('ix_user_meetting_user_id', 'user_meeting', ['user_id'], unique=False)

    op.execute('ALTER INDEX ix_user_meeting_meeting_id RENAME TO ix_user_meetting_meeting_id')

    op.execute('ALTER TABLE user_meeting RENAME CONSTRAINT user_meeting_user_id_fkey TO user_meetting_user_id_fkey')
    op.execute('ALTER TABLE user_meeting RENAME CONSTRAINT user_meeting_meeting_id_fkey TO user_meetting_meeting_id_fkey')
    op.execute('ALTER INDEX user_meeting_pkey RENAME TO user_meetting_pkey')
    op.execute('ALTER SEQUENCE user_meeting_id_seq RENAME TO user_meetting_id_seq')
    op.rename_table('user_meeting', 'user_meetting')
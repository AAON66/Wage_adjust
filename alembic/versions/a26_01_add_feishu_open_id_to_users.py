"""add_feishu_open_id_to_users

Revision ID: a26_01_feishu_open_id
Revises: 7de9baee16f0
Create Date: 2026-04-16
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a26_01_feishu_open_id'
down_revision: Union[str, None] = '7de9baee16f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('feishu_open_id', sa.String(255), nullable=True))
        batch_op.create_unique_constraint('uq_users_feishu_open_id', ['feishu_open_id'])
        batch_op.create_index('ix_users_feishu_open_id', ['feishu_open_id'])


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_index('ix_users_feishu_open_id')
        batch_op.drop_constraint('uq_users_feishu_open_id', type_='unique')
        batch_op.drop_column('feishu_open_id')

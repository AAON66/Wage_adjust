"""add_prompt_hash_dimension_scores_used_fallback_evaluations

Revision ID: 4f2eeacd62c3
Revises: fa1c02bf9cd1
Create Date: 2026-03-26 13:59:21.035120

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f2eeacd62c3'
down_revision: Union[str, None] = 'fa1c02bf9cd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add prompt_hash column to dimension_scores (nullable, 64-char SHA-256 hex)
    with op.batch_alter_table('dimension_scores') as batch_op:
        batch_op.add_column(sa.Column('prompt_hash', sa.String(64), nullable=True))

    # Add used_fallback column to ai_evaluations (non-nullable boolean, default False)
    with op.batch_alter_table('ai_evaluations') as batch_op:
        batch_op.add_column(sa.Column('used_fallback', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('ai_evaluations') as batch_op:
        batch_op.drop_column('used_fallback')

    with op.batch_alter_table('dimension_scores') as batch_op:
        batch_op.drop_column('prompt_hash')

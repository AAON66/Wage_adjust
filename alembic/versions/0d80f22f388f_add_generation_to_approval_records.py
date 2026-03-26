"""add_generation_to_approval_records

Revision ID: 0d80f22f388f
Revises: 4f2eeacd62c3
Create Date: 2026-03-27 07:56:52.016365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d80f22f388f'
down_revision: Union[str, None] = '4f2eeacd62c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('approval_records', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('generation', sa.Integer(), nullable=False, server_default='0')
        )
        # Actual constraint name in DB is uq_approval_records_recommendation_id
        batch_op.drop_constraint('uq_approval_records_recommendation_id', type_='unique')
        batch_op.create_unique_constraint(
            'uq_approval_records_recommendation_step_generation',
            ['recommendation_id', 'step_name', 'generation'],
        )


def downgrade() -> None:
    with op.batch_alter_table('approval_records', schema=None) as batch_op:
        batch_op.drop_constraint('uq_approval_records_recommendation_step_generation', type_='unique')
        batch_op.create_unique_constraint(
            'uq_approval_records_recommendation_id',
            ['recommendation_id', 'step_name'],
        )
        batch_op.drop_column('generation')

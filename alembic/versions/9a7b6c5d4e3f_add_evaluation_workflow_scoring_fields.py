"""add evaluation workflow scoring fields

Revision ID: 9a7b6c5d4e3f
Revises: 3c1d2e4f5a6b
Create Date: 2026-03-21 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '9a7b6c5d4e3f'
down_revision = '3c1d2e4f5a6b'
branch_labels = None
depends_on = None


COLUMNS = {
    'ai_overall_score': sa.Column('ai_overall_score', sa.Float(), nullable=False, server_default='0'),
    'manager_score': sa.Column('manager_score', sa.Float(), nullable=True),
    'score_gap': sa.Column('score_gap', sa.Float(), nullable=True),
    'manager_comment': sa.Column('manager_comment', sa.Text(), nullable=True),
    'hr_comment': sa.Column('hr_comment', sa.Text(), nullable=True),
    'hr_decision': sa.Column('hr_decision', sa.String(length=32), nullable=True),
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('ai_evaluations')}
    indexes = {index['name'] for index in inspector.get_indexes('ai_evaluations')}

    with op.batch_alter_table('ai_evaluations', recreate='always') as batch_op:
        for name, column in COLUMNS.items():
            if name not in columns:
                batch_op.add_column(column)
        if 'ix_ai_evaluations_hr_decision' not in indexes:
            batch_op.create_index(batch_op.f('ix_ai_evaluations_hr_decision'), ['hr_decision'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('ai_evaluations')}
    indexes = {index['name'] for index in inspector.get_indexes('ai_evaluations')}

    with op.batch_alter_table('ai_evaluations', recreate='always') as batch_op:
        if 'ix_ai_evaluations_hr_decision' in indexes:
            batch_op.drop_index(batch_op.f('ix_ai_evaluations_hr_decision'))
        for name in ['hr_decision', 'hr_comment', 'manager_comment', 'score_gap', 'manager_score', 'ai_overall_score']:
            if name in columns:
                batch_op.drop_column(name)

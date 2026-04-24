"""Add comment column to performance_records.

Revision ID: 36_01_add_comment_perf
Revises: p34_02_tier_snapshot
Create Date: 2026-04-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = '36_01_add_comment_perf'
down_revision = 'p34_02_tier_snapshot'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('performance_records') as batch_op:
        batch_op.add_column(
            sa.Column(
                'comment',
                sa.Text(),
                nullable=True,
                comment=(
                    'Phase 36 D-02：绩效评语，存量行保持 NULL；'
                    'manual/excel 来源可写入；feishu 来源恒 None'
                ),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table('performance_records') as batch_op:
        batch_op.drop_column('comment')

"""Phase 34 D-01: add performance_tier_snapshots table.

Revision ID: p34_02_tier_snapshot
Revises: p34_01_dept_snapshot
Create Date: 2026-04-22

D-01：单年一行的档次快照表。HR 重算或导入触发同步重算时 UPSERT；
查询走 Redis cache → 表 → 404；并发控制由 Service 层 SELECT ... FOR UPDATE
NOWAIT（D-05）实现。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'p34_02_tier_snapshot'
down_revision: Union[str, None] = 'p34_01_dept_snapshot'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'performance_tier_snapshots',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('tiers_json', sa.JSON(), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'insufficient_sample',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('0'),
        ),
        sa.Column(
            'distribution_warning',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('0'),
        ),
        sa.Column('actual_distribution_json', sa.JSON(), nullable=False),
        sa.Column(
            'skipped_invalid_grades',
            sa.Integer(),
            nullable=False,
            server_default='0',
        ),
        sa.UniqueConstraint('year', name='uq_performance_tier_snapshot_year'),
    )
    op.create_index(
        'ix_performance_tier_snapshots_year',
        'performance_tier_snapshots',
        ['year'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_performance_tier_snapshots_year',
        table_name='performance_tier_snapshots',
    )
    op.drop_table('performance_tier_snapshots')

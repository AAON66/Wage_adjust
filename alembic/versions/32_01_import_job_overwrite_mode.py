"""add_overwrite_mode_actor_id_updated_at_to_import_jobs_and_salary_adj_unique

Revision ID: 32_01_import_job_overwrite_mode
Revises: 31_01_sync_log_observability
Create Date: 2026-04-21

Phase 32 / IMPORT-05 / IMPORT-06 / D-12 / D-13 / D-14 / Pitfall 4.

Changes:
  1. import_jobs: 三阶段迁移加 overwrite_mode (NOT NULL default 'merge')；
     同时加 actor_id (FK users.id ON DELETE SET NULL) + updated_at (server_default=now())。
  2. salary_adjustment_records: 加 UniqueConstraint(employee_id, adjustment_date, adjustment_type)
     对齐飞书同步业务键（_sync_salary_adjustments_body line 947-952）。
     注：当前表中可能存在重复行（append 模式残留）— 本迁移在加约束前先 dedup（保留 created_at 最新一条）。
  3. PerformanceRecord 已有 uq_performance_employee_year 约束（决议 D-15），本期不动。
"""
from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32_01_import_job_overwrite_mode'
down_revision: Union[str, None] = '31_01_sync_log_observability'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


logger = logging.getLogger('alembic.runtime.migration')


def upgrade() -> None:
    # ===== import_jobs: 三阶段加 overwrite_mode + 一次性加 actor_id / updated_at =====
    with op.batch_alter_table('import_jobs') as batch_op:
        batch_op.add_column(sa.Column('overwrite_mode', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('actor_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            'fk_import_jobs_actor_id_users', 'users',
            ['actor_id'], ['id'], ondelete='SET NULL',
        )
        batch_op.create_index('ix_import_jobs_actor_id', ['actor_id'], unique=False)
        batch_op.add_column(sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ))

    # Stage 2: backfill — 历史 ImportJob 默认按 'merge' 处理
    op.execute("UPDATE import_jobs SET overwrite_mode='merge' WHERE overwrite_mode IS NULL")

    # Stage 3: enforce NOT NULL on overwrite_mode
    with op.batch_alter_table('import_jobs') as batch_op:
        batch_op.alter_column(
            'overwrite_mode',
            existing_type=sa.String(length=16),
            nullable=False,
            server_default='merge',
        )

    # ===== salary_adjustment_records: dedup + 加 UniqueConstraint =====
    # 先统计 dedup 前后差异，写入 alembic logger 供运维审计（Info 1 acceptance）
    bind = op.get_bind()
    before_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM salary_adjustment_records")
    ).scalar() or 0

    # SQLite-safe dedup：保留每个 (employee_id, adjustment_date, adjustment_type) 组合最新一条
    op.execute("""
        DELETE FROM salary_adjustment_records
        WHERE id NOT IN (
            SELECT id FROM (
                SELECT sa1.id FROM salary_adjustment_records sa1
                WHERE sa1.created_at = (
                    SELECT MAX(sa2.created_at) FROM salary_adjustment_records sa2
                    WHERE sa2.employee_id = sa1.employee_id
                      AND sa2.adjustment_date = sa1.adjustment_date
                      AND sa2.adjustment_type = sa1.adjustment_type
                )
            ) AS keepers
        )
    """)

    after_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM salary_adjustment_records")
    ).scalar() or 0
    removed = before_count - after_count
    logger.info(
        'Removed %d duplicate salary_adjustment_records before adding UniqueConstraint',
        removed,
    )

    with op.batch_alter_table('salary_adjustment_records') as batch_op:
        batch_op.create_unique_constraint(
            'uq_salary_adj_employee_date_type',
            ['employee_id', 'adjustment_date', 'adjustment_type'],
        )


def downgrade() -> None:
    with op.batch_alter_table('salary_adjustment_records') as batch_op:
        batch_op.drop_constraint('uq_salary_adj_employee_date_type', type_='unique')

    with op.batch_alter_table('import_jobs') as batch_op:
        batch_op.drop_index('ix_import_jobs_actor_id')
        batch_op.drop_constraint('fk_import_jobs_actor_id_users', type_='foreignkey')
        batch_op.drop_column('updated_at')
        batch_op.drop_column('actor_id')
        batch_op.drop_column('overwrite_mode')

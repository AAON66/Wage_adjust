"""Phase 34 D-07: add department_snapshot column to performance_records.

Revision ID: p34_01_dept_snapshot
Revises: 33_01_employee_salary
Create Date: 2026-04-22

D-07：仅添加列，存量行保持 NULL；不跑数据回填脚本（按当前部门回填会引入虚假
快照，违反「快照」语义）。Service 层在新增/导入路径上显式从 employee.department
赋值。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'p34_01_dept_snapshot'
down_revision: Union[str, None] = '33_01_employee_salary'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('performance_records') as batch_op:
        batch_op.add_column(
            sa.Column(
                'department_snapshot',
                sa.String(length=100),
                nullable=True,
                comment='Phase 34 D-07：录入时员工所属部门快照；存量行 NULL',
            )
        )


def downgrade() -> None:
    with op.batch_alter_table('performance_records') as batch_op:
        batch_op.drop_column('department_snapshot')

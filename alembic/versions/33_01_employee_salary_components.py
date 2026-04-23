"""add employee salary components

Revision ID: 33_01_employee_salary
Revises: 32_01_import_job_overwrite_mode
Create Date: 2026-04-22 14:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '33_01_employee_salary'
down_revision: Union[str, None] = '32_01_import_job_overwrite_mode'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('employees', sa.Column('base_salary', sa.Numeric(12, 2), nullable=True))
    op.add_column('employees', sa.Column('performance_salary', sa.Numeric(12, 2), nullable=True))
    op.add_column('employees', sa.Column('project_allowance', sa.Numeric(12, 2), nullable=True))
    op.add_column('employees', sa.Column('intern_monthly_salary', sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('employees', 'intern_monthly_salary')
    op.drop_column('employees', 'project_allowance')
    op.drop_column('employees', 'performance_salary')
    op.drop_column('employees', 'base_salary')

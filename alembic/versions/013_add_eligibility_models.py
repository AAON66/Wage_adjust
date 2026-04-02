"""Add eligibility models: performance_records, salary_adjustment_records, employee/attendance columns

Revision ID: 013_eligibility
Revises: b12a00000001
Create Date: 2026-04-02
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '013_eligibility'
down_revision: Union[str, None] = 'b12a00000001'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # -- Add columns to existing tables --
    op.add_column('employees', sa.Column('hire_date', sa.Date(), nullable=True))
    op.add_column('employees', sa.Column('last_salary_adjustment_date', sa.Date(), nullable=True))
    op.add_column('attendance_records', sa.Column('non_statutory_leave_days', sa.Float(), nullable=True))

    # -- Create performance_records table --
    op.create_table(
        'performance_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('employee_id', sa.String(36), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('employee_no', sa.String(64), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('grade', sa.String(8), nullable=False),
        sa.Column('source', sa.String(32), nullable=False, server_default='manual'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('employee_id', 'year', name='uq_performance_employee_year'),
    )
    op.create_index('ix_performance_records_employee_id', 'performance_records', ['employee_id'])
    op.create_index('ix_performance_records_employee_no', 'performance_records', ['employee_no'])
    op.create_index('ix_performance_records_year', 'performance_records', ['year'])

    # -- Create salary_adjustment_records table --
    op.create_table(
        'salary_adjustment_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('employee_id', sa.String(36), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('employee_no', sa.String(64), nullable=False),
        sa.Column('adjustment_date', sa.Date(), nullable=False),
        sa.Column('adjustment_type', sa.String(32), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('source', sa.String(32), nullable=False, server_default='manual'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_salary_adj_employee_date', 'salary_adjustment_records', ['employee_id', 'adjustment_date'])
    op.create_index('ix_salary_adjustment_records_employee_id', 'salary_adjustment_records', ['employee_id'])
    op.create_index('ix_salary_adjustment_records_employee_no', 'salary_adjustment_records', ['employee_no'])
    op.create_index('ix_salary_adjustment_records_adjustment_date', 'salary_adjustment_records', ['adjustment_date'])


def downgrade() -> None:
    # Drop tables first
    op.drop_table('salary_adjustment_records')
    op.drop_table('performance_records')

    # Drop columns in reverse order
    op.drop_column('attendance_records', 'non_statutory_leave_days')
    op.drop_column('employees', 'last_salary_adjustment_date')
    op.drop_column('employees', 'hire_date')

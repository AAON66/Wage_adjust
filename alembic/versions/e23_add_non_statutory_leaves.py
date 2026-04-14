"""Add non_statutory_leaves table.

Revision ID: e23_non_statutory_leaves
Revises: d16_sharing_requests
Create Date: 2026-04-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = 'e23_non_statutory_leaves'
down_revision = 'd16_sharing_requests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'non_statutory_leaves',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('employee_id', sa.String(36), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('employee_no', sa.String(64), nullable=False, index=True),
        sa.Column('year', sa.Integer, nullable=False, index=True),
        sa.Column('total_days', sa.Numeric(6, 1), nullable=False),
        sa.Column('leave_type', sa.String(32), nullable=True, comment='事假/病假/其他'),
        sa.Column('source', sa.String(32), nullable=False, server_default='manual', comment='manual/excel/feishu'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('employee_id', 'year', name='uq_leave_employee_year'),
    )


def downgrade() -> None:
    op.drop_table('non_statutory_leaves')

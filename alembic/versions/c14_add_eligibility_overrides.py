"""Add eligibility_overrides table.

Revision ID: c14_add_eligibility_overrides
Revises: 013_add_eligibility_models
Create Date: 2026-04-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = 'c14_add_eligibility_overrides'
down_revision = '013_add_eligibility_models'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'eligibility_overrides',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('employee_id', sa.String(36), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('requester_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('override_rules', sa.JSON, nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending_hrbp'),
        sa.Column('year', sa.Integer, nullable=False, index=True),
        sa.Column('reference_date', sa.Date, nullable=True),
        sa.Column('hrbp_approver_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('hrbp_decision', sa.String(32), nullable=True),
        sa.Column('hrbp_comment', sa.Text, nullable=True),
        sa.Column('hrbp_decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('admin_approver_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('admin_decision', sa.String(32), nullable=True),
        sa.Column('admin_comment', sa.Text, nullable=True),
        sa.Column('admin_decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('employee_id', 'year', name='uq_active_override_employee_year'),
    )


def downgrade() -> None:
    op.drop_table('eligibility_overrides')

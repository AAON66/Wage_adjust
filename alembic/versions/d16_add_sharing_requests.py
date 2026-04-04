"""Add sharing_requests table for file sharing workflow.

Revision ID: d16_sharing_requests
Revises: c14_add_eligibility_overrides
Create Date: 2026-04-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = 'd16_sharing_requests'
down_revision = 'c14_add_eligibility_overrides'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sharing_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('requester_file_id', sa.String(36), sa.ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('original_file_id', sa.String(36), sa.ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('requester_submission_id', sa.String(36), sa.ForeignKey('employee_submissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('original_submission_id', sa.String(36), sa.ForeignKey('employee_submissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending'),
        sa.Column('proposed_pct', sa.Float, nullable=False, server_default='50.0'),
        sa.Column('final_pct', sa.Float, nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('requester_file_id', 'original_file_id', name='uq_sharing_request_file_pair'),
    )


def downgrade() -> None:
    op.drop_table('sharing_requests')

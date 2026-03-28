"""Phase 05: add content_hash and project_contributors table

Revision ID: a5b6c7d8e9f0
Revises: a3f1c8e92b04
Create Date: 2026-03-28 00:00:00.000000
"""
from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a5b6c7d8e9f0'
down_revision: Union[str, None] = 'a3f1c8e92b04'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add content_hash and owner_contribution_pct to uploaded_files
    with op.batch_alter_table('uploaded_files') as batch_op:
        batch_op.add_column(
            sa.Column('content_hash', sa.String(64), nullable=False, server_default=''),
        )
        batch_op.add_column(
            sa.Column('owner_contribution_pct', sa.Float, nullable=False, server_default='100.0'),
        )
        batch_op.create_index('ix_uploaded_files_content_hash', ['content_hash'])

    # Create project_contributors table
    op.create_table(
        'project_contributors',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('uploaded_file_id', sa.String(36), sa.ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('submission_id', sa.String(36), sa.ForeignKey('employee_submissions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('contribution_pct', sa.Float, nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='accepted'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('uploaded_file_id', 'submission_id', name='uq_project_contributors_file_submission'),
        sa.CheckConstraint('contribution_pct > 0 AND contribution_pct <= 100', name='ck_contribution_pct_range'),
    )


def downgrade() -> None:
    op.drop_table('project_contributors')

    with op.batch_alter_table('uploaded_files') as batch_op:
        batch_op.drop_index('ix_uploaded_files_content_hash')
        batch_op.drop_column('owner_contribution_pct')
        batch_op.drop_column('content_hash')

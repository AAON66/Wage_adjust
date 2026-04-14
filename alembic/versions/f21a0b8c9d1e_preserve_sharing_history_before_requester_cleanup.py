"""preserve_sharing_history_before_requester_cleanup

Revision ID: f21a0b8c9d1e
Revises: e55f2f84b5d1
Create Date: 2026-04-09 15:50:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f21a0b8c9d1e'
down_revision: Union[str, None] = 'e55f2f84b5d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('sharing_requests') as batch_op:
        batch_op.add_column(sa.Column('requester_content_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('requester_file_name_snapshot', sa.String(length=255), nullable=True))

    op.execute(
        """
        UPDATE sharing_requests
        SET requester_content_hash = COALESCE(
                (SELECT uploaded_files.content_hash
                 FROM uploaded_files
                 WHERE uploaded_files.id = sharing_requests.requester_file_id),
                ''
            ),
            requester_file_name_snapshot = COALESCE(
                (SELECT uploaded_files.file_name
                 FROM uploaded_files
                 WHERE uploaded_files.id = sharing_requests.requester_file_id),
                ''
            )
        """
    )

    with op.batch_alter_table('sharing_requests') as batch_op:
        batch_op.drop_constraint(
            batch_op.f('fk_sharing_requests_requester_file_id_uploaded_files'),
            type_='foreignkey',
        )
        batch_op.alter_column(
            'requester_file_id',
            existing_type=sa.String(length=36),
            nullable=True,
        )
        batch_op.alter_column(
            'requester_content_hash',
            existing_type=sa.String(length=64),
            nullable=False,
            server_default='',
        )
        batch_op.alter_column(
            'requester_file_name_snapshot',
            existing_type=sa.String(length=255),
            nullable=False,
            server_default='',
        )
        batch_op.create_foreign_key(
            batch_op.f('fk_sharing_requests_requester_file_id_uploaded_files'),
            'uploaded_files',
            ['requester_file_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    op.execute("DELETE FROM sharing_requests WHERE requester_file_id IS NULL")

    with op.batch_alter_table('sharing_requests') as batch_op:
        batch_op.drop_constraint(
            batch_op.f('fk_sharing_requests_requester_file_id_uploaded_files'),
            type_='foreignkey',
        )
        batch_op.create_foreign_key(
            batch_op.f('fk_sharing_requests_requester_file_id_uploaded_files'),
            'uploaded_files',
            ['requester_file_id'],
            ['id'],
            ondelete='CASCADE',
        )
        batch_op.alter_column(
            'requester_file_id',
            existing_type=sa.String(length=36),
            nullable=False,
        )
        batch_op.drop_column('requester_file_name_snapshot')
        batch_op.drop_column('requester_content_hash')

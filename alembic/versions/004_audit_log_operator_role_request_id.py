"""audit_log_operator_role_request_id

Revision ID: a3f1c8e92b04
Revises: 0d80f22f388f
Create Date: 2026-03-27 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f1c8e92b04'
down_revision: Union[str, None] = '0d80f22f388f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('operator_role', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('request_id', sa.String(36), nullable=True))
        batch_op.create_index('ix_audit_logs_operator_role', ['operator_role'])
        batch_op.create_index('ix_audit_logs_request_id', ['request_id'])


def downgrade() -> None:
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_logs_request_id')
        batch_op.drop_index('ix_audit_logs_operator_role')
        batch_op.drop_column('request_id')
        batch_op.drop_column('operator_role')

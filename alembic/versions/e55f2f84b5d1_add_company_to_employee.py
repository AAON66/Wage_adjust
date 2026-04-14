"""add_company_to_employee

Revision ID: e55f2f84b5d1
Revises: d16_sharing_requests
Create Date: 2026-04-09 12:05:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e55f2f84b5d1'
down_revision: Union[str, None] = 'd16_sharing_requests'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('employees') as batch_op:
        batch_op.add_column(sa.Column('company', sa.String(length=128), nullable=True))
        batch_op.create_index(batch_op.f('ix_employees_company'), ['company'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('employees') as batch_op:
        batch_op.drop_index(batch_op.f('ix_employees_company'))
        batch_op.drop_column('company')

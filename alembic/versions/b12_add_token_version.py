"""Add token_version column to users table

Revision ID: b12a00000001
Revises: 9d428de0df97
Create Date: 2026-04-01
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b12a00000001'
down_revision: Union[str, None] = '9d428de0df97'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'token_version')

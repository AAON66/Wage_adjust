"""merge_heads_before_feishu

Revision ID: 7de9baee16f0
Revises: e23_non_statutory_leaves, f21a0b8c9d1e
Create Date: 2026-04-16 13:49:38.816475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7de9baee16f0'
down_revision: Union[str, None] = ('e23_non_statutory_leaves', 'f21a0b8c9d1e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

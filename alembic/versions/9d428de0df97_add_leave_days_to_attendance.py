"""add_leave_days_to_attendance

Revision ID: 9d428de0df97
Revises: e13acf4f2de0
Create Date: 2026-03-31 09:02:15.222689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d428de0df97'
down_revision: Union[str, None] = 'e13acf4f2de0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('attendance_records', sa.Column('leave_days', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('attendance_records', 'leave_days')

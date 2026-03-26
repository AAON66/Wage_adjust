"""encrypt_national_id_columns

Revision ID: fa1c02bf9cd1
Revises: 6e4824832f6a
Create Date: 2026-03-26 08:56:58.094061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa1c02bf9cd1'
down_revision: Union[str, None] = '6e4824832f6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Expand id_card_no columns from String(32) to String(256) to accommodate
    # AES-256-GCM ciphertext (12-byte nonce + ciphertext + 16-byte GCM tag, base64-encoded).
    # Note: SQLite requires batch_alter_table for column type changes.
    # PostgreSQL supports direct ALTER COLUMN TYPE and will use batch mode transparently.
    with op.batch_alter_table('employees') as batch_op:
        batch_op.alter_column(
            'id_card_no',
            existing_type=sa.String(length=32),
            type_=sa.String(length=256),
            existing_nullable=True,
        )
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            'id_card_no',
            existing_type=sa.String(length=32),
            type_=sa.String(length=256),
            existing_nullable=True,
        )


def downgrade() -> None:
    # Revert id_card_no columns back to String(32).
    # WARNING: If encrypted values are stored, they will be truncated on downgrade.
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            'id_card_no',
            existing_type=sa.String(length=256),
            type_=sa.String(length=32),
            existing_nullable=True,
        )
    with op.batch_alter_table('employees') as batch_op:
        batch_op.alter_column(
            'id_card_no',
            existing_type=sa.String(length=256),
            type_=sa.String(length=32),
            existing_nullable=True,
        )

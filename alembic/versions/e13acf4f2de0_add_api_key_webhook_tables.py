"""add_api_key_webhook_tables

Revision ID: e13acf4f2de0
Revises: a1b2c3d4e5f6
Create Date: 2026-03-30 19:36:35.863438

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e13acf4f2de0'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('api_keys',
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('key_prefix', sa.String(length=8), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_ip', sa.String(length=45), nullable=True),
        sa.Column('rate_limit', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_api_keys_created_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_api_keys')),
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)

    op.create_table('webhook_endpoints',
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('secret', sa.String(length=128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('description', sa.String(length=256), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('events', sa.JSON(), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_webhook_endpoints_created_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_webhook_endpoints')),
    )

    op.create_table('webhook_delivery_logs',
        sa.Column('webhook_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhook_endpoints.id'], name=op.f('fk_webhook_delivery_logs_webhook_id_webhook_endpoints')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_webhook_delivery_logs')),
    )
    op.create_index(op.f('ix_webhook_delivery_logs_webhook_id'), 'webhook_delivery_logs', ['webhook_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_webhook_delivery_logs_webhook_id'), table_name='webhook_delivery_logs')
    op.drop_table('webhook_delivery_logs')
    op.drop_table('webhook_endpoints')
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_table('api_keys')

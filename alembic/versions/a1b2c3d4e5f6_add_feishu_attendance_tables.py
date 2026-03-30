"""add feishu attendance tables

Revision ID: a1b2c3d4e5f6
Revises: 9a7b6c5d4e3f
Create Date: 2026-03-30 14:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '9a7b6c5d4e3f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'feishu_configs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('app_id', sa.String(128), nullable=False),
        sa.Column('encrypted_app_secret', sa.String(512), nullable=False),
        sa.Column('bitable_app_token', sa.String(128), nullable=False),
        sa.Column('bitable_table_id', sa.String(128), nullable=False),
        sa.Column('field_mapping', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('sync_hour', sa.Integer(), nullable=False, server_default='6'),
        sa.Column('sync_minute', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sync_timezone', sa.String(64), nullable=False, server_default='Asia/Shanghai'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'attendance_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('employee_id', sa.String(36), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('employee_no', sa.String(64), nullable=False, index=True),
        sa.Column('period', sa.String(32), nullable=False, index=True),
        sa.Column('attendance_rate', sa.Float(), nullable=True),
        sa.Column('absence_days', sa.Float(), nullable=True),
        sa.Column('overtime_hours', sa.Float(), nullable=True),
        sa.Column('late_count', sa.Integer(), nullable=True),
        sa.Column('early_leave_count', sa.Integer(), nullable=True),
        sa.Column('feishu_record_id', sa.String(128), nullable=True),
        sa.Column('source_modified_at', sa.BigInteger(), nullable=True),
        sa.Column('data_as_of', sa.DateTime(timezone=True), nullable=False),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('employee_id', 'period', name='uq_attendance_employee_period'),
        sa.UniqueConstraint('feishu_record_id', name='uq_attendance_feishu_record_id'),
    )

    op.create_table(
        'feishu_sync_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('mode', sa.String(32), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('total_fetched', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('synced_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unmatched_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('unmatched_employee_nos', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('triggered_by', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('feishu_sync_logs')
    op.drop_table('attendance_records')
    op.drop_table('feishu_configs')

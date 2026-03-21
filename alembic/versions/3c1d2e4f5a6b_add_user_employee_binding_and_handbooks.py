"""add user employee binding and employee handbooks

Revision ID: 3c1d2e4f5a6b
Revises: 8f4e5a1c9b2d
Create Date: 2026-03-21 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '3c1d2e4f5a6b'
down_revision = '8f4e5a1c9b2d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column['name'] for column in inspector.get_columns('users')}
    user_indexes = {index['name'] for index in inspector.get_indexes('users')}

    if 'employee_id' not in user_columns:
        with op.batch_alter_table('users', recreate='always') as batch_op:
            batch_op.add_column(sa.Column('employee_id', sa.String(length=36), nullable=True))
            batch_op.create_index(batch_op.f('ix_users_employee_id'), ['employee_id'], unique=True)
            batch_op.create_foreign_key('fk_users_employee_id_employees', 'employees', ['employee_id'], ['id'])
    elif 'ix_users_employee_id' not in user_indexes:
        op.create_index(op.f('ix_users_employee_id'), 'users', ['employee_id'], unique=True)

    if 'employee_handbooks' not in inspector.get_table_names():
        op.create_table(
            'employee_handbooks',
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('file_name', sa.String(length=255), nullable=False),
            sa.Column('file_type', sa.String(length=32), nullable=False),
            sa.Column('storage_key', sa.String(length=512), nullable=False),
            sa.Column('parse_status', sa.String(length=32), nullable=False),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('key_points_json', sa.JSON(), nullable=False),
            sa.Column('tags_json', sa.JSON(), nullable=False),
            sa.Column('uploaded_by_user_id', sa.String(length=36), nullable=True),
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
            sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('storage_key'),
        )
        op.create_index(op.f('ix_employee_handbooks_file_type'), 'employee_handbooks', ['file_type'], unique=False)
        op.create_index(op.f('ix_employee_handbooks_parse_status'), 'employee_handbooks', ['parse_status'], unique=False)
        op.create_index(op.f('ix_employee_handbooks_uploaded_by_user_id'), 'employee_handbooks', ['uploaded_by_user_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'employee_handbooks' in inspector.get_table_names():
        op.drop_index(op.f('ix_employee_handbooks_uploaded_by_user_id'), table_name='employee_handbooks')
        op.drop_index(op.f('ix_employee_handbooks_parse_status'), table_name='employee_handbooks')
        op.drop_index(op.f('ix_employee_handbooks_file_type'), table_name='employee_handbooks')
        op.drop_table('employee_handbooks')

    user_columns = {column['name'] for column in inspector.get_columns('users')}
    if 'employee_id' in user_columns:
        with op.batch_alter_table('users', recreate='always') as batch_op:
            try:
                batch_op.drop_constraint('fk_users_employee_id_employees', type_='foreignkey')
            except Exception:
                pass
            try:
                batch_op.drop_index(batch_op.f('ix_users_employee_id'))
            except Exception:
                pass
            batch_op.drop_column('employee_id')

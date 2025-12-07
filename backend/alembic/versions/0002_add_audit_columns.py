"""add audit columns and indexes

Revision ID: 0002_add_audit_columns
Revises: 0001_create_item_audit
Create Date: 2025-12-07
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_audit_columns'
down_revision = '0001_create_item_audit'
branch_labels = None
depends_on = None


def upgrade():
    # add typed columns for common audit fields to allow indexing and faster queries
    op.add_column('item_audit', sa.Column('user_id', sa.String(length=128), nullable=True))
    op.add_column('item_audit', sa.Column('ip', sa.String(length=45), nullable=True))
    op.add_column('item_audit', sa.Column('method', sa.String(length=16), nullable=True))
    op.add_column('item_audit', sa.Column('user_agent', sa.Text(), nullable=True))
    op.add_column('item_audit', sa.Column('request_path', sa.String(length=512), nullable=True))

    # create indexes for fields that will be frequently queried
    op.create_index('ix_item_audit_user_id', 'item_audit', ['user_id'])
    op.create_index('ix_item_audit_ip', 'item_audit', ['ip'])
    op.create_index('ix_item_audit_method', 'item_audit', ['method'])
    op.create_index('ix_item_audit_created_at', 'item_audit', ['created_at'])


def downgrade():
    op.drop_index('ix_item_audit_created_at', table_name='item_audit')
    op.drop_index('ix_item_audit_method', table_name='item_audit')
    op.drop_index('ix_item_audit_ip', table_name='item_audit')
    op.drop_index('ix_item_audit_user_id', table_name='item_audit')

    op.drop_column('item_audit', 'request_path')
    op.drop_column('item_audit', 'user_agent')
    op.drop_column('item_audit', 'method')
    op.drop_column('item_audit', 'ip')
    op.drop_column('item_audit', 'user_id')

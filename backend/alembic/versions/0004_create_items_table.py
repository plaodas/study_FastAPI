"""create items table

Revision ID: 0004_create_items_table
Revises: 0003_backfill_audit_columns
Create Date: 2025-12-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_create_items_table"
down_revision = "0003_backfill_audit_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create 'items' table using SQLAlchemy types. Keep schema aligned with db/init.sql.
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )


def downgrade() -> None:
    op.drop_table("items")

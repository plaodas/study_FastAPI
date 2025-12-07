"""create item_audit table

Revision ID: 0001_create_item_audit
Revises:
Create Date: 2025-12-07
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_create_item_audit"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "item_audit",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("item_id", sa.Integer, nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
    )


def downgrade():
    op.drop_table("item_audit")

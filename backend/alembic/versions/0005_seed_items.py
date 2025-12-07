"""seed items table

Revision ID: 0005_seed_items
Revises: 0004_create_items_table
Create Date: 2025-12-07 00:15:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_seed_items"
down_revision = "0004_create_items_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insert seed rows only if the table is empty
    op.execute(
        """
        INSERT INTO items (name)
        SELECT v.name FROM (VALUES ('Apple'), ('Banana'), ('Cherry')) AS v(name)
        WHERE NOT EXISTS (SELECT 1 FROM items)
        """
    )


def downgrade() -> None:
    # Remove seeded rows if present (best-effort, won't remove user-added rows)
    op.execute(
        """
        DELETE FROM items WHERE name IN ('Apple', 'Banana', 'Cherry')
        """
    )

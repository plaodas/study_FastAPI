"""backfill audit columns from payload

Revision ID: 0003_backfill_audit_columns
Revises: 0002_add_audit_columns
Create Date: 2025-12-07
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_backfill_audit_columns'
down_revision = '0002_add_audit_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Backfill newly added typed columns from JSON payload for existing rows.
    # This operation can be heavy on large tables; run during maintenance window if needed.
    conn = op.get_bind()

    # Update all rows where the typed column is NULL and payload contains a value.
    conn.execute(
        sa.text(
            """
            UPDATE item_audit
            SET
              user_id = COALESCE(user_id, payload ->> 'user_id'),
              ip = COALESCE(ip, payload ->> 'ip'),
              method = COALESCE(method, payload ->> 'method'),
              user_agent = COALESCE(user_agent, payload ->> 'user_agent'),
              request_path = COALESCE(request_path, payload ->> 'request_path')
            WHERE payload IS NOT NULL
              AND (
                user_id IS NULL OR ip IS NULL OR method IS NULL OR user_agent IS NULL OR request_path IS NULL
              );
            """
        )
    )


def downgrade():
    # No data rollback necessary; keep columns intact.
    pass

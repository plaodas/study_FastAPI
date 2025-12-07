#!/usr/bin/env bash
set -euo pipefail

# Wait for DB to be ready
until psql "$DATABASE_URL" -c 'SELECT 1;' >/dev/null 2>&1; do
  echo "Waiting for DB..."
  sleep 1
done

# Check if alembic_version exists
if ! psql "$DATABASE_URL" -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version'" | grep -q 1; then
  echo "No alembic_version table found => treating DB as empty"
  if [ -f /backups/latest.sql ]; then
    echo "Restoring backup /backups/latest.sql..."
    psql "$DATABASE_URL" -f /backups/latest.sql
    echo "Backup restored."
    # ensure alembic knows current head (if backup included schema but not alembic_version)
    alembic stamp head
  else
    echo "No backup found. Continuing to run migrations to create schema."
  fi
fi

# Always apply migrations (idempotent)
alembic upgrade head

# Start the app (example)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

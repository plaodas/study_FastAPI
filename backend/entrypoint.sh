#!/usr/bin/env bash
set -euo pipefail

# DB 接続文字列を環境変数で受け取る想定
# 例: export DATABASE_URL="postgresql://user:pass@db:5432/appdb"

# 1) DB が起きるまで待つ
echo "Waiting for DB..."
until psql "$DATABASE_URL" -c 'SELECT 1;' >/dev/null 2>&1; do
  sleep 1
done
echo "DB is ready."

# 2) DB が空（alembic_version が存在しない）かチェック
ALEMBIC_EXISTS=$(psql "$DATABASE_URL" -tAc "SELECT to_regclass('public.alembic_version');")

if [ -z "$ALEMBIC_EXISTS" ] || [ "$ALEMBIC_EXISTS" = "" ]; then
  echo "No alembic_version table detected -> treating DB as empty/unnormalized."

  # only restore if backup file exists
  if [ -f /backups/latest.sql ]; then
    echo "Restoring backup from /backups/latest.sql ..."
    psql "$DATABASE_URL" -f /backups/latest.sql
    echo "Backup restore completed."

    # If backup contained schema but not alembic_version, mark alembic as in-sync.
    # Use stamp head so alembic won't try to re-run already-applied DDL.
    if command -v alembic >/dev/null 2>&1; then
      echo "Stamping alembic head..."
      alembic stamp head || true
    fi
  else
    echo "No /backups/latest.sql found. Will proceed to run migrations to create schema."
  fi
else
  echo "alembic_version table present. Skipping automatic restore."
fi

# 3) Ensure migrations are applied (idempotent)
if command -v alembic >/dev/null 2>&1; then
  echo "Running alembic upgrade head..."
  alembic upgrade head
fi

# 4) Exec main command (passed from Dockerfile/CMD)
exec "$@"
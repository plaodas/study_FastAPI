#!/usr/bin/env bash
set -euo pipefail

# DB 接続文字列を環境変数で受け取る想定
# 例: export DATABASE_URL="postgresql://user:pass@db:5432/appdb"

LOGDIR="/app/logs"
LOGFILE="$LOGDIR/startup.log"
mkdir -p "$LOGDIR"

# rotate startup log if it exceeds max size (in bytes)
rotate_logs() {
  # configurable via env vars:
  # STARTUP_ROTATE_MAX_BYTES (default 5MB)
  # STARTUP_ROTATE_KEEP (default 7 archives to keep)
  local max_size=${STARTUP_ROTATE_MAX_BYTES:-$((5 * 1024 * 1024))}
  local keep=${STARTUP_ROTATE_KEEP:-7}
  # rotate every .log file in LOGDIR (excluding already-rotated .log.gz)
  for f in "$LOGDIR"/*.log; do
    [ -e "$f" ] || continue
    # skip socket-like or special files
    if [ ! -f "$f" ]; then
      continue
    fi
    local size=$(stat -c%s "$f" 2>/dev/null || echo 0)
    if [ "$size" -ge "$max_size" ]; then
      base=$(basename "$f" .log)
      ts=$(date -u +"%Y%m%dT%H%M%SZ")
      gzip -c "$f" > "$LOGDIR/${base}-$ts.log.gz" || true
      : > "$f"  # truncate
      # cleanup old rotated files for this base name
      ls -1t "$LOGDIR/${base}-"*.log.gz 2>/dev/null | sed -e "1,${keep}d" | xargs -r rm -f --
    fi
  done
}

rotate_logs

# start a background daemon to periodically rotate logs
rotate_daemon() {
  local interval=${STARTUP_ROTATE_INTERVAL:-300}
  while true; do
    rotate_logs
    sleep "$interval"
  done
}

rotate_daemon &
_ROTATE_DAEMON_PID=$!

# ensure background daemon is killed on container exit to avoid orphaned processes
trap 'kill "${_ROTATE_DAEMON_PID:-}" 2>/dev/null || true; wait "${_ROTATE_DAEMON_PID:-}" 2>/dev/null || true' EXIT

log() {
  # echo to stdout and append to logfile
  echo "$@"
  echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') $@" >> "$LOGFILE"
}

# 1) DB が起きるまで待つ
log "Waiting for DB..."
until psql "$DATABASE_URL" -c 'SELECT 1;' >/dev/null 2>&1; do
  sleep 1
done
log "DB is ready."

# 2) DB が空（alembic_version が存在しない）かチェック
ALEMBIC_EXISTS=$(psql "$DATABASE_URL" -tAc "SELECT to_regclass('public.alembic_version');")

if [ -z "$ALEMBIC_EXISTS" ] || [ "$ALEMBIC_EXISTS" = "" ]; then
  echo "No alembic_version table detected -> treating DB as empty/unnormalized."

  # only restore if backup file exists
    if [ -f /backups/latest.sql ]; then
      log "Restoring backup from /backups/latest.sql ..."
      if psql "$DATABASE_URL" -f /backups/latest.sql 2>&1 | tee -a "$LOGFILE"; then
        log "Backup restore completed."
      else
        log "Backup restore failed; continuing to migrations. See logs for details."
      fi

    # If backup contained schema but not alembic_version, mark alembic as in-sync.
    # Use stamp head so alembic won't try to re-run already-applied DDL.
    if command -v alembic >/dev/null 2>&1; then
      log "Stamping alembic head..."
      # retry stamping a few times in case DB is still settling
      n=0
      until [ "$n" -ge 3 ]; do
        if alembic stamp head 2>&1 | tee -a "$LOGFILE"; then
          log "Alembic stamped successfully."
          break
        fi
        n=$((n+1))
        echo "Stamp attempt $n failed; retrying in 2s..."
        sleep 2
      done
    fi
  else
    log "No /backups/latest.sql found. Will proceed to run migrations to create schema."
  fi
else
  log "alembic_version table present. Skipping automatic restore."
fi

# 3) Ensure migrations are applied (idempotent)
if command -v alembic >/dev/null 2>&1; then
  log "Running alembic upgrade head..."
  # Run alembic with retries to handle transient DB locks
  n=0
  until [ "$n" -ge 5 ]; do
    if alembic upgrade head 2>&1 | tee -a "$LOGFILE"; then
      log "Alembic upgrade completed."
      break
    fi
    n=$((n+1))
    log "Alembic upgrade attempt $n failed; retrying in 3s..."
    sleep 3
  done
  if [ "$n" -ge 5 ]; then
    log "Alembic upgrade failed after multiple attempts; continuing startup (may be inconsistent)."
  fi
fi

# 3b) Ensure required tables exist even if alembic_version indicates head
# There are scenarios where a DB was stamped or otherwise marked as having
# migrations applied while some DDL is missing (e.g. partial restore from
# backups). To be resilient, check critical tables and create them when
# absent. Keep this lightweight and idempotent.
ensure_table() {
  local tbl=$1
  local create_sql=$2
  # use psql against DATABASE_URL; tolerate transient failures
  n=0
  until [ "$n" -ge 5 ]; do
    if psql "$DATABASE_URL" -tAc "SELECT to_regclass('public.${tbl}')" | grep -q -v "^$"; then
      return 0
    fi
    # try to create the table if create_sql provided
    if [ -n "${create_sql}" ]; then
      if psql "$DATABASE_URL" -c "${create_sql}" >> "$LOGFILE" 2>&1; then
        log "Created missing table ${tbl}."
        return 0
      fi
    fi
    n=$((n+1))
    sleep 1
  done
  log "Table ${tbl} still missing after retries."
  return 1
}

# Define create SQL for tables we expect to always exist
CREATE_ITEM_AUDIT_SQL="CREATE TABLE IF NOT EXISTS item_audit (\
  id SERIAL PRIMARY KEY, \
  item_id INTEGER, \
  action VARCHAR(50) NOT NULL, \
  payload JSON, \
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), \
  user_id TEXT, ip TEXT, method TEXT, user_agent TEXT, request_path TEXT\
);"

# Ensure the minimal required tables are present
ensure_table "items" ""
ensure_table "item_audit" "${CREATE_ITEM_AUDIT_SQL}"

# 4) Exec main command (passed from Dockerfile/CMD)
# If no command/args were provided (some compose setups may not pass image CMD),
# fall back to starting uvicorn so the container remains a service.
if [ "$#" -eq 0 ]; then
  log "No command provided; starting uvicorn as default"
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
else
  log "Executing provided command: $@"
  exec "$@"
fi
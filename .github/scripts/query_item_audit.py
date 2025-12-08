#!/usr/bin/env python3
# Script to query item_audit table for debugging
# Usage: python .github/scripts/query_item_audit.py
# Add bellow settings in .github/workflows/ci.yml if needed to debug DATABASE_URL issues
# Example:
#   - name: Query item_audit table (debug)
#     if: always()
#     env:
#       DATABASE_URL: postgresql://user:pass@localhost:5432/appdb_test
#     run: |
#       echo "--- Querying item_audit in DATABASE_URL ---"
#       python .github/scripts/query_item_audit.py || true
import os
import json
from sqlalchemy import create_engine, text


def main():
    db_url = os.getenv("DATABASE_URL")
    print("QUERY SCRIPT: DATABASE_URL=", db_url)
    if not db_url:
        print("No DATABASE_URL; exiting")
        return
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            print("Connected to DB; checking item_audit")
            r = conn.execute(
                text(
                    "SELECT count(*) as cnt FROM item_audit"
                )
            )
            cnt = r.fetchone()
            print("item_audit count:", cnt[0] if cnt is not None else None)

            r2 = conn.execute(
                text(
                    "SELECT id, item_id, payload, method, user_agent, request_path FROM item_audit ORDER BY id DESC LIMIT 5"
                )
            )
            rows = r2.fetchall()
            print("Latest rows:")
            for row in rows:
                id_, item_id, payload_col, method, user_agent, request_path = row
                try:
                    if isinstance(payload_col, (bytes, str)):
                        payload = json.loads(payload_col)
                    else:
                        payload = payload_col
                except Exception:
                    payload = repr(payload_col)
                print({
                    "id": id_,
                    "item_id": item_id,
                    "payload": payload,
                    "method": method,
                    "user_agent": user_agent,
                    "request_path": request_path,
                })
    except Exception as e:
        print("DB query failed:", e)


if __name__ == "__main__":
    main()

# !/usr/bin/env python3
# Script to print database URLs from app.db and environment for debugging
# Usage: python .github/scripts/print_db_urls.py
# Add bellow settings in .github/workflows/ci.yml if needed to debug DATABASE_URL issues
# Example:
#   - name: Print app and env DB URLs
#     env:
#       DATABASE_URL: postgresql://user:pass@localhost:5432/appdb_test
#     run: |
#       echo "--- app + env DB URLs ---"
#       python .github/scripts/print_db_urls.py || true
import sys
import os

try:
    import app.db as db
    engine = getattr(db, "engine", None)
    print("APP_DB_ENGINE_URL:", getattr(engine, "url", "<missing>"))
except Exception as e:
    print("Failed to import app.db:", e)

print("ENV DATABASE_URL:", os.getenv("DATABASE_URL"))

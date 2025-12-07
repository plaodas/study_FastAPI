"""
Simple migration runner for this project.

Usage (from repo root):
  python backend/manage_migrations.py

It will connect to the DATABASE_URL in backend/app/main.py and apply
any SQL files in backend/migrations/ (sorted) that haven't been applied yet.
Applied versions are tracked in the database table `schema_migrations`.
"""
from pathlib import Path
from sqlalchemy import create_engine, text
import re


ROOT = Path(__file__).parent
MIGRATIONS_DIR = ROOT / "migrations"

# import DATABASE_URL from the app
from app.main import DATABASE_URL


def ensure_schema_migrations(conn):
    conn.execute(text(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR PRIMARY KEY,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
        """
    ))


def get_applied(conn):
    res = conn.execute(text("SELECT version FROM schema_migrations"))
    return {row[0] for row in res}


def apply_migration(conn, path: Path):
    sql = path.read_text(encoding="utf8")
    print(f"Applying {path.name}...")
    conn.execute(text(sql))
    conn.execute(text("INSERT INTO schema_migrations (version) VALUES (:v)"), {"v": path.name})


def main():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        ensure_schema_migrations(conn)
        applied = get_applied(conn)
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                print(f"Skipping {path.name} (already applied)")
                continue
            apply_migration(conn, path)
    print("Migrations complete")


if __name__ == "__main__":
    main()

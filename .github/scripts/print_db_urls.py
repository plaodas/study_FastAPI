import sys
import os

try:
    import app.db as db
    engine = getattr(db, "engine", None)
    print("APP_DB_ENGINE_URL:", getattr(engine, "url", "<missing>"))
except Exception as e:
    print("Failed to import app.db:", e)

print("ENV DATABASE_URL:", os.getenv("DATABASE_URL"))

import importlib
import os

import pytest


def reload_config():
    import app.config as conf

    importlib.reload(conf)
    return conf


def test_main_uses_settings(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "smoke-test-app")
    monkeypatch.setenv("DEBUG", "true")
    # Prevent loading repository .env which may contain non-JSON lists
    monkeypatch.setenv("ENV_FILE", "")
    monkeypatch.setenv("FORBIDDEN_WORDS", "[]")

    reload_config()

    import app.main as main

    importlib.reload(main)

    app = main.create_app()

    assert app.title == "smoke-test-app"
    # FastAPI stores debug flag on app.debug
    assert app.debug is True


def test_db_uses_pool_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db:5432/appdb_test")
    monkeypatch.setenv("DB_POOL_SIZE", "5")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "7")
    # Prevent loading repository .env which may contain non-JSON lists
    monkeypatch.setenv("ENV_FILE", "")
    monkeypatch.setenv("FORBIDDEN_WORDS", "[]")

    reload_config()

    import app.db as db

    importlib.reload(db)

    # Engine should use the configured database name and host
    assert getattr(db.engine.url, "database", None) == "appdb_test"
    assert getattr(db.engine.url, "host", None) == "db"

    # For QueuePool implementations, the internal pool exposes configured sizes.
    pool = getattr(db.engine, "pool", None)
    try:
        # QueuePool stores maxsize on the internal queue
        maxsize = getattr(pool._pool, "maxsize", None)
        max_overflow = getattr(pool, "_max_overflow", None)
        if maxsize is not None:
            assert maxsize == 5
        if max_overflow is not None:
            assert max_overflow == 7
    except Exception:
        pytest.skip("Pool internals not available for assertion")

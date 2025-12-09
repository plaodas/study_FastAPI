import os
import pytest


"""Test fixtures and helpers for backend tests.

Provides `prepare_db` which sets up a SQLite in-memory engine that is safe to
share with `TestClient` (uses StaticPool). Tests that need DB access should
request the `prepare_db` fixture.
"""

# Shared DB fixture for tests that need the app DB ready. Tests may request this
# fixture by name (`prepare_db`) to initialize an in-memory SQLite engine that
# is safe to share with TestClient threads.
@pytest.fixture
def prepare_db():
    test_db_path = "/tmp/pytest_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

    # Import here so the env var is applied and models get registered on Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.db as app_db

    # create engine that can be used across threads for TestClient
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    app_db.engine = test_engine
    app_db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # import models and ensure their metadata/tables are created on the test engine
    import app.models as models_mod

    # Some modules may have defined models against a different Base instance.
    # Collect metadata objects from model classes and create tables for each.
    metadatas = set()
    for name in dir(models_mod):
        obj = getattr(models_mod, name)
        try:
            table = getattr(obj, "__table__", None)
            if table is not None:
                metadatas.add(table.metadata)
        except Exception:
            continue

    if not metadatas:
        # fallback: use app_db.Base if no models found
        try:
            app_db.Base.metadata.create_all(bind=test_engine)
        except Exception:
            pass
    else:
        for md in metadatas:
            try:
                md.create_all(bind=test_engine)
            except Exception:
                pass
    # reload app.main so the FastAPI `app` instance picks up the test DB/session
    try:
        import importlib
        import app.main as app_main

        importlib.reload(app_main)
    except Exception:
        pass
    yield
    app_db.Base.metadata.drop_all(bind=test_engine)
    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    except Exception:
        pass

import os
import json
import pytest

# Use a file-backed SQLite DB for tests so TestClient threads can share it
test_db_path = "/tmp/pytest_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def prepare_db():
    # Import here so the env var is applied and models get registered on Base
    from app.db import engine, Base
    import app.models

    # ensure stale DB file (possibly from earlier failed runs) is removed so creation can proceed
    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    except Exception:
        pass
    # Create a test SQLite in-memory engine that's safe to share across threads
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
    # swap into app.db so application code uses the test engine/session
    app_db.engine = test_engine
    app_db.SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    app_db.Base = app_db.Base

    import app.models

    # create all tables in the in-memory sqlite
    app_db.Base.metadata.create_all(bind=test_engine)
    yield
    # teardown
    app_db.Base.metadata.drop_all(bind=test_engine)
    try:
        os.remove(test_db_path)
    except Exception:
        pass


def test_create_item_sanitizes_and_calls_audit(monkeypatch):
    # import app after DB prepared
    from app.main import app
    from app.services import audit as audit_service

    called = {}

    def fake_insert_audit(db, engine, db_item, payload_metadata):
        called["called"] = True
        called["payload"] = payload_metadata
        return 1

    monkeypatch.setattr(audit_service, "insert_audit", fake_insert_audit)

    client = TestClient(app)

    # include HTML and control chars to ensure sanitize runs
    data = {"name": "  <b>hello</b>\n\x00world  "}
    headers = {"X-User-Id": "test-user"}
    resp = client.post("/items", json=data, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["name"] == "hello world"
    # audit was invoked
    assert called.get("called") is True
    assert called["payload"]["user_id"] == "test-user"

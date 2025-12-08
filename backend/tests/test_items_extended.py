import os
import json
import pytest

# Use a file-backed SQLite DB for tests so TestClient threads can share it
test_db_path = "/tmp/pytest_test.db"

from fastapi.testclient import TestClient


@pytest.fixture(autouse=True, scope="module")
def prepare_db():
    # set DATABASE_URL here (fixture runtime) so module import doesn't mutate global env
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
    # Create a test SQLite in-memory engine that's safe to share across threads
    from sqlalchemy import Table, Column, Integer, String, MetaData, JSON, create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.db as app_db

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    app_db.engine = test_engine
    app_db.SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    # Ensure modules that imported `engine` at import-time use the test engine
    try:
        import app.routes.items as items_mod

        items_mod.engine = test_engine
    except Exception:
        # best-effort: if module not imported yet, it's fine
        pass

    import app.models

    app_db.Base.metadata.create_all(bind=test_engine)

    meta = MetaData()
    audit = Table(
        "item_audit",
        meta,
        Column("id", Integer, primary_key=True),
        Column("item_id", Integer),
        Column("action", String),
        Column("payload", JSON),
        Column("user_id", String),
        Column("ip", String),
        Column("method", String),
        Column("user_agent", String),
        Column("request_path", String),
    )
    meta.create_all(bind=test_engine)

    yield

    # teardown
    meta.drop_all(bind=test_engine)
    app_db.Base.metadata.drop_all(bind=test_engine)


def test_forbidden_word_rejected(monkeypatch):
    # set forbidden words env
    monkeypatch.setenv("FORBIDDEN_WORDS", "badword")
    monkeypatch.setenv("VALIDATION_RULES", "/items:POST")

    from app.main import app

    client = TestClient(app)

    resp = client.post("/items", json={"name": "this has badword inside"})
    assert resp.status_code == 400
    assert "forbidden" in resp.json().get("detail", "").lower()


def test_invalid_json_body():
    from app.main import app

    client = TestClient(app)
    # send invalid json (raw text)
    resp = client.post(
        "/items", content="not-json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 400


def test_length_validation():
    from app.main import app

    client = TestClient(app)
    long_name = "x" * 101
    resp = client.post("/items", json={"name": long_name})
    assert resp.status_code == 400


def test_audit_inserts_typed_columns():
    from app.main import app
    from app.db import engine

    client = TestClient(app)

    headers = {"X-User-Id": "int-user", "User-Agent": "pytest-agent"}
    resp = client.post("/items", json={"name": "integration-check"}, headers=headers)
    assert resp.status_code == 201

    # query the item_audit table
    from sqlalchemy import text

    with engine.connect() as conn:
        r = conn.execute(
            text(
                "SELECT item_id, payload, method, user_agent, request_path FROM item_audit ORDER BY id DESC LIMIT 1"
            )
        )
        row = r.fetchone()
        assert row is not None
        payload_col = row[1]
        # payload may be returned as a string for sqlite; normalize to dict
        if isinstance(payload_col, (bytes, str)):
            payload = json.loads(payload_col)
        else:
            payload = payload_col
        assert str(payload.get("user_id")) == "int-user"
        assert row[2] == "POST"
        assert "pytest-agent" in (row[3] or "")

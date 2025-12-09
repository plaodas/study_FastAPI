"""Postgres-specific tests for the audit service.

These tests require a running Postgres instance reachable via the
`TEST_POSTGRES_DSN` environment variable (e.g. "postgresql+psycopg2://user:pass@host:5432/db").
If the variable is not set the tests are skipped so CI jobs without Postgres won't fail.

The test verifies that:
 - `insert_audit` returns an integer id when using Postgres (RETURNING path), and
 - the backfill SQL path updates rows that only had `payload` populated (columns NULL).
"""
import os
import pytest
from sqlalchemy import create_engine, select, text

from app.services import audit as audit_service


TEST_DSN = os.environ.get("TEST_POSTGRES_DSN")


if not TEST_DSN:
    pytest.skip("TEST_POSTGRES_DSN not set; skipping Postgres audit tests", allow_module_level=True)


def test_insert_audit_postgres_returning_and_backfill():
    print("Using TEST_POSTGRES_DSN:", TEST_DSN)
    engine = create_engine(TEST_DSN)

    # ensure table exists
    audit_table = audit_service._get_or_create_audit_table(engine)

    # clean up previous rows for a deterministic test
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE item_audit RESTART IDENTITY CASCADE"))

    # Insert a row that only has payload populated (user_id/ip/method columns NULL)
    payload = {"user_id": "pgtester", "ip": "10.0.0.1", "method": "POST"}
    with engine.begin() as conn:
        conn.execute(audit_table.insert().values(item_id=1, action="create", payload=payload))

    # Now call insert_audit which on Postgres should use RETURNING for its own insert
    dummy = type("D", (), {"id": 2})()
    res = audit_service.insert_audit(None, engine, dummy, {})

    assert getattr(res, "success", False) is True, "insert_audit should succeed on Postgres"
    assert isinstance(res.id, int), "insert_audit should return new id on Postgres"

    # The earlier-manual row should have been backfilled by the function's post-insert SQL
    with engine.connect() as conn:
        sel = select(audit_table.c.user_id, audit_table.c.ip, audit_table.c.method).where(audit_table.c.item_id == 1)
        row = conn.execute(sel).mappings().first()

    assert row is not None, "manual row should exist"
    assert row["user_id"] == "pgtester"
    assert row["ip"] == "10.0.0.1"
    assert row["method"] == "POST"

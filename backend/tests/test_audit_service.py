"""Tests for the audit service.

These tests verify that `insert_audit` creates an `item_audit` row when using
an in-memory SQLite engine. The test uses `StaticPool` so that the same
connection is reused across SQLAlchemy engines/sessions in the test process.
"""
from sqlalchemy import create_engine, MetaData, Table, select
from sqlalchemy.pool import StaticPool
import pytest

from app.services import audit as audit_service


class DummyItem:
    def __init__(self, id_, name):
        self.id = id_
        self.name = name


def test_insert_audit_sqlite():
    # in-memory sqlite engine that is shareable across threads/sessions
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    dummy = DummyItem(42, "widget")
    payload = {"name": "widget", "user_id": "tester", "ip": "127.0.0.1"}

    result = audit_service.insert_audit(None, engine, dummy, payload)

    # Our implementation now returns an AuditInsertResult
    assert getattr(result, "success", False) is True
    assert isinstance(result.id, int)

    # reflect table and assert the row exists
    meta = MetaData()
    audit_table = Table("item_audit", meta, autoload_with=engine)

    with engine.connect() as conn:
        sel = select(audit_table.c.item_id, audit_table.c.payload)
        rows = conn.execute(sel).fetchall()

    assert len(rows) == 1
    item_id, payload_col = rows[0]
    assert item_id == 42
    # payload may be stored as JSON/text depending on dialect; ensure content present
    assert "widget" in str(payload_col)


def test_insert_audit_sqlite_return_row_and_error():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    dummy = DummyItem(43, "widget2")
    payload = {"name": "widget2", "user_id": "tester2"}

    # request the full row back
    res = audit_service.insert_audit(None, engine, dummy, payload, return_row=True)
    assert res.success is True
    assert isinstance(res.id, int)
    assert isinstance(res.row, dict)
    assert res.row.get("item_id") == 43

    # error case: pass an invalid engine and expect AuditError when fail_silent=False
    bad_engine = object()
    with pytest.raises(audit_service.AuditError):
        audit_service.insert_audit(None, bad_engine, dummy, {}, fail_silent=False)

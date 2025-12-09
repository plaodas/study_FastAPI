from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy import Table, MetaData, text, inspect, Column, Integer, String, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import JSON as SA_JSON
import logging


_audit_table_cache = {}


def _get_or_create_audit_table(engine):
    """Return a Table object for `item_audit`, creating it when missing.

    Caches per-engine to avoid repeated reflection/creation.
    """
    # Use engine identity to avoid collisions between distinct Engine
    # objects that may share the same URL (e.g. multiple in-memory sqlite engines).
    key = id(engine)
    if key in _audit_table_cache:
        return _audit_table_cache[key]

    meta = MetaData()
    try:
        inspector = inspect(engine)
    except Exception:
        inspector = None

    if inspector is None or not inspector.has_table("item_audit"):
        # Create deterministically
        audit_table = Table(
            "item_audit",
            meta,
            Column("id", Integer, primary_key=True),
            Column("item_id", Integer),
            Column("action", String),
            Column("payload", SA_JSON),
            Column("user_id", String),
            Column("ip", String),
            Column("method", String),
            Column("user_agent", String),
            Column("request_path", String),
        )
        meta.create_all(bind=engine)
    else:
        audit_table = Table("item_audit", meta, autoload_with=engine)

    _audit_table_cache[key] = audit_table
    return audit_table


@dataclass
class AuditInsertResult:
    success: bool
    id: Optional[int] = None
    row: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AuditError(Exception):
    """Raised when an audit insertion should fail loudly."""


def insert_audit(db, engine, db_item, payload_metadata: dict, *, fail_silent: bool = True, return_row: bool = False) -> AuditInsertResult:
    """Insert an audit row and return an AuditInsertResult.

    Parameters:
    - db: existing DB/session object (not used for insert but kept for API compatibility)
    - engine: SQLAlchemy Engine to use for the insert
    - db_item: the item object containing an `id` attribute
    - payload_metadata: dict payload to store in `payload` column
    - fail_silent: when False, raise `AuditError` on failure; when True return result with success=False
    - return_row: when True, return the inserted row as `row` (dict) when available

    Maintains previous behavior: prefers Postgres `RETURNING` for id retrieval and
    falls back to a deterministic select for other dialects.
    """
    logger = logging.getLogger(__name__)

    try:
        logger.info("insert_audit called for item_id=%s", getattr(db_item, "id", None))
    except Exception:
        pass

    try:
        audit_table = _get_or_create_audit_table(engine)
    except Exception as exc:
        msg = "Failed to ensure item_audit table: %s" % (exc,)
        logging.getLogger(__name__).exception(msg)
        result = AuditInsertResult(success=False, error=msg)
        if not fail_silent:
            raise AuditError(msg)
        return result

    insert_values = {
        "item_id": getattr(db_item, "id", None),
        "action": "create",
        "payload": payload_metadata,
    }
    for key in ("user_id", "ip", "user_agent", "request_path", "method"):
        val = payload_metadata.get(key)
        if val is not None:
            insert_values[key] = val

    Session = sessionmaker(bind=engine)
    new_audit_id = None
    inserted_row = None
    try:
        with Session() as s:
            try:
                bind = s.get_bind()
                logger.debug("Audit session bind=%s", getattr(bind, "url", str(bind)))
            except Exception:
                pass

            ins = audit_table.insert().values(**insert_values)

            # Prefer RETURNING on Postgres to get the inserted id (and optionally the row)
            if engine.dialect.name == "postgresql":
                try:
                    if return_row:
                        ins = ins.returning(*audit_table.c)
                        result = s.execute(ins)
                        row = result.mappings().fetchone()
                        if row:
                            inserted_row = dict(row)
                            new_audit_id = inserted_row.get("id")
                    else:
                        ins = ins.returning(audit_table.c.id)
                        result = s.execute(ins)
                        new_audit_id = result.scalar_one_or_none()
                    s.commit()
                except Exception as exc:
                    s.rollback()
                    logger.exception("Postgres audit INSERT failed")
                    err = f"Postgres INSERT failed: {exc}"
                    if not fail_silent:
                        raise AuditError(err)
                    return AuditInsertResult(success=False, id=None, row=None, error=err)
            else:
                try:
                    s.execute(ins)
                    s.commit()
                except Exception as exc:
                    s.rollback()
                    logger.exception("Audit INSERT failed")
                    err = f"Audit INSERT failed: {exc}"
                    if not fail_silent:
                        raise AuditError(err)
                    return AuditInsertResult(success=False, id=None, row=None, error=err)

                # best-effort: fetch last id deterministically
                try:
                    with engine.connect() as conn:
                        sel = select(audit_table.c.id).order_by(audit_table.c.id.desc()).limit(1)
                        new_audit_id = conn.execute(sel).scalar_one_or_none()
                except Exception:
                    logger.exception("Failed to fetch new audit id after insert")
                    new_audit_id = None

            # Postgres-only backfill: keep behavior for typed columns
            if engine.dialect.name == "postgresql":
                try:
                    backfill_sql = text(
                        "UPDATE item_audit SET "
                        "user_id = COALESCE(user_id, payload ->> 'user_id'), "
                        "ip = COALESCE(ip, payload ->> 'ip'), "
                        "method = COALESCE(method, payload ->> 'method'), "
                        "user_agent = COALESCE(user_agent, payload ->> 'user_agent'), "
                        "request_path = COALESCE(request_path, payload ->> 'request_path') "
                        "WHERE payload IS NOT NULL AND (user_id IS NULL OR ip IS NULL OR method IS NULL OR user_agent IS NULL OR request_path IS NULL)"
                    )
                    s.execute(backfill_sql)
                    s.commit()
                except Exception:
                    logger.exception("Postgres backfill failed")

    except SQLAlchemyError:
        logger.exception("SQLAlchemyError during audit insertion")
        if not fail_silent:
            raise AuditError("SQLAlchemyError during audit insertion")
        return AuditInsertResult(success=False, id=None, row=None, error="SQLAlchemyError during audit insertion")
    except Exception:
        logger.exception("Unexpected exception during audit insertion")
        if not fail_silent:
            raise AuditError("Unexpected exception during audit insertion")
        return AuditInsertResult(success=False, id=None, row=None, error="Unexpected exception during audit insertion")

    # Optionally fetch the full row for non-postgres case when requested
    if return_row and inserted_row is None and new_audit_id is not None:
        try:
            with engine.connect() as conn:
                sel = select(audit_table).where(audit_table.c.id == new_audit_id)
                row = conn.execute(sel).mappings().fetchone()
                if row:
                    inserted_row = dict(row)
        except Exception:
            logger.exception("Failed to fetch inserted audit row")

    try:
        logger.info("insert_audit finished for item_id=%s", insert_values.get("item_id"))
    except Exception:
        pass

    return AuditInsertResult(success=True, id=new_audit_id, row=inserted_row, error=None)

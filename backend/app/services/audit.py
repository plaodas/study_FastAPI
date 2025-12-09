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
    key = getattr(engine, "url", None) or id(engine)
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


def insert_audit(db, engine, db_item, payload_metadata: dict):
    """Insert an audit row for the given item and return the new id when available.

    Uses a short-lived session bound to `engine`. On PostgreSQL the function
    attempts to use `RETURNING` to obtain the new id; on other dialects it falls
    back to a safe query after commit.
    """
    logger = logging.getLogger(__name__)

    try:
        logger.info("insert_audit called for item_id=%s", getattr(db_item, "id", None))
    except Exception:
        pass

    try:
        audit_table = _get_or_create_audit_table(engine)
    except Exception:
        logging.getLogger(__name__).exception("Failed to ensure item_audit table")
        return None

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
    try:
        with Session() as s:
            try:
                bind = s.get_bind()
                logger.debug("Audit session bind=%s", getattr(bind, "url", str(bind)))
            except Exception:
                pass

            ins = audit_table.insert().values(**insert_values)

            # Prefer RETURNING on Postgres to get the inserted id
            if engine.dialect.name == "postgresql":
                try:
                    ins = ins.returning(audit_table.c.id)
                    result = s.execute(ins)
                    new_audit_id = result.scalar_one_or_none()
                    s.commit()
                except Exception:
                    s.rollback()
                    logger.exception("Postgres audit INSERT failed")
                    new_audit_id = None
            else:
                try:
                    s.execute(ins)
                    s.commit()
                except Exception:
                    s.rollback()
                    logger.exception("Audit INSERT failed")
                    return None

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
        new_audit_id = None
    except Exception:
        logger.exception("Unexpected exception during audit insertion")
        new_audit_id = None

    try:
        logger.info("insert_audit finished for item_id=%s", insert_values.get("item_id"))
    except Exception:
        pass

    return new_audit_id

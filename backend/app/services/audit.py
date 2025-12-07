from sqlalchemy import Table, MetaData, text, inspect, Column, Integer, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import JSON as SA_JSON
import logging


def insert_audit(db, engine, db_item, payload_metadata: dict):
    """Insert an audit row for the given item in a deterministic way.

    - Ensures the `item_audit` table exists on the provided `engine` before inserting.
    - Uses a short-lived session bound to `engine` to perform INSERT and any backfill
      in the same transactional context to avoid cross-connection races (important for
      in-memory SQLite tests).
    - Avoids relying on RETURNING for SQLite compatibility; this function focuses on
      reliably inserting the audit row (the caller may inspect the table if needed).
    Returns the new audit id when available, else None.
    """
    logger = logging.getLogger("uvicorn.error")
    meta = MetaData()
    try:
        logger.info(
            "insert_audit called for item_id=%s payload_keys=%s",
            getattr(db_item, "id", None),
            (
                list(payload_metadata.keys())
                if isinstance(payload_metadata, dict)
                else None
            ),
        )
    except Exception:
        # best-effort logging, don't fail the flow
        pass

    try:
        inspector = inspect(engine)
    except Exception:
        inspector = None

    # Ensure audit table exists on the engine. Create it deterministically when missing.
    if inspector is None or not inspector.has_table("item_audit"):
        try:
            # Use SA_JSON for JSON column where supported; SQLite will store JSON as text.
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
        except Exception:
            logging.getLogger("uvicorn.error").exception(
                "Failed to create item_audit table on engine"
            )
            return None
    else:
        # reflect existing table
        try:
            audit_table = Table("item_audit", meta, autoload_with=engine)
        except Exception:
            logging.getLogger("uvicorn.error").exception(
                "Failed to reflect item_audit table"
            )
            return None

    insert_values = {
        "item_id": db_item.id,
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
            # perform insert
            ins = audit_table.insert().values(**insert_values)
            try:
                logger.info(
                    "About to execute audit INSERT with values: %s", insert_values
                )
            except Exception:
                pass
            s.execute(ins)
            s.commit()
            try:
                logger.info(
                    "Audit INSERT committed for item_id=%s",
                    insert_values.get("item_id"),
                )
            except Exception:
                pass

            # best-effort backfill for typed columns (Postgres JSON operators used previously)
            # For portability, on Postgres use the JSON ->> operator; on SQLite the payload
            # column is JSON/text so the backfill may be a no-op in tests. Keep the SQL safe.
            if engine.dialect.name == "postgresql":
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
            else:
                # For SQLite (tests), keep backfill lightweight or skip because JSON operators differ.
                pass
    except SQLAlchemyError as e:
        logger.exception(
            "SQLAlchemyError during core audit INSERT. values=%s", insert_values
        )
        new_audit_id = None
    except Exception as e:
        logger.exception(
            "Unexpected exception during audit insert. values=%s", insert_values
        )
        new_audit_id = None

    return new_audit_id

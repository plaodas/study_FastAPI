from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from app.middleware.validation import ValidationMiddleware
from pydantic import BaseModel, constr
import re
from sqlalchemy import Column, Integer, String, create_engine, Table, MetaData
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import json
from sqlalchemy import text
import logging
import sys

DATABASE_URL = "postgresql://user:pass@db:5432/appdb"

engine = create_engine(DATABASE_URL)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- モデル定義 ---
class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Add validation middleware early so requests are sanitized before route handlers
app.add_middleware(ValidationMiddleware)

# Allow requests from the frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DBセッション依存性 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- APIエンドポイント ---
@app.get("/items")
def read_items(db: Session = Depends(get_db)):
    return db.query(Item).all()


@app.get("/health")
def health():
    return {"status": "ok"}


# ----- POST: create a new item -----
class ItemCreate(BaseModel):
    name: constr(min_length=1, max_length=100)


import pydantic


def _pydantic_is_v2() -> bool:
    try:
        ver = tuple(int(x) for x in pydantic.__version__.split("."))
        return ver[0] >= 2
    except Exception:
        return False


if _pydantic_is_v2():
    class ItemRead(BaseModel):
        id: int
        name: str

        model_config = {"from_attributes": True}
else:
    class ItemRead(BaseModel):
        id: int
        name: str

        class Config:
            orm_mode = True


@app.post("/items", response_model=ItemRead, status_code=201)
async def create_item(request: Request, db: Session = Depends(get_db)):
    # Prefer validated payload from middleware if present
    validated = getattr(request.state, "validated_json", None)
    if validated is None:
        # fallback: read and validate body here
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")
        validated = payload

    # Use Pydantic model for final validation
    item = ItemCreate(**validated)
    # server-side sanitization: strip HTML tags and control characters
    def sanitize(s: str) -> str:
        # remove HTML tags
        s = re.sub(r"<[^>]*>", "", s)
        # remove control chars except newline/tab/space
        s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", s)
        # normalize whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s

    # sanitize name before persisting
    clean_name = sanitize(item.name)
    db_item = Item(name=clean_name)
    # add and flush so we have an id assigned before inserting audit
    db.add(db_item)
    db.flush()

    # determine user info for audit
    # prefer X-User-Id header if present
    user_id = None
    try:
        user_id = request.headers.get("x-user-id")
    except Exception:
        user_id = None

    # try to get client IP (may be proxied)
    ip = None
    try:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            ip = xff.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else None
    except Exception:
        ip = None

    # user agent, request path, method
    try:
        user_agent = request.headers.get("user-agent")
    except Exception:
        user_agent = None

    try:
        request_path = request.url.path
    except Exception:
        request_path = None

    try:
        method = request.method
    except Exception:
        method = None

    # insert audit record using table reflection
    meta = MetaData()
    try:
        audit_table = Table('item_audit', meta, autoload_with=engine)
        # include metadata in the JSON payload so the information is stored
        # and can be used to backfill typed columns if needed
        payload = {
            "name": db_item.name,
            "user_id": user_id,
            "ip": ip,
            "user_agent": user_agent,
            "request_path": request_path,
            "method": method,
        }
        # prepare values for typed columns if present
        insert_values = {
            "item_id": db_item.id,
            "action": "create",
            "payload": payload,
        }
        if user_id is not None:
            insert_values["user_id"] = user_id
        if ip is not None:
            insert_values["ip"] = ip
        if user_agent is not None:
            insert_values["user_agent"] = user_agent
        if request_path is not None:
            insert_values["request_path"] = request_path
        if method is not None:
            insert_values["method"] = method

        # Use SQLAlchemy Core insert via the reflected table so parameter binding (including JSON)
        # is handled correctly and we avoid manual ::json casting which can break param styles.
        try:
            ins = audit_table.insert().values(**insert_values).returning(audit_table.c.id)
            try:
                res = db.execute(ins)
                row = res.fetchone()
                new_audit_id = row[0] if row is not None else None
            except Exception:
                logging.getLogger("uvicorn.error").exception("Exception during core audit INSERT")
                new_audit_id = None
        except Exception:
            # if reflection or insert fails, fall back to other strategies below
            new_audit_id = None
    except Exception:
        # if audit table doesn't exist, skip silently (migration may not be applied)
        pass

    # commit and refresh the ORM object; if refresh fails, log and try a simple re-query
    try:
        db.commit()
    except Exception:
        logging.getLogger("uvicorn.error").exception("Error committing transaction for item %s", getattr(db_item, 'id', None))
        # best-effort: continue to attempt to return the created item

    try:
        db.refresh(db_item)
    except Exception:
        logging.getLogger("uvicorn.error").warning("Could not refresh item instance id=%s; performing simple re-query", getattr(db_item, 'id', None))
        try:
            db_item = db.query(Item).filter_by(id=getattr(db_item, 'id', None)).one_or_none()
        except Exception:
            logging.getLogger("uvicorn.error").exception("Failed to re-query item after refresh failure")

    # Backfill typed audit columns from payload JSON for rows where typed columns are NULL.
    # This is a simple and reliable fallback: copy values from payload ->> key into typed columns.
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
        # use a fresh engine connection to ensure visibility and avoid Session snapshot issues
        with engine.begin() as conn:
            conn.execute(backfill_sql)
    except Exception:
        # don't fail request if backfill fails
        pass
    return db_item
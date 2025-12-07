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

DATABASE_URL = "postgresql://user:pass@db:5432/appdb"

engine = create_engine(DATABASE_URL)
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

    db_item = Item(name=item.name)
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
        payload = {"name": db_item.name}
        if user_id is not None:
            payload["user_id"] = user_id
        if ip is not None:
            payload["ip"] = ip
        if user_agent is not None:
            payload["user_agent"] = user_agent
        if request_path is not None:
            payload["request_path"] = request_path
        if method is not None:
            payload["method"] = method
        db.execute(audit_table.insert().values(item_id=db_item.id, action='create', payload=payload))
    except Exception:
        # if audit table doesn't exist, skip silently (migration may not be applied)
        pass

    db.commit()
    db.refresh(db_item)
    return db_item
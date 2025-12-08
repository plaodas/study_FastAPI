from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db, engine, SessionLocal
from app import models, schemas
from app.utils import sanitize, extract_request_metadata
from app.services import audit as audit_service

router = APIRouter()


@router.get("/items")
def read_items(db: Session = Depends(get_db)):
    return db.query(models.Item).all()


@router.post("/items", response_model=schemas.ItemRead, status_code=201)
async def create_item(request: Request, db: Session = Depends(get_db)):
    validated = getattr(request.state, "validated_json", None)
    if validated is None:
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body"
            )
        validated = payload

    item_in = schemas.ItemCreate(**validated)
    clean_name = sanitize(item_in.name)
    db_item = models.Item(name=clean_name)
    db.add(db_item)
    db.flush()

    # capture id and payload early
    item_id = getattr(db_item, "id", None)
    meta = extract_request_metadata(request)
    payload = {"name": db_item.name, **meta}

    try:
        db.commit()
    except Exception:
        import logging

        logging.getLogger("uvicorn.error").exception(
            "Error committing transaction for item %s", item_id
        )

    # refresh the instance from DB; if that fails, re-query by id
    try:
        db.refresh(db_item)
    except Exception:
        import logging

        logging.getLogger("uvicorn.error").warning(
            "Could not refresh item instance id=%s; performing simple re-query", item_id
        )
        try:
            db_item = db.query(models.Item).filter_by(id=item_id).one_or_none()
        except Exception:
            logging.getLogger("uvicorn.error").exception(
                "Failed to re-query item after refresh failure"
            )

    # perform audit insertion in a separate short-lived session to avoid interfering with request session
    try:
        with SessionLocal() as audit_db:
            # import app.db here so we get the current engine value (tests may swap it)
            import app.db as app_db
            import logging

            logger = logging.getLogger("uvicorn.error")
            try:
                # Also print to stdout so CI's nohup/uvicorn.log captures it reliably
                print(f"DEBUG: Calling insert_audit for item_id={getattr(db_item, 'id', None)}")
                logger.info("Calling insert_audit for item_id=%s", getattr(db_item, "id", None))
                audit_service.insert_audit(audit_db, app_db.engine, db_item, payload)
                print(f"DEBUG: insert_audit completed for item_id={getattr(db_item, 'id', None)}")
                logger.info("insert_audit completed for item_id=%s", getattr(db_item, "id", None))
            except Exception:
                # Print before logging exception so it's visible even if logger config is odd
                print(f"DEBUG: insert_audit raised an exception for item_id={getattr(db_item, 'id', None)}")
                logger.exception("insert_audit raised an exception for item_id=%s", getattr(db_item, "id", None))
    except Exception:
        # errors are logged in the service; don't fail request
        pass

    return db_item

from __future__ import annotations

from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

def create_entity(db: Session, model, payload):
    entity = model(**payload.model_dump())
    try:
        db.add(entity)
        db.commit()
        db.refresh(entity)
        return entity
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A record with that unique value already exists")

def list_entities(db: Session, model, limit: int, offset: int, search: Optional[str] = None):
    query = select(model).order_by(model.created_at.desc()).limit(limit).offset(offset)
    if search and hasattr(model, "name"):
        query = query.where(model.name.ilike(f"%{search.strip()}%"))
    return list(db.scalars(query))

def update_entity(db: Session, model, record_id, payload):
    entity = db.get(model, record_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record was not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entity, field, value)
    try:
        db.commit(); db.refresh(entity); return entity
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A record with that unique value already exists")

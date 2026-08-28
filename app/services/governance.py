import json
from datetime import date
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.governance import AccountingPeriod, AuditLog


def ensure_open_period(db: Session, transaction_date: date):
    period = db.scalar(select(AccountingPeriod).where(AccountingPeriod.is_closed.is_(True), AccountingPeriod.start_date <= transaction_date, AccountingPeriod.end_date >= transaction_date))
    if period:
        raise HTTPException(status_code=422, detail=f"Accounting period '{period.name}' is closed")


def audit(db: Session, *, action: str, entity_type: str, entity_id=None, user_id=None, details: Optional[dict] = None):
    db.add(AuditLog(action=action, entity_type=entity_type, entity_id=str(entity_id) if entity_id else None, user_id=user_id, details=json.dumps(details, default=str) if details else None))

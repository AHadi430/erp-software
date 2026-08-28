from __future__ import annotations

import uuid
from datetime import date
from typing import Optional
from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.common import UUIDTimestampMixin


class AccountingPeriod(UUIDTimestampMixin, Base):
    __tablename__ = "accounting_periods"
    name: Mapped[str] = mapped_column(String(100), unique=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    closed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


class AuditLog(UUIDTimestampMixin, Base):
    __tablename__ = "audit_logs"
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    details: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), index=True)

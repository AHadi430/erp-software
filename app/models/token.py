from __future__ import annotations

import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.common import UUIDTimestampMixin

class TokenClaimStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    VOID = "void"

class TokenClaim(UUIDTimestampMixin, Base):
    __tablename__ = "token_claims"
    claim_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    claim_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    painter_name: Mapped[str] = mapped_column(String(180), index=True)
    painter_phone: Mapped[Optional[str]] = mapped_column(String(40))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    token_value: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[TokenClaimStatus] = mapped_column(Enum(TokenClaimStatus), default=TokenClaimStatus.PENDING, index=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(30))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("journal_entries.id"))
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))

from __future__ import annotations

import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Boolean, CheckConstraint, Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.common import UUIDTimestampMixin


class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class TaxRate(UUIDTimestampMixin, Base):
    __tablename__ = "tax_rates"
    name: Mapped[str] = mapped_column(String(100), unique=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    is_inclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Account(UUIDTimestampMixin, Base):
    __tablename__ = "accounts"
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), index=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("accounts.id"))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class JournalEntry(UUIDTimestampMixin, Base):
    __tablename__ = "journal_entries"
    entry_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    entry_date: Mapped[date] = mapped_column(Date, default=date.today)
    memo: Mapped[Optional[str]] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    posted_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    is_posted: Mapped[bool] = mapped_column(Boolean, default=False)


class JournalLine(UUIDTimestampMixin, Base):
    __tablename__ = "journal_lines"
    __table_args__ = (CheckConstraint("(debit = 0 AND credit > 0) OR (credit = 0 AND debit > 0)", name="ck_journal_line_one_side"),)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("journal_entries.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    description: Mapped[Optional[str]] = mapped_column(String(255))

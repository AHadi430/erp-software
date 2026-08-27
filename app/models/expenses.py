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

class CashTransactionType(str, enum.Enum):
    RECEIPT = "receipt"
    PAYMENT = "payment"
    TRANSFER = "transfer"

class ExpenseCategory(UUIDTimestampMixin, Base):
    __tablename__ = "expense_categories"
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)

class Expense(UUIDTimestampMixin, Base):
    __tablename__ = "expenses"
    expense_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    expense_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    description: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("expense_categories.id"))
    expense_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    cash_bank_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("journal_entries.id"))
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)

class CashBankTransaction(UUIDTimestampMixin, Base):
    __tablename__ = "cash_bank_transactions"
    transaction_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    transaction_type: Mapped[CashTransactionType] = mapped_column(Enum(CashTransactionType), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    offset_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("journal_entries.id"))
    description: Mapped[str] = mapped_column(String(255))
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

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


class StockMovementType(str, enum.Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    SALES_RETURN = "sales_return"
    PURCHASE_RETURN = "purchase_return"
    ADJUSTMENT = "adjustment"
    DAMAGE = "damage"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    OTHER = "other"


class StockMovement(UUIDTimestampMixin, Base):
    __tablename__ = "stock_movements"
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True)
    movement_type: Mapped[StockMovementType] = mapped_column(Enum(StockMovementType), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    reference_type: Mapped[str] = mapped_column(String(50), index=True)
    reference_id: Mapped[str] = mapped_column(String(50), index=True)
    occurred_on: Mapped[date] = mapped_column(Date, default=date.today)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))


class Payment(UUIDTimestampMixin, Base):
    __tablename__ = "payments"
    payment_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    payment_date: Mapped[date] = mapped_column(Date, default=date.today)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod))
    direction: Mapped[str] = mapped_column(String(20), index=True)  # receipt or disbursement
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("customers.id"))
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("suppliers.id"))
    cash_bank_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("journal_entries.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class PaymentAllocation(UUIDTimestampMixin, Base):
    __tablename__ = "payment_allocations"
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), index=True)
    sales_invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("sales_invoices.id"), index=True)
    purchase_invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("purchase_invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))

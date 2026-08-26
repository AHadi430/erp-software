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


class ReturnType(str, enum.Enum):
    SALES_RETURN = "sales_return"
    PURCHASE_RETURN = "purchase_return"


class ReturnDocument(UUIDTimestampMixin, Base):
    __tablename__ = "return_documents"
    return_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    return_type: Mapped[ReturnType] = mapped_column(Enum(ReturnType), index=True)
    return_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    sales_invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("sales_invoices.id"), index=True)
    purchase_invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("purchase_invoices.id"), index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("journal_entries.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class ReturnItem(UUIDTimestampMixin, Base):
    __tablename__ = "return_items"
    return_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("return_documents.id", ondelete="CASCADE"), index=True)
    source_line_id: Mapped[uuid.UUID] = mapped_column(index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))

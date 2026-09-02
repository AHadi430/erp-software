from __future__ import annotations
import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.common import UUIDTimestampMixin
from app.models.operations import PaymentMethod
class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"
class SalesInvoice(UUIDTimestampMixin, Base):
    __tablename__ = "sales_invoices"
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    invoice_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, index=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), default=PaymentMethod.CASH)
    tax_inclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    due_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    returned_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("journal_entries.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
class SalesInvoiceItem(UUIDTimestampMixin, Base):
    __tablename__ = "sales_invoice_items"
    sales_invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sales_invoices.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    token_included: Mapped[bool] = mapped_column(Boolean, default=False)
    token_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
class PurchaseInvoice(UUIDTimestampMixin, Base):
    __tablename__ = "purchase_invoices"
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    supplier_invoice_number: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    invoice_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"), index=True)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, index=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), default=PaymentMethod.CASH)
    tax_inclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    due_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    returned_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    journal_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("journal_entries.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
class PurchaseInvoiceItem(UUIDTimestampMixin, Base):
    __tablename__ = "purchase_invoice_items"
    purchase_invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_invoices.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    token_included: Mapped[bool] = mapped_column(Boolean, default=False)
    token_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

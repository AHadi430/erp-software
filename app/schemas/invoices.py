from __future__ import annotations
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.operations import PaymentMethod
class InvoiceItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0, decimal_places=3)
    unit_price: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    tax_rate: Optional[Decimal] = Field(default=None, ge=0, le=100, decimal_places=4)
    token_included: bool = False
    token_value: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
class SalesInvoiceCreate(BaseModel):
    customer_id: Optional[uuid.UUID] = None
    invoice_date: date = Field(default_factory=date.today)
    payment_method: PaymentMethod = PaymentMethod.CASH
    paid_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    tax_inclusive: bool = False
    notes: Optional[str] = None
    items: list[InvoiceItemCreate] = Field(min_length=1)
class PurchaseInvoiceCreate(BaseModel):
    supplier_id: uuid.UUID
    supplier_invoice_number: Optional[str] = Field(default=None, max_length=80)
    invoice_date: date = Field(default_factory=date.today)
    payment_method: PaymentMethod = PaymentMethod.CASH
    paid_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    tax_inclusive: bool = False
    notes: Optional[str] = None
    items: list[InvoiceItemCreate] = Field(min_length=1)
class InvoiceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    unit_cost: Optional[Decimal] = None
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_total: Decimal
    token_included: bool = False
    token_value: Decimal = Decimal("0")
class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_number: str
    invoice_date: date
    customer_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None
    status: str
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    grand_total: Decimal
    paid_amount: Decimal
    due_amount: Decimal
    notes: Optional[str]
    items: list[InvoiceItemRead] = []

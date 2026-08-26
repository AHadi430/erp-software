from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, model_validator
from app.models.operations import PaymentMethod


class PaymentAllocationCreate(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal = Field(gt=0, decimal_places=2)


class CustomerReceiptCreate(BaseModel):
    customer_id: uuid.UUID
    amount: Decimal = Field(gt=0, decimal_places=2)
    method: PaymentMethod = PaymentMethod.CASH
    payment_date: date = Field(default_factory=date.today)
    notes: Optional[str] = None
    allocations: list[PaymentAllocationCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def allocations_match_payment(self):
        if sum(item.amount for item in self.allocations) != self.amount:
            raise ValueError("Allocation amounts must exactly equal the payment amount")
        return self


class SupplierPaymentCreate(BaseModel):
    supplier_id: uuid.UUID
    amount: Decimal = Field(gt=0, decimal_places=2)
    method: PaymentMethod = PaymentMethod.CASH
    payment_date: date = Field(default_factory=date.today)
    notes: Optional[str] = None
    allocations: list[PaymentAllocationCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def allocations_match_payment(self):
        if sum(item.amount for item in self.allocations) != self.amount:
            raise ValueError("Allocation amounts must exactly equal the payment amount")
        return self


class PaymentRead(BaseModel):
    id: uuid.UUID
    payment_number: str
    payment_date: date
    amount: Decimal
    direction: str
    method: PaymentMethod

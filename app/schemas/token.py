from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class TokenClaimCreate(BaseModel):
    painter_name: str = Field(min_length=1, max_length=180)
    painter_phone: Optional[str] = Field(default=None, max_length=40)
    quantity: Decimal = Field(gt=0, decimal_places=0)
    token_value: Decimal = Field(gt=0, decimal_places=2)
    claim_date: date = Field(default_factory=date.today)
    notes: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_whole(cls, value: Decimal) -> Decimal:
        if value != value.to_integral_value():
            raise ValueError("Token quantity must be a whole number")
        return value

class TokenProductUpdate(BaseModel):
    token_enabled: bool
    token_value: Decimal = Field(ge=0, decimal_places=2)

class TokenClaimRead(BaseModel):
    id: uuid.UUID
    claim_number: str
    claim_date: date
    painter_name: str
    painter_phone: Optional[str]
    quantity: Decimal
    token_value: Decimal
    total_amount: Decimal
    status: str
    payment_method: Optional[str]
    notes: Optional[str]

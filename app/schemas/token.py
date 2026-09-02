from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

class TokenClaimCreate(BaseModel):
    painter_name: str = Field(min_length=1, max_length=180)
    painter_phone: Optional[str] = Field(default=None, max_length=40)
    quantity: Decimal = Field(gt=0, decimal_places=3)
    token_value: Decimal = Field(gt=0, decimal_places=2)
    claim_date: date = Field(default_factory=date.today)
    notes: Optional[str] = None

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

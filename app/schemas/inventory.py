from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

class StockItemRead(BaseModel):
    product_id: uuid.UUID
    sku: str
    name: str
    packaging: str
    quantity: Decimal
    unit_cost: Decimal
    value: Decimal
    minimum_stock: Decimal
    is_low_stock: bool

class StockAdjustmentCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(ne=0, decimal_places=3)
    unit_cost: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2)
    notes: str = Field(min_length=3, max_length=1000)

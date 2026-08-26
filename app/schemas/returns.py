from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class ReturnLineCreate(BaseModel):
    source_line_id: uuid.UUID
    quantity: Decimal = Field(gt=0, decimal_places=3)


class ReturnCreate(BaseModel):
    return_date: date = Field(default_factory=date.today)
    notes: Optional[str] = None
    items: list[ReturnLineCreate] = Field(min_length=1)

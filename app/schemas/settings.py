from __future__ import annotations

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class BusinessSettingsUpdate(BaseModel):
    business_name: str = Field(min_length=2, max_length=180)
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_number: Optional[str] = None
    invoice_prefix: str = Field(default="INV", min_length=1, max_length=20)
    show_tax_on_invoice: bool = True

class BusinessSettingsRead(BusinessSettingsUpdate):
    model_config = ConfigDict(from_attributes=True)

class TaxRateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rate: Decimal = Field(ge=0, le=100, decimal_places=4)
    is_inclusive: bool = False

class TaxRateRead(TaxRateCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    is_active: bool

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    is_active: bool


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: bool = True

class CategoryRead(EntityRead):
    name: str
    description: Optional[str]

class BrandCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True

class BrandRead(EntityRead):
    name: str

class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    barcode: Optional[str] = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=180)
    brand_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    paint_type: Optional[str] = None
    shade_code: Optional[str] = None
    shade_name: Optional[str] = None
    volume: Optional[str] = None
    unit: str = "each"
    cost_price: Decimal = Field(default=Decimal("0"), ge=0)
    selling_price: Decimal = Field(ge=0)
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0)
    tax_rate_id: Optional[uuid.UUID] = None
    is_active: bool = True

class ProductRead(ProductCreate, EntityRead):
    pass

class PartyBase(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    phone: Optional[str] = Field(default=None, max_length=40)
    email: Optional[str] = Field(default=None, max_length=255)
    address: Optional[str] = None
    tax_number: Optional[str] = Field(default=None, max_length=80)
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0)
    is_active: bool = True

class CustomerCreate(PartyBase):
    credit_limit: Decimal = Field(default=Decimal("0"), ge=0)

class CustomerRead(CustomerCreate, EntityRead):
    pass

class SupplierCreate(PartyBase):
    pass

class SupplierRead(SupplierCreate, EntityRead):
    pass

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.common import UUIDTimestampMixin

class Category(UUIDTimestampMixin, Base):
    __tablename__ = "categories"
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Brand(UUIDTimestampMixin, Base):
    __tablename__ = "brands"
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Product(UUIDTimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (Index("ix_products_brand_category", "brand_id", "category_id"),)
    sku: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("brands.id"))
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("categories.id"))
    paint_type: Mapped[Optional[str]] = mapped_column(String(100))
    shade_code: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    shade_name: Mapped[Optional[str]] = mapped_column(String(120))
    volume: Mapped[Optional[str]] = mapped_column(String(50))
    packaging: Mapped[str] = mapped_column(String(30), default="Other", index=True)
    unit: Mapped[str] = mapped_column(String(30), default="each")
    cost_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    selling_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    tax_rate_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("tax_rates.id"))
    token_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    token_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Customer(UUIDTimestampMixin, Base):
    __tablename__ = "customers"
    name: Mapped[str] = mapped_column(String(180), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    address: Mapped[Optional[str]] = mapped_column(Text)
    tax_number: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Supplier(UUIDTimestampMixin, Base):
    __tablename__ = "suppliers"
    name: Mapped[str] = mapped_column(String(180), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    address: Mapped[Optional[str]] = mapped_column(Text)
    tax_number: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

from __future__ import annotations

from typing import Optional
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.common import UUIDTimestampMixin


class BusinessSettings(UUIDTimestampMixin, Base):
    __tablename__ = "business_settings"
    business_name: Mapped[str] = mapped_column(String(180), default="Paint Shop")
    address: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    tax_number: Mapped[Optional[str]] = mapped_column(String(100))
    invoice_prefix: Mapped[str] = mapped_column(String(20), default="INV")
    show_tax_on_invoice: Mapped[bool] = mapped_column(Boolean, default=True)

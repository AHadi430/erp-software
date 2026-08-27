from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from app.models.expenses import CashTransactionType

class ExpenseCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

class ExpenseCreate(BaseModel):
    expense_date: date = Field(default_factory=date.today)
    description: str = Field(min_length=2, max_length=255)
    amount: Decimal = Field(gt=0, decimal_places=2)
    category_id: Optional[uuid.UUID] = None
    expense_account_id: uuid.UUID
    cash_bank_account_id: uuid.UUID
    notes: Optional[str] = None

class CashTransactionCreate(BaseModel):
    transaction_date: date = Field(default_factory=date.today)
    transaction_type: CashTransactionType
    amount: Decimal = Field(gt=0, decimal_places=2)
    account_id: uuid.UUID
    offset_account_id: uuid.UUID
    description: str = Field(min_length=2, max_length=255)

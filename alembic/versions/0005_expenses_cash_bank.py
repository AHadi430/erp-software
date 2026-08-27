"""expenses and cash bank transactions

Revision ID: 0005_expenses_cash_bank
Revises: 0004_settings
Create Date: 2026-08-27
"""
from alembic import op
from app.database.base import Base
import app.models  # noqa: F401
revision = "0005_expenses_cash_bank"
down_revision = "0004_settings"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    for table in ("expense_categories", "expenses", "cash_bank_transactions"):
        Base.metadata.tables[table].create(bind=bind, checkfirst=True)

def downgrade() -> None:
    bind = op.get_bind()
    for table in ("cash_bank_transactions", "expenses", "expense_categories"):
        Base.metadata.tables[table].drop(bind=bind, checkfirst=True)

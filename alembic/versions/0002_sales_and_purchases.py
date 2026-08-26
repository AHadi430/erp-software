"""sales and purchase documents

Revision ID: 0002_sales_purchases
Revises: 0001_initial_core
Create Date: 2026-08-24
"""
from alembic import op
from app.database.base import Base
import app.models  # noqa: F401

revision = "0002_sales_purchases"
down_revision = "0001_initial_core"
branch_labels = None
depends_on = None

TABLES = ["sales_invoices", "sales_invoice_items", "purchase_invoices", "purchase_invoice_items"]

def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        Base.metadata.tables[table].create(bind=bind, checkfirst=True)

def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(TABLES):
        Base.metadata.tables[table].drop(bind=bind, checkfirst=True)

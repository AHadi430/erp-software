"""payment allocations, returns, and invoice adjustments

Revision ID: 0003_payments_returns
Revises: 0002_sales_purchases
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from app.database.base import Base
import app.models  # noqa: F401

revision = "0003_payments_returns"
down_revision = "0002_sales_purchases"
branch_labels = None
depends_on = None

TABLES = ["payment_allocations", "return_documents", "return_items"]

def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    for table in ("sales_invoices", "purchase_invoices"):
        if "returned_amount" not in {column["name"] for column in inspector.get_columns(table)}:
            op.add_column(table, sa.Column("returned_amount", sa.Numeric(14, 2), nullable=False, server_default="0"))
    for table in TABLES:
        Base.metadata.tables[table].create(bind=bind, checkfirst=True)

def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(TABLES):
        Base.metadata.tables[table].drop(bind=bind, checkfirst=True)
    for table in ("sales_invoices", "purchase_invoices"):
        if "returned_amount" in {column["name"] for column in inspect(bind).get_columns(table)}:
            op.drop_column(table, "returned_amount")

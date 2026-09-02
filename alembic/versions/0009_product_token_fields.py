"""add product token settings and invoice token fields

Revision ID: 0009_product_token_fields
Revises: 0008_token_claims
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_product_token_fields"
down_revision = "0008_token_claims"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("products", sa.Column("token_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("products", sa.Column("token_value", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("sales_invoice_items", sa.Column("token_included", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("sales_invoice_items", sa.Column("token_value", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("purchase_invoice_items", sa.Column("token_included", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("purchase_invoice_items", sa.Column("token_value", sa.Numeric(14, 2), nullable=False, server_default="0"))

def downgrade() -> None:
    op.drop_column("purchase_invoice_items", "token_value")
    op.drop_column("purchase_invoice_items", "token_included")
    op.drop_column("sales_invoice_items", "token_value")
    op.drop_column("sales_invoice_items", "token_included")
    op.drop_column("products", "token_value")
    op.drop_column("products", "token_enabled")

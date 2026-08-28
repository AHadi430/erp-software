"""independent product packaging variants

Revision ID: 0007_product_packaging
Revises: 0006_governance
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_product_packaging"
down_revision = "0006_governance"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("products", sa.Column("packaging", sa.String(length=30), nullable=False, server_default="Other"))
    op.create_index("ix_products_packaging", "products", ["packaging"])

def downgrade() -> None:
    op.drop_index("ix_products_packaging", table_name="products")
    op.drop_column("products", "packaging")

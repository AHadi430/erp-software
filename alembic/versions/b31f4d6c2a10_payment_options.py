"""add JazzCash and Easypaisa payment options

Revision ID: b31f4d6c2a10
Revises: aea240d0171e
"""

from alembic import op
import sqlalchemy as sa

revision = "b31f4d6c2a10"
down_revision = "aea240d0171e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing production databases already have the paymentmethod enum.
    # Add the two digital payment choices without recreating the enum.
    op.execute("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'jazzcash'")
    op.execute("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'easypaisa'")

    op.add_column(
        "sales_invoices",
        sa.Column("payment_submethod", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "purchase_invoices",
        sa.Column("payment_submethod", sa.String(length=30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("purchase_invoices", "payment_submethod")
    op.drop_column("sales_invoices", "payment_submethod")
    # PostgreSQL does not safely support removing enum values in-place.

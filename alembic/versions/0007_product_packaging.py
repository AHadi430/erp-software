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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("products")
    }

    # Add packaging only if it does not already exist.
    if "packaging" not in columns:
        op.add_column(
            "products",
            sa.Column(
                "packaging",
                sa.String(length=30),
                nullable=False,
                server_default="Other",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("products")
    }

    # Remove packaging only if it exists.
    if "packaging" in columns:
        op.drop_column("products", "packaging")
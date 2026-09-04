"""add product token settings and invoice token fields

Revision ID: 0009_product_token_fields
Revises: 0008_token_claims
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0009_product_token_fields"
down_revision = "0008_token_claims"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    if not table_exists(table_name):
        return False

    bind = op.get_bind()
    inspector = inspect(bind)

    return any(
        column["name"] == column_name
        for column in inspector.get_columns(table_name)
    )


def add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if table_exists(table_name) and not column_exists(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    # Product token configuration
    add_column_if_missing(
        "products",
        sa.Column(
            "token_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    add_column_if_missing(
        "products",
        sa.Column(
            "token_value",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
    )

    # Only add these fields if the corresponding tables actually exist.
    add_column_if_missing(
        "sales",
        sa.Column(
            "token_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    add_column_if_missing(
        "purchases",
        sa.Column(
            "token_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    if column_exists("purchases", "token_enabled"):
        op.drop_column("purchases", "token_enabled")

    if column_exists("sales", "token_enabled"):
        op.drop_column("sales", "token_enabled")

    if column_exists("products", "token_value"):
        op.drop_column("products", "token_value")

    if column_exists("products", "token_enabled"):
        op.drop_column("products", "token_enabled")
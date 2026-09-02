"""store token claim quantities as whole numbers

Revision ID: 0009_whole_token_quantities
Revises: 0008_token_claims
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_whole_token_quantities"
down_revision = "0008_token_claims"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.alter_column(
        "token_claims",
        "quantity",
        existing_type=sa.Numeric(14, 3),
        type_=sa.Numeric(14, 0),
        existing_nullable=False,
    )

def downgrade() -> None:
    op.alter_column(
        "token_claims",
        "quantity",
        existing_type=sa.Numeric(14, 0),
        type_=sa.Numeric(14, 3),
        existing_nullable=False,
    )

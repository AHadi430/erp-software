"""business settings

Revision ID: 0004_settings
Revises: 0003_payments_returns
Create Date: 2026-08-25
"""
from alembic import op
from app.database.base import Base
import app.models  # noqa: F401

revision = "0004_settings"
down_revision = "0003_payments_returns"
branch_labels = None
depends_on = None

def upgrade() -> None:
    Base.metadata.tables["business_settings"].create(bind=op.get_bind(), checkfirst=True)

def downgrade() -> None:
    Base.metadata.tables["business_settings"].drop(bind=op.get_bind(), checkfirst=True)

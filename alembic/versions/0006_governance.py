"""audit logs and accounting periods

Revision ID: 0006_governance
Revises: 0005_expenses_cash_bank
"""
from alembic import op
import sqlalchemy as sa
from app.database.base import Base
import app.models  # noqa: F401

revision = "0006_governance"
down_revision = "0005_expenses_cash_bank"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    for table in ("accounting_periods", "audit_logs"):
        Base.metadata.tables[table].create(bind=bind, checkfirst=True)
    with op.batch_alter_table("return_documents") as batch:
        batch.add_column(sa.Column("refunded_amount", sa.Numeric(14, 2), nullable=False, server_default="0"))

def downgrade() -> None:
    bind = op.get_bind()
    for table in ("audit_logs", "accounting_periods"):
        Base.metadata.tables[table].drop(bind=bind, checkfirst=True)
    with op.batch_alter_table("return_documents") as batch:
        batch.drop_column("refunded_amount")

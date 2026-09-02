"""add painter token claims

Revision ID: 0008_token_claims
Revises: 0007_product_packaging
"""
from alembic import op
import sqlalchemy as sa
revision = "0008_token_claims"
down_revision = "0007_product_packaging"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_table("token_claims", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("claim_number", sa.String(length=50), nullable=False), sa.Column("claim_date", sa.Date(), nullable=False), sa.Column("painter_name", sa.String(length=180), nullable=False), sa.Column("painter_phone", sa.String(length=40), nullable=True), sa.Column("quantity", sa.Numeric(14, 3), nullable=False), sa.Column("token_value", sa.Numeric(14, 2), nullable=False), sa.Column("total_amount", sa.Numeric(14, 2), nullable=False), sa.Column("status", sa.Enum("PENDING", "PAID", "VOID", name="tokenclaimstatus"), nullable=False), sa.Column("payment_method", sa.String(length=30), nullable=True), sa.Column("notes", sa.Text(), nullable=True), sa.Column("journal_entry_id", sa.Uuid(), nullable=True), sa.Column("created_by_id", sa.Uuid(), nullable=True), sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]), sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_token_claims_claim_number", "token_claims", ["claim_number"], unique=True)
    op.create_index("ix_token_claims_claim_date", "token_claims", ["claim_date"])
    op.create_index("ix_token_claims_painter_name", "token_claims", ["painter_name"])
    op.create_index("ix_token_claims_status", "token_claims", ["status"])
def downgrade() -> None:
    op.drop_index("ix_token_claims_status", table_name="token_claims")
    op.drop_index("ix_token_claims_painter_name", table_name="token_claims")
    op.drop_index("ix_token_claims_claim_date", table_name="token_claims")
    op.drop_index("ix_token_claims_claim_number", table_name="token_claims")
    op.drop_table("token_claims")
    sa.Enum(name="tokenclaimstatus").drop(op.get_bind(), checkfirst=True)

"""add painter token claims

Revision ID: 0008_token_claims

Revises: 0007_product_packaging

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0008_token_claims"
down_revision = "0007_product_packaging"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # PostgreSQL enum may already exist.
    # Create it only if it does not exist.
    enum_exists = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'tokenclaimstatus'
            )
            """
        )
    ).scalar()

    if not enum_exists:
        token_claim_status = postgresql.ENUM(
            "PENDING",
            "PAID",
            "VOID",
            name="tokenclaimstatus",
        )
        token_claim_status.create(bind, checkfirst=True)

    # Create token_claims only if it does not already exist.
    if "token_claims" not in inspector.get_table_names():
        op.create_table(
            "token_claims",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column(
                "claim_number",
                sa.String(length=50),
                nullable=False,
            ),
            sa.Column(
                "claim_date",
                sa.Date(),
                nullable=False,
            ),
            sa.Column(
                "painter_name",
                sa.String(length=180),
                nullable=False,
            ),
            sa.Column(
                "painter_phone",
                sa.String(length=40),
                nullable=True,
            ),
            sa.Column(
                "quantity",
                sa.Numeric(14, 3),
                nullable=False,
            ),
            sa.Column(
                "token_value",
                sa.Numeric(14, 2),
                nullable=False,
            ),
            sa.Column(
                "total_amount",
                sa.Numeric(14, 2),
                nullable=False,
            ),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "PENDING",
                    "PAID",
                    "VOID",
                    name="tokenclaimstatus",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "payment_method",
                sa.String(length=30),
                nullable=True,
            ),
            sa.Column(
                "notes",
                sa.Text(),
                nullable=True,
            ),
            sa.Column(
                "journal_entry_id",
                sa.Uuid(),
                nullable=True,
            ),
            sa.Column(
                "created_by_id",
                sa.Uuid(),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["created_by_id"],
                ["users.id"],
            ),
            sa.ForeignKeyConstraint(
                ["journal_entry_id"],
                ["journal_entries.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )

        # Indexes matching the model/schema.
        op.create_index(
            "ix_token_claims_claim_number",
            "token_claims",
            ["claim_number"],
            unique=True,
        )
        op.create_index(
            "ix_token_claims_claim_date",
            "token_claims",
            ["claim_date"],
            unique=False,
        )
        op.create_index(
            "ix_token_claims_painter_name",
            "token_claims",
            ["painter_name"],
            unique=False,
        )
        op.create_index(
            "ix_token_claims_status",
            "token_claims",
            ["status"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "token_claims" in inspector.get_table_names():
        # Drop indexes if they exist.
        existing_indexes = {
            index["name"]
            for index in inspector.get_indexes("token_claims")
        }

        for index_name in (
            "ix_token_claims_claim_number",
            "ix_token_claims_claim_date",
            "ix_token_claims_painter_name",
            "ix_token_claims_status",
        ):
            if index_name in existing_indexes:
                op.drop_index(
                    index_name,
                    table_name="token_claims",
                )

        op.drop_table("token_claims")

    # Only remove the enum if it exists.
    enum_exists = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'tokenclaimstatus'
            )
            """
        )
    ).scalar()

    if enum_exists:
        token_claim_status = postgresql.ENUM(
            "PENDING",
            "PAID",
            "VOID",
            name="tokenclaimstatus",
        )
        token_claim_status.drop(bind, checkfirst=True)
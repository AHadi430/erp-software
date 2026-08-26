"""initial core schema

Revision ID: 0001_initial_core
Revises:
Create Date: 2026-08-24
"""
from alembic import op
from app.database.base import Base
import app.models  # noqa: F401

revision = "0001_initial_core"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())

def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())

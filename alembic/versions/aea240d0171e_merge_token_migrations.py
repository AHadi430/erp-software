"""merge token migrations

Revision ID: aea240d0171e
Revises: 0009_product_token_fields, 0009_whole_token_quantities
Create Date: 2026-09-04 16:30:16.068897
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'aea240d0171e'
down_revision: Union[str, Sequence[str], None] = ('0009_product_token_fields', '0009_whole_token_quantities')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

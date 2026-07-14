"""migrate other category to damage

Revision ID: 00263471ef5f
Revises: 98346377a60b
Create Date: 2026-07-05 15:59:59.330462

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00263471ef5f'
down_revision: Union[str, Sequence[str], None] = '98346377a60b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    import logging
    logger = logging.getLogger("alembic.runtime.migration")
    logger.warning("Migrating any evidence records with category 'other' to 'damage'.")
    op.execute("UPDATE evidence SET category = 'damage' WHERE category = 'other'")


def downgrade() -> None:
    """Downgrade schema."""
    pass

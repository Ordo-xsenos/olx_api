"""change tg_id to bigint

Revision ID: 0d757a1f5c48
Revises: 41025f4c2198
Create Date: 2026-04-26 19:46:00.744887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d757a1f5c48'
down_revision: Union[str, Sequence[str], None] = '41025f4c2198'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - tg_id already BIGINT in database."""
    # tg_id уже имеет тип BIGINT в базе данных
    # Просто обновляем модель SQLAlchemy для соответствия
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

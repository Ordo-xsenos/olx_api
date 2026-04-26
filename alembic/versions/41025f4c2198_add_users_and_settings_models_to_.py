"""add users and settings models to sqlalchemy

Revision ID: 41025f4c2198
Revises: 
Create Date: 2026-04-26 19:26:48.217055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41025f4c2198'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - tables already exist, just registering with Alembic."""
    # Tables users, settings, products, webhook_outbox already exist in database
    # This migration just registers them with Alembic version control
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # No-op since we're just registering existing tables
    pass

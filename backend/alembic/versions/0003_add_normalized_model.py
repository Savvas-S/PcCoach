"""Add normalized_model column to components table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "components",
        sa.Column("normalized_model", sa.String(200), nullable=True),
    )
    # Backfill: set normalized_model = model for existing rows
    op.execute("UPDATE components SET normalized_model = model WHERE normalized_model IS NULL")


def downgrade() -> None:
    op.drop_column("components", "normalized_model")

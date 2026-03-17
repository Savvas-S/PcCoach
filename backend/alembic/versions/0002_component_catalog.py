"""component catalog tables and builds.request column

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "components",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("brand", sa.String(100), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column(
            "specs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("in_stock", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_components_category", "components", ["category"])
    op.create_index("ix_components_in_stock", "components", ["in_stock"])

    op.create_table(
        "affiliate_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("store", sa.String(30), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("price_eur", sa.Float(), nullable=False),
        sa.Column(
            "last_checked",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["components.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("component_id", "store", name="uq_affiliate_component_store"),
    )
    op.create_index("ix_affiliate_links_component_id", "affiliate_links", ["component_id"])

    # Add request column to builds
    op.add_column(
        "builds",
        sa.Column("request", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("builds", "request")
    op.drop_table("affiliate_links")
    op.drop_table("components")

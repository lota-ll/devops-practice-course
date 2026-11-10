"""Товари мереж та знімки цін

Revision ID: 0001
Revises:
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chain", sa.String(20), nullable=False),
        sa.Column("chain_product_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("pack", sa.String(40)),
        sa.Column("qty", sa.Float()),
        sa.Column("qty_base", sa.String(4)),
        sa.Column("ean", sa.String(14)),
        sa.Column("ean_source", sa.String(10)),
        sa.Column("ean_checked_at", sa.DateTime(timezone=True)),
        sa.Column("slug", sa.String(300)),
        sa.Column("url", sa.String(500)),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chain", "chain_product_id", name="uq_products_chain_id"),
    )
    op.create_index("ix_products_ean", "products", ["ean"])

    op.create_table(
        "price_snapshots",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("old_price", sa.Numeric(10, 2)),
        sa.Column("promo", sa.String(200)),
        sa.Column("in_stock", sa.Boolean()),
        sa.Column("stock_qty", sa.Float()),
    )
    op.create_index("ix_snapshots_product_time", "price_snapshots", ["product_id", "observed_at"])


def downgrade() -> None:
    op.drop_index("ix_snapshots_product_time", table_name="price_snapshots")
    op.drop_table("price_snapshots")
    op.drop_index("ix_products_ean", table_name="products")
    op.drop_table("products")

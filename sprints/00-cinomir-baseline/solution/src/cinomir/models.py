from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow

# BIGINT у PostgreSQL, INTEGER у SQLite (інакше SQLite не робить autoincrement)
BigId = BigInteger().with_variant(Integer(), "sqlite")


class Product(Base):
    """Товар конкретної мережі. Один і той самий фізичний товар у 3 мережах = 3 рядки."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chain: Mapped[str] = mapped_column(String(20))
    chain_product_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(300))
    pack: Mapped[str | None] = mapped_column(String(40), default=None)
    qty: Mapped[float | None] = mapped_column(Float, default=None)  # г або мл
    qty_base: Mapped[str | None] = mapped_column(String(4), default=None)  # "кг" | "л"
    ean: Mapped[str | None] = mapped_column(String(14), default=None, index=True)
    ean_source: Mapped[str | None] = mapped_column(String(10), default=None)
    # Коли воркер востаннє шукав штрихкод (щоб не питати мережу щоразу, якщо його немає)
    ean_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    slug: Mapped[str | None] = mapped_column(String(300), default=None)
    url: Mapped[str | None] = mapped_column(String(500), default=None)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    snapshots: Mapped[list[PriceSnapshot]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (UniqueConstraint("chain", "chain_product_id", name="uq_products_chain_id"),)


class PriceSnapshot(Base):
    """Ціна і наявність у момент спостереження. З цього росте історія цін."""

    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    old_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=None)
    promo: Mapped[str | None] = mapped_column(String(200), default=None)
    in_stock: Mapped[bool | None] = mapped_column(Boolean, default=None)
    stock_qty: Mapped[float | None] = mapped_column(Float, default=None)

    product: Mapped[Product] = relationship(back_populates="snapshots")

    __table_args__ = (Index("ix_snapshots_product_time", "product_id", "observed_at"),)

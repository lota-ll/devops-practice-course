from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SortKey = Literal["price", "unit"]


class OfferOut(BaseModel):
    product_id: int | None
    chain: str
    chain_title: str
    title: str
    price: float
    old_price: float | None
    pack: str | None
    unit_price: float | None  # грн за кг/л: лише для сортування «вигідніше за вагою»
    unit_base: str | None
    in_stock: bool | None
    stock_qty: float | None
    promo: str | None
    ean: str | None
    url: str | None


class ChainStatus(BaseModel):
    chain: str
    title: str
    ok: bool
    received: int = 0  # скільки віддала мережа
    relevant: int = 0  # скільки лишилось після фільтра релевантності
    latency_ms: int | None = None
    error: str | None = None


class GroupItem(BaseModel):
    chain_title: str
    price: float
    in_stock: bool | None
    pack: str | None


class MatchGroup(BaseModel):
    """Той самий товар у кількох мережах (за штрихкодом або спільним id Сільпо/Фори)."""

    title: str
    items: list[GroupItem]
    cheapest_in_stock: str | None
    saving: float | None  # різниця між найдорожчою і найдешевшою наявною


class SearchSnapshot(BaseModel):
    """Повний результат — саме він лежить у кеші."""

    search_id: str
    query: str
    created_at: datetime
    chains: list[ChainStatus]
    offers: list[OfferOut]
    groups: list[MatchGroup]


class SearchPage(BaseModel):
    search_id: str
    query: str
    created_at: datetime
    cached: bool
    chains: list[ChainStatus]
    sort: SortKey
    page: int
    pages: int
    page_size: int
    total: int  # з урахуванням фільтра наявності
    hidden_out_of_stock: int
    offers: list[OfferOut]
    groups: list[MatchGroup]


class SnapshotOut(BaseModel):
    observed_at: datetime
    price: float
    old_price: float | None
    promo: str | None
    in_stock: bool | None

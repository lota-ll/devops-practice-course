"""Спільний інтерфейс адаптерів мереж.

Кожна мережа — окремий адаптер з однаковим контрактом. Додати METRO (той самий zakaz.ua)
чи АТБ у майбутньому = написати ще один клас, не чіпаючи сервіс пошуку.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx


@dataclass
class ChainOffer:
    """Сира пропозиція мережі, вже приведена до спільного вигляду."""

    chain: str
    chain_product_id: str
    title: str
    price: float
    old_price: float | None = None
    pack_raw: str | None = None  # як написано в мережі: "160г", "2*80г/уп"
    ean: str | None = None
    ean_source: str | None = None
    promo: str | None = None
    in_stock: bool | None = None  # None = мережа не повідомляє
    stock_qty: float | None = None
    slug: str | None = None
    url: str | None = None
    weighted: bool = False  # ціна вже за кг (вагові товари)
    extra: dict = field(default_factory=dict)


class BlockedError(RuntimeError):
    """Мережа відповіла сторінкою захисту від ботів."""


class ChainError(RuntimeError):
    """Мережа відповіла, але не тим, що ми очікували (API змінився?)."""


def check_response(r: httpx.Response) -> None:
    is_cf = "cf-ray" in r.headers or "cloudflare" in r.headers.get("server", "").lower()
    if r.status_code in (403, 429, 503) and is_cf:
        raise BlockedError(f"Cloudflare HTTP {r.status_code}")
    r.raise_for_status()


def to_float(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class Chain(ABC):
    name: str  # машинне ім'я: "silpo"
    title: str  # для людей: "Сільпо"

    @abstractmethod
    async def search(self, client: httpx.AsyncClient, query: str, limit: int) -> list[ChainOffer]:
        """Пошук товарів у мережі. Кидає BlockedError / ChainError / httpx.HTTPError."""

    async def fetch_barcodes(self, client: httpx.AsyncClient, offer_slug: str) -> list[str]:
        """Штрихкоди товару, якщо мережа не віддає їх у пошуку. За замовчуванням — нічого."""
        return []

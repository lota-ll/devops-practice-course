"""Novus через zakaz.ua: GET {api}/stores/{store}/products/search/?q=…

На zakaz.ua працюють й інші мережі (напр. METRO) — той самий адаптер з іншим store id.
"""

from __future__ import annotations

import httpx

from ..matching import pick_public_ean
from .base import Chain, ChainError, ChainOffer, check_response


def parse_item(item: dict) -> ChainOffer:
    # zakaz.ua віддає ціни в копійках
    discount = item.get("discount") or {}
    active = bool(discount.get("status"))
    old = discount.get("old_price") if active else None
    promo = None
    if active:
        promo = f"-{discount['value']}%" if discount.get("value") else "знижка"
        if discount.get("due_date"):
            promo += f" до {str(discount['due_date'])[:10]}"
    pack = None
    if item.get("weight"):
        pack = f"{float(item['weight']):g}г"
    elif item.get("volume"):
        pack = f"{float(item['volume']):g}мл"
    ean, ean_source = pick_public_ean([item["ean"]] if item.get("ean") else [])
    in_stock = item.get("in_stock")
    return ChainOffer(
        chain="novus",
        chain_product_id=str(item.get("sku") or item.get("ean")),
        title=item["title"],
        price=item["price"] / 100,
        old_price=old / 100 if old else None,
        pack_raw=pack,
        ean=ean,
        ean_source=ean_source,
        promo=promo,
        # залишку zakaz.ua не віддає, лише прапорець (параметр in_stock у запиті не фільтрує)
        in_stock=in_stock if isinstance(in_stock, bool) else None,
        url=item.get("web_url"),
        weighted=item.get("unit") == "kg",
    )


class Novus(Chain):
    name, title = "novus", "Novus"

    def __init__(self, api: str, store: int) -> None:
        self.url = f"{api.rstrip('/')}/stores/{store}/products/search/"

    async def search(self, client: httpx.AsyncClient, query: str, limit: int) -> list[ChainOffer]:
        r = await client.get(
            self.url, params={"q": query, "page": 1}, headers={"Accept-Language": "uk"}
        )
        check_response(r)
        data = r.json()
        if "results" not in data:
            raise ChainError(f"no 'results' in response, keys={list(data)[:10]}")
        return [parse_item(i) for i in data["results"][:limit]]

"""Сільпо: GET {api}/v1/uk/branches/{branch}/products?search=… (внутрішній API сайту)."""

from __future__ import annotations

import httpx

from .base import Chain, ChainError, ChainOffer, check_response, to_float


def parse_item(item: dict) -> ChainOffer:
    promos = [p.get("id") for p in item.get("promotions") or [] if p.get("id")]
    if item.get("specialPrices"):
        promos.append("special_price")
    stock = to_float(item.get("stock"))
    return ChainOffer(
        chain="silpo",
        # externalProductId спільний із Форою (обидві мережі — Fozzy Group)
        chain_product_id=str(item.get("externalProductId") or item["id"]),
        title=item["title"],
        price=float(item["price"]),
        old_price=to_float(item.get("oldPrice")),
        pack_raw=item.get("displayRatio"),
        promo=", ".join(promos) or None,
        stock_qty=stock,
        in_stock=(stock > 0) if stock is not None else None,
        slug=item.get("slug"),
        url=f"https://silpo.ua/product/{item['slug']}" if item.get("slug") else None,
        weighted=bool(item.get("weighted")) and "кг" in (item.get("ratio") or ""),
    )


class Silpo(Chain):
    name, title = "silpo", "Сільпо"

    def __init__(self, api: str, branch: str) -> None:
        self.base = f"{api.rstrip('/')}/v1/uk/branches/{branch}/products"

    async def search(self, client: httpx.AsyncClient, query: str, limit: int) -> list[ChainOffer]:
        params = {
            "limit": limit,
            "offset": 0,
            "deliveryType": "DeliveryHome",
            "includeChildCategories": "true",
            "sortBy": "productsList",
            "sortDirection": "desc",
            "inStock": "true",
            "search": query,
        }
        r = await client.get(self.base, params=params)
        check_response(r)
        data = r.json()
        if "items" not in data:
            raise ChainError(f"no 'items' in response, keys={list(data)[:10]}")
        return [parse_item(i) for i in data["items"]]

    async def fetch_barcodes(self, client: httpx.AsyncClient, offer_slug: str) -> list[str]:
        r = await client.get(f"{self.base}/{offer_slug}")
        check_response(r)
        return [str(c) for c in r.json().get("barcodes") or []]

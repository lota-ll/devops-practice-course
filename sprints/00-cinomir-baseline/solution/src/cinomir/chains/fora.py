"""Фора: POST {api}/api/2.0/exec/EcomCatalogGlobal, метод GetSimpleCatalogItems."""

from __future__ import annotations

import httpx

from .base import Chain, ChainError, ChainOffer, check_response, to_float


def parse_item(item: dict) -> ChainOffer:
    promo = item.get("promoTitle")
    if item.get("priceStopAfter"):
        promo = f"{promo or 'акція'} до {str(item['priceStopAfter'])[:10]}"
    # quantity == 0 -> на сайті «немає в наявності» (перевірено на артикулі 942879)
    stock = to_float(item.get("quantity", item.get("calcStoreQuantity")))
    return ChainOffer(
        chain="fora",
        chain_product_id=str(item["id"]),
        title=item["name"],
        price=float(item["price"]),
        old_price=to_float(item.get("oldPrice")),
        pack_raw=item.get("unit"),
        promo=promo,
        stock_qty=stock,
        in_stock=(stock > 0) if stock is not None else None,
        slug=item.get("slug"),
        weighted=bool(item.get("isWeightedProduct")),
    )


class Fora(Chain):
    name, title = "fora", "Фора"

    def __init__(self, api: str, filial: int) -> None:
        self.url = f"{api.rstrip('/')}/api/2.0/exec/EcomCatalogGlobal"
        self.filial = filial

    async def search(self, client: httpx.AsyncClient, query: str, limit: int) -> list[ChainOffer]:
        body = {
            "method": "GetSimpleCatalogItems",
            "data": {
                "merchantId": 2,
                "deliveryType": 2,
                "filialId": self.filial,
                "From": 1,
                "To": limit,
                "slug": "all",
                "businessId": 1,
                "customFilter": query,
                "RangeFilters": {},
                "MultiFilters": {},
                "UniversalFilters": [],
                "CategoryFilter": [],
                "Promos": [],
            },
        }
        r = await client.post(self.url, json=body)
        check_response(r)
        data = r.json()
        if data.get("EComError") and not data.get("items"):
            raise ChainError(f"EComError: {str(data['EComError'])[:200]}")
        return [parse_item(i) for i in data.get("items") or []]

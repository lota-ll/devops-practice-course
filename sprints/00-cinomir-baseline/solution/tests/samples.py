"""Зразки відповідей мереж. Структури повторюють побачене в браузері 10.11.2026.

Тести ніколи не ходять у справжні мережі: усе через httpx.MockTransport.
"""

from __future__ import annotations

import json

import httpx

SILPO_ITEM = {
    "id": "1edb04e3-a722-6680-856e-432881cbcc65",
    "title": "Тунець Fish Line у власному соці",
    "price": 144,
    "oldPrice": None,
    "ratio": "шт",
    "externalProductId": 919622,
    "promotions": [],
    "specialPrices": [],
    "slug": "tunets-fish-line-u-vlasnomu-sotsi-919622",
    "displayRatio": "160г",
    "weighted": False,
    "stock": 6,
}
SILPO_PROMO_ITEM = {
    **SILPO_ITEM,
    "id": "1edb04e3-0000-0000-0000-000000000001",
    "title": "Тунець Iberica цілий у власному соку",
    "price": 73.99,
    "oldPrice": 99,
    "externalProductId": 921000,
    "slug": "tunets-iberica-921000",
    "displayRatio": "150г",
    "promotions": [{"id": "only_online", "type": "promo"}],
}
SILPO_CAT_FOOD = {
    **SILPO_ITEM,
    "id": "1edb04e3-0000-0000-0000-000000000002",
    "title": "Вологий корм Whiskas з тунцем в желе",
    "price": 21.5,
    "externalProductId": 555001,
    "slug": "korm-whiskas-555001",
    "displayRatio": "85г",
}
FORA_ITEM = {
    "id": 919622,  # той самий id, що externalProductId у Сільпо
    "name": "Тунець Fish Line у власному соці",
    "unit": "160г",
    "price": 109,
    "oldPrice": None,
    "promoTitle": None,
    "priceStopAfter": None,
    "isWeightedProduct": False,
    "slug": "tunets-fish-line-u-vlasnomu-sotsi-919622",
    "quantity": 0,  # у Форі немає в наявності
}
FORA_PROMO_ITEM = {
    **FORA_ITEM,
    "id": 1014853,
    "name": "Тунець Oceano шматочки у власному соку",
    "unit": "185г",
    "price": 74.9,
    "oldPrice": 119,
    "promoTitle": "Лайк ціна",
    "priceStopAfter": "2026-11-16T23:59:59",
    "slug": "tunets-oceano-1014853",
    "quantity": 22,
}
NOVUS_ITEM = {
    "ean": "04820235630591",  # zakaz.ua віддає GTIN-14 з провідним нулем
    "sku": "1234567",
    "title": "Тунець Fish Line у власному соці 160г",
    "price": 9899,  # копійки
    "discount": {"status": True, "value": 15, "old_price": 11650, "due_date": "2026-11-12"},
    "unit": "pcs",
    "weight": 160,
    "volume": None,
    "web_url": "https://novus.zakaz.ua/uk/products/4820235630591--fish-line/",
    "in_stock": True,
}
NOVUS_OOS_ITEM = {
    "ean": "8410000000009",
    "sku": "7654321",
    "title": "Тунець Calvo у власному соку 160г",
    "price": 16900,
    "discount": {"status": False},
    "unit": "pcs",
    "weight": 160,
    "web_url": None,
    "in_stock": False,
}
NOVUS_BIG_CAN = {
    "ean": "4820000000000",
    "sku": "1111111",
    "title": "Тунець Своя марка у власному соку 400г",
    "price": 15900,
    "discount": {"status": False},
    "unit": "pcs",
    "weight": 400,
    "web_url": None,
    "in_stock": True,
}

# Картка Сільпо: внутрішній код 02x першим — має бути пропущений
SILPO_BARCODES = {SILPO_ITEM["slug"]: ["0250000000009", "4820235630591"]}


class FakeChains:
    """Обробник MockTransport + лічильник запитів і перемикачі збоїв."""

    def __init__(self) -> None:
        self.calls: dict[str, int] = {"silpo": 0, "fora": 0, "novus": 0, "silpo_card": 0}
        self.fail: set[str] = set()
        self.cloudflare: set[str] = set()
        self.sent_queries: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        host, path = request.url.host, request.url.path
        chain = {
            "sf-ecom-api.silpo.ua": "silpo",
            "api.catalog.ecom.fora.ua": "fora",
            "stores-api.zakaz.ua": "novus",
        }.get(host)
        if chain is None:
            return httpx.Response(404)
        if chain in self.cloudflare:
            return httpx.Response(
                403, headers={"server": "cloudflare", "cf-ray": "x"}, text="Just a moment..."
            )
        if chain in self.fail:
            return httpx.Response(500, text="boom")

        if chain == "silpo":
            if path.endswith("/products"):
                self.calls["silpo"] += 1
                self.sent_queries.append(request.url.params["search"])
                items = [SILPO_ITEM, SILPO_PROMO_ITEM, SILPO_CAT_FOOD]
                return httpx.Response(200, json={"total": len(items), "items": items})
            self.calls["silpo_card"] += 1
            slug = path.rsplit("/", 1)[-1]
            return httpx.Response(200, json={"barcodes": SILPO_BARCODES.get(slug, [])})
        if chain == "fora":
            self.calls["fora"] += 1
            body = json.loads(request.content)
            self.sent_queries.append(body["data"]["customFilter"])
            return httpx.Response(200, json={"items": [FORA_ITEM, FORA_PROMO_ITEM]})
        self.calls["novus"] += 1
        self.sent_queries.append(request.url.params["q"])
        return httpx.Response(
            200, json={"count": 3, "results": [NOVUS_ITEM, NOVUS_OOS_ITEM, NOVUS_BIG_CAN]}
        )

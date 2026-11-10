from __future__ import annotations

import pytest
from sqlalchemy import func, select

from cinomir.models import PriceSnapshot, Product
from cinomir.search import ENRICH_PENDING, paginate, search_id_for

pytestmark = pytest.mark.anyio
Q = "тунець у власному соку"


async def test_search_filters_persists_and_groups(service, fake_chains, sessions, settings):
    snap, cached = await service.search(Q)
    assert cached is False
    # у мережі йде лише головне слово, точність — наш фільтр
    assert set(fake_chains.sent_queries) == {"тунець"}
    titles = [o.title for o in snap.offers]
    assert not any("Whiskas" in t for t in titles)
    assert {c.chain: (c.ok, c.received, c.relevant) for c in snap.chains} == {
        "silpo": (True, 3, 2),
        "fora": (True, 2, 2),
        "novus": (True, 3, 3),
    }

    async with sessions() as s:
        assert await s.scalar(select(func.count()).select_from(Product)) == 7
        assert await s.scalar(select(func.count()).select_from(PriceSnapshot)) == 7

    # Fish Line: Сільпо+Фора (спільний id) і Novus (за EAN після воркера — поки ні)
    fish = next(g for g in snap.groups if "Fish Line" in g.title)
    assert {i.chain_title for i in fish.items} == {"Сільпо", "Фора"}
    # Фора дешевша, але її немає -> економії між наявними немає
    assert fish.cheapest_in_stock == "Сільпо" and fish.saving is None
    assert snap.search_id == search_id_for(Q, settings)


async def test_second_search_is_served_from_cache(service, fake_chains):
    await service.search(Q)
    snap, cached = await service.search("  Тунець у ВЛАСНОМУ соку ")
    assert cached is True
    assert fake_chains.calls["silpo"] == 1 and fake_chains.calls["novus"] == 1
    assert await service.get_cached(snap.search_id) is not None


async def test_silpo_products_without_ean_are_queued_once(service, redis, settings):
    await service.search(Q)
    queued = await redis.lrange(settings.enrich_queue, 0, -1)
    assert len(queued) == 2  # два релевантні товари Сільпо без штрихкоду
    await redis.delete(service.settings.enrich_queue)
    await redis.delete("cinomir:search:" + search_id_for(Q, settings))
    await service.search(Q)  # повторний пошук без кешу
    assert await redis.llen(settings.enrich_queue) == 0  # SADD не пустив дублікати
    assert await redis.scard(ENRICH_PENDING) == 2


async def test_one_chain_down_others_still_answer(service, fake_chains, redis):
    fake_chains.fail.add("fora")
    fake_chains.cloudflare.add("novus")
    snap, _ = await service.search(Q)
    st = {c.chain: c for c in snap.chains}
    assert st["silpo"].ok and len(snap.offers) == 2
    assert st["fora"].error == "помилка: HTTPStatusError"
    assert st["novus"].error.startswith("заблоковано")


async def test_all_chains_down_is_not_cached(service, fake_chains, redis):
    fake_chains.fail.update({"silpo", "fora", "novus"})
    snap, _ = await service.search(Q)
    assert snap.offers == []
    assert await service.get_cached(snap.search_id) is None


async def test_paginate_hides_out_of_stock_and_sorts(service):
    snap, _ = await service.search(Q)
    page = paginate(snap, cached=False, sort="price", page_size=3)
    assert page.hidden_out_of_stock == 2  # Fish Line у Форі та Calvo в Novus
    assert page.total == 5 and page.pages == 2
    prices = [o.price for o in page.offers]
    assert prices == sorted(prices) and prices[0] == 73.99

    by_weight = paginate(snap, cached=False, sort="unit", page_size=10)
    # 400 г за 159 грн = 397.5 грн/кг — найвигідніше за вагою, хоча не найдешевше
    assert by_weight.offers[0].title.startswith("Тунець Своя марка")
    assert by_weight.offers[0].pack == "400 г"

    everything = paginate(snap, cached=False, include_out_of_stock=True, page_size=50)
    assert everything.total == 7 and everything.hidden_out_of_stock == 0


async def test_paginate_clamps_page(service):
    snap, _ = await service.search(Q)
    assert paginate(snap, cached=True, page=99, page_size=3).page == 2

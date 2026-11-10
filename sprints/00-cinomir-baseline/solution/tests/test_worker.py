from __future__ import annotations

import pytest
from sqlalchemy import select

from cinomir.chains import build_chains
from cinomir.models import Product
from cinomir.search import ENRICH_PENDING
from cinomir.worker import EnrichWorker

pytestmark = pytest.mark.anyio
Q = "тунець у власному соку"


@pytest.fixture
def worker(settings, http, redis, sessions):
    return EnrichWorker(settings, build_chains(settings), http, redis, sessions, delay_seconds=0)


async def _product(sessions, chain, title_part):
    async with sessions() as s:
        rows = await s.scalars(select(Product).where(Product.chain == chain))
        return next(p for p in rows if title_part in p.title)


async def test_barcode_found_and_shared_with_fora(service, worker, sessions, redis):
    await service.search(Q)
    silpo = await _product(sessions, "silpo", "Fish Line")

    assert await worker.process(silpo.id) == "found"

    silpo = await _product(sessions, "silpo", "Fish Line")
    fora = await _product(sessions, "fora", "Fish Line")
    # внутрішній 025… пропущено, взято публічний EAN; Фора отримала його за спільним id
    assert (silpo.ean, silpo.ean_source) == ("4820235630591", "retail")
    assert fora.ean == "4820235630591"
    assert not await redis.sismember(ENRICH_PENDING, str(silpo.id))


async def test_after_enrichment_novus_joins_the_group(service, worker, sessions, redis, settings):
    await service.search(Q)
    silpo = await _product(sessions, "silpo", "Fish Line")
    await worker.process(silpo.id)
    await redis.flushall()  # скинути кеш пошуку

    snap, _ = await service.search(Q)
    fish = next(g for g in snap.groups if "Fish Line" in g.title)
    assert {i.chain_title for i in fish.items} == {"Сільпо", "Фора", "Novus"}
    # наявні: Novus 98.99 і Сільпо 144 -> дешевше в Novus на 45.01
    assert fish.cheapest_in_stock == "Novus" and fish.saving == pytest.approx(45.01)


async def test_no_public_barcode_and_skips(service, worker, sessions):
    await service.search(Q)
    iberica = await _product(sessions, "silpo", "Iberica")
    assert await worker.process(iberica.id) == "none"
    assert await worker.process(999_999) == "skipped"
    novus = await _product(sessions, "novus", "Fish Line")
    assert await worker.process(novus.id) == "skipped"  # штрихкод уже є


async def test_product_without_barcode_is_not_requeued_every_search(
    service, worker, sessions, redis, settings
):
    await service.search(Q)
    iberica = await _product(sessions, "silpo", "Iberica")
    await worker.process(iberica.id)
    await redis.flushall()

    await service.search(Q)
    queued = await redis.lrange(settings.enrich_queue, 0, -1)
    assert str(iberica.id) not in queued  # перевіряли нещодавно — не питаємо знову

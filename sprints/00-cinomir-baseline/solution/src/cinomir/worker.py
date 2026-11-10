"""Воркер: дозбирає штрихкоди товарів Сільпо у фоні.

Пошук Сільпо не віддає штрихкод — лише картка товару (окремий запит на кожен).
Робити це під час пошуку = змушувати користувача чекати 20+ запитів. Тому:
api кладе id товару в чергу -> worker повільно і ввічливо дозбирує -> наступні пошуки
вже зіставляють товари Сільпо з Novus за штрихкодом.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal

import httpx
import redis.asyncio as aioredis
from prometheus_client import start_http_server
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .chains import BlockedError, Chain, build_chains
from .config import Settings, get_settings
from .db import dispose, session_factory, utcnow
from .logs import configure_logging, get_logger
from .matching import pick_public_ean
from .metrics import ENRICH
from .models import Product
from .search import ENRICH_PENDING

log = get_logger("cinomir.worker")


class EnrichWorker:
    def __init__(
        self,
        settings: Settings,
        chains: dict[str, Chain],
        http: httpx.AsyncClient,
        redis: aioredis.Redis,
        sessions: async_sessionmaker[AsyncSession],
        delay_seconds: float = 0.5,
    ) -> None:
        self.settings = settings
        self.chains = chains
        self.http = http
        self.redis = redis
        self.sessions = sessions
        self.delay = delay_seconds

    async def process(self, product_id: int) -> str:
        """Обробити одну задачу. Повертає результат: found | none | skipped."""
        try:
            async with self.sessions() as session:
                product = await session.get(Product, product_id)
                if product is None or product.ean or not product.slug:
                    ENRICH.labels("skipped").inc()
                    return "skipped"
                chain = self.chains.get(product.chain)
                if chain is None:
                    ENRICH.labels("skipped").inc()
                    return "skipped"

                codes = await chain.fetch_barcodes(self.http, product.slug)
                ean, source = pick_public_ean(codes)
                product.ean_checked_at = utcnow()
                if ean is None:
                    await session.commit()  # запам'ятати перевірку, щоб не питати щоразу
                    ENRICH.labels("none").inc()
                    log.info("no public barcode", extra={"product_id": product_id, "codes": codes})
                    return "none"

                product.ean, product.ean_source = ean, source
                if product.chain == "silpo":
                    # Фора — та сама Fozzy Group, той самий id товару -> той самий штрихкод
                    await session.execute(
                        update(Product)
                        .where(
                            Product.chain == "fora",
                            Product.chain_product_id == product.chain_product_id,
                            Product.ean.is_(None),
                        )
                        .values(ean=ean, ean_source=source)
                    )
                await session.commit()
                ENRICH.labels("found").inc()
                log.info(
                    "barcode found",
                    extra={"product_id": product_id, "ean": ean, "source": source},
                )
                return "found"
        finally:
            await self.redis.srem(ENRICH_PENDING, product_id)

    async def run(self, stop: asyncio.Event) -> None:
        log.info("worker started", extra={"queue": self.settings.enrich_queue})
        while not stop.is_set():
            try:
                # Короткий timeout BRPOP = швидка реакція на SIGTERM
                item = await self.redis.brpop([self.settings.enrich_queue], timeout=2)
                if item is None:
                    continue
                await self.process(int(item[1]))
                await asyncio.sleep(self.delay)  # ввічливість до мережі
            except BlockedError as exc:
                ENRICH.labels("error").inc()
                log.warning("chain blocked, backing off", extra={"error": str(exc)})
                await _wait(stop, 60)
            except Exception:
                ENRICH.labels("error").inc()
                log.exception("job failed")
                await _wait(stop, 1)  # не крутити гарячий цикл, якщо Redis/БД лежать
        log.info("worker stopped")


async def _wait(stop: asyncio.Event, seconds: float) -> None:
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=seconds)


async def amain() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    start_http_server(settings.worker_metrics_port)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    async with httpx.AsyncClient(
        headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
        timeout=settings.chain_timeout_seconds,
    ) as http:
        r = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            worker = EnrichWorker(settings, build_chains(settings), http, r, session_factory())
            await worker.run(stop)
        finally:
            await r.aclose()
            await dispose()


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()

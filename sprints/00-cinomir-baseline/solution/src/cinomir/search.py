"""Сервіс пошуку: паралельний запит до мереж, фільтр, збереження цін, кеш, зіставлення."""

from __future__ import annotations

import asyncio
import hashlib
import math
import time
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

import httpx
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .chains import BlockedError, Chain, ChainError, ChainOffer
from .config import Settings
from .db import utcnow
from .logs import get_logger
from .matching import format_pack, main_word, parse_quantity, relevance
from .metrics import CHAIN_LAST_ITEMS, CHAIN_LATENCY, CHAIN_REQUESTS, SEARCHES
from .models import PriceSnapshot, Product
from .schemas import (
    ChainStatus,
    GroupItem,
    MatchGroup,
    OfferOut,
    SearchPage,
    SearchSnapshot,
    SortKey,
)

log = get_logger("cinomir.search")

MIN_RELEVANCE = 0.6
CACHE_PREFIX = "cinomir:search:"
ENRICH_PENDING = "cinomir:enrich:pending"


def _aware(dt: datetime) -> datetime:
    """SQLite повертає naive datetime навіть для timezone=True — вважаємо його UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def normalize_query(query: str) -> str:
    return " ".join(query.lower().split())


def search_id_for(query: str, settings: Settings) -> str:
    """Детермінований id: той самий запит з тими самими магазинами = той самий кеш."""
    scope = (
        f"{normalize_query(query)}|{','.join(settings.enabled_chains)}|"
        f"{settings.silpo_branch}|{settings.fora_filial}|{settings.novus_store}"
    )
    return hashlib.sha1(scope.encode()).hexdigest()[:16]


class SearchService:
    def __init__(
        self,
        settings: Settings,
        chains: dict[str, Chain],
        http: httpx.AsyncClient,
        redis: aioredis.Redis,
        sessions: async_sessionmaker[AsyncSession],
    ) -> None:
        self.settings = settings
        self.chains = chains
        self.http = http
        self.redis = redis
        self.sessions = sessions
        # Не більше N одночасних запитів до однієї мережі з цього процесу
        self._limits = {name: asyncio.Semaphore(settings.chain_concurrency) for name in chains}

    # ------------------------------------------------------------ публічне API

    async def search(self, query: str) -> tuple[SearchSnapshot, bool]:
        """(результат, чи з кешу)."""
        sid = search_id_for(query, self.settings)
        cached = await self.get_cached(sid)
        if cached is not None:
            SEARCHES.labels("hit").inc()
            return cached, True

        SEARCHES.labels("miss").inc()
        word = main_word(query)
        fetched = await asyncio.gather(*(self._fetch(c, word) for c in self.chains.values()))

        statuses: list[ChainStatus] = []
        relevant: list[ChainOffer] = []
        for status, offers in fetched:
            keep = [o for o in offers if relevance(query, o.title) >= MIN_RELEVANCE]
            status.relevant = len(keep)
            statuses.append(status)
            relevant.extend(keep)

        products = await self._persist(relevant)
        await self._enqueue_enrichment(products.values())
        out = [self._to_out(o, products.get((o.chain, o.chain_product_id))) for o in relevant]

        snapshot = SearchSnapshot(
            search_id=sid,
            query=query.strip(),
            created_at=utcnow(),
            chains=statuses,
            offers=out,
            groups=build_groups(out, relevant),
        )
        # Не кешуємо результат, де впали всі мережі: наступний запит має спробувати знову
        if any(s.ok for s in statuses):
            await self.redis.set(
                CACHE_PREFIX + sid, snapshot.model_dump_json(), ex=self.settings.cache_ttl_seconds
            )
        log.info(
            "search",
            extra={
                "query": query,
                "sent_to_chains": word,
                "chains": {s.chain: (s.received, s.relevant, s.error) for s in statuses},
            },
        )
        return snapshot, False

    async def get_cached(self, search_id: str) -> SearchSnapshot | None:
        raw = await self.redis.get(CACHE_PREFIX + search_id)
        return SearchSnapshot.model_validate_json(raw) if raw else None

    # ------------------------------------------------------------ мережі

    async def _fetch(self, chain: Chain, word: str) -> tuple[ChainStatus, list[ChainOffer]]:
        status = ChainStatus(chain=chain.name, title=chain.title, ok=False)
        started = time.perf_counter()
        outcome = "error"
        try:
            async with self._limits[chain.name]:
                offers = await asyncio.wait_for(
                    chain.search(self.http, word, self.settings.search_limit_per_chain),
                    timeout=self.settings.chain_timeout_seconds,
                )
            status.ok, status.received, outcome = True, len(offers), "ok"
            CHAIN_LAST_ITEMS.labels(chain.name).set(len(offers))
            return status, offers
        except TimeoutError:
            outcome, status.error = "timeout", "не відповіла вчасно"
        except BlockedError as exc:
            outcome, status.error = "blocked", f"заблоковано ({exc})"
        except (httpx.HTTPError, ChainError, ValueError, KeyError) as exc:
            status.error = f"помилка: {type(exc).__name__}"
            log.warning("chain failed", extra={"chain": chain.name, "error": repr(exc)[:300]})
        finally:
            elapsed = time.perf_counter() - started
            status.latency_ms = round(elapsed * 1000)
            CHAIN_LATENCY.labels(chain.name).observe(elapsed)
            CHAIN_REQUESTS.labels(chain.name, outcome).inc()
        return status, []

    # ------------------------------------------------------------ збереження

    async def _persist(self, offers: list[ChainOffer]) -> dict[tuple[str, str], Product]:
        """Upsert товарів + знімок ціни на кожну пропозицію. Повертає товари з БД (з EAN)."""
        if not offers:
            return {}
        keys = {(o.chain, o.chain_product_id) for o in offers}
        now = utcnow()
        async with self.sessions() as session:
            existing = await session.scalars(
                select(Product).where(Product.chain_product_id.in_({k[1] for k in keys}))
            )
            products = {
                (p.chain, p.chain_product_id): p
                for p in existing
                if (p.chain, p.chain_product_id) in keys
            }
            for o in offers:
                p = products.get((o.chain, o.chain_product_id))
                if p is None:
                    p = Product(chain=o.chain, chain_product_id=o.chain_product_id, first_seen=now)
                    session.add(p)
                    products[(o.chain, o.chain_product_id)] = p
                qty = parse_quantity(o.pack_raw, o.title)
                p.title, p.pack, p.slug, p.url, p.last_seen = (
                    o.title,
                    o.pack_raw,
                    o.slug,
                    o.url,
                    now,
                )
                p.qty, p.qty_base = qty if qty else (None, None)
                if o.ean and not p.ean:
                    p.ean, p.ean_source = o.ean, o.ean_source
            await session.flush()  # нові товари отримують id
            session.add_all(
                PriceSnapshot(
                    product_id=products[(o.chain, o.chain_product_id)].id,
                    observed_at=now,
                    price=o.price,
                    old_price=o.old_price,
                    promo=o.promo,
                    in_stock=o.in_stock,
                    stock_qty=o.stock_qty,
                )
                for o in offers
            )
            await session.commit()
        return products

    async def _enqueue_enrichment(self, products: Iterable[Product]) -> None:
        """Штрихкоди Сільпо — окремий запит на товар. Робимо у фоні (worker), не тут."""
        recheck_after = utcnow() - timedelta(days=self.settings.enrich_recheck_days)
        todo = [
            p.id
            for p in products
            if p.chain == "silpo"
            and not p.ean
            and p.slug
            and (p.ean_checked_at is None or _aware(p.ean_checked_at) < recheck_after)
        ]
        queued = 0
        for pid in todo[: self.settings.enrich_per_search]:
            # SADD повертає 1, якщо id ще не в черзі — без дублікатів
            if await self.redis.sadd(ENRICH_PENDING, pid):
                await self.redis.lpush(self.settings.enrich_queue, pid)
                queued += 1
        if queued:
            log.info("enrichment queued", extra={"count": queued})

    def _to_out(self, o: ChainOffer, p: Product | None) -> OfferOut:
        qty = parse_quantity(o.pack_raw, o.title)
        if o.weighted:
            unit_price, unit_base = o.price, "кг"
        elif qty:
            unit_price, unit_base = round(o.price / (qty[0] / 1000), 2), qty[1]
        else:
            unit_price, unit_base = None, None
        chain = self.chains.get(o.chain)
        return OfferOut(
            product_id=p.id if p else None,
            chain=o.chain,
            chain_title=chain.title if chain else o.chain,
            title=o.title,
            price=o.price,
            old_price=o.old_price,
            pack=format_pack(*qty, fallback=o.pack_raw) if qty else o.pack_raw,
            unit_price=unit_price,
            unit_base=unit_base,
            in_stock=o.in_stock,
            stock_qty=o.stock_qty,
            promo=o.promo,
            ean=(p.ean if p and p.ean else o.ean),
            url=o.url,
        )


# ---------------------------------------------------------------- зіставлення


def build_groups(out: list[OfferOut], raw: list[ChainOffer]) -> list[MatchGroup]:
    """Union-find за ключами ean:X та fozzy:id (Сільпо і Фора мають спільні id товарів)."""
    parent = list(range(len(out)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first_by_key: dict[str, int] = {}
    for i, (o, r) in enumerate(zip(out, raw, strict=True)):
        keys = [f"ean:{o.ean}"] if o.ean else []
        if o.chain in ("silpo", "fora"):
            keys.append(f"fozzy:{r.chain_product_id}")
        for k in keys:
            if k in first_by_key:
                parent[find(i)] = find(first_by_key[k])
            else:
                first_by_key[k] = i

    clusters: dict[int, list[OfferOut]] = {}
    for i, o in enumerate(out):
        clusters.setdefault(find(i), []).append(o)

    groups: list[MatchGroup] = []
    for members in clusters.values():
        if len({m.chain for m in members}) < 2:
            continue
        members.sort(key=lambda m: m.price)
        buyable = [m for m in members if m.in_stock is not False]
        saving = None
        if len(buyable) >= 2 and buyable[-1].price > buyable[0].price:
            saving = round(buyable[-1].price - buyable[0].price, 2)
        groups.append(
            MatchGroup(
                title=min((m.title for m in members), key=len),
                items=[
                    GroupItem(
                        chain_title=m.chain_title, price=m.price, in_stock=m.in_stock, pack=m.pack
                    )
                    for m in members
                ],
                cheapest_in_stock=buyable[0].chain_title if buyable else None,
                saving=saving,
            )
        )
    # Найбільша економія — першою
    groups.sort(key=lambda g: g.saving or 0, reverse=True)
    return groups


# ---------------------------------------------------------------- сторінка результату


def paginate(
    snap: SearchSnapshot,
    *,
    cached: bool,
    sort: SortKey = "price",
    page: int = 1,
    page_size: int = 8,
    include_out_of_stock: bool = False,
) -> SearchPage:
    offers = snap.offers
    hidden = sum(1 for o in offers if o.in_stock is False)
    if not include_out_of_stock:
        offers = [o for o in offers if o.in_stock is not False]
    if sort == "unit":
        offers = sorted(offers, key=lambda o: (o.unit_price is None, o.unit_price or 0, o.price))
    else:
        offers = sorted(offers, key=lambda o: o.price)
    pages = max(1, math.ceil(len(offers) / page_size))
    page = min(max(1, page), pages)
    start = (page - 1) * page_size
    return SearchPage(
        search_id=snap.search_id,
        query=snap.query,
        created_at=snap.created_at,
        cached=cached,
        chains=snap.chains,
        sort=sort,
        page=page,
        pages=pages,
        page_size=page_size,
        total=len(offers),
        hidden_out_of_stock=0 if include_out_of_stock else hidden,
        offers=offers[start : start + page_size],
        groups=snap.groups,
    )

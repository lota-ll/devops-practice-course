"""HTTP API: пошук, історія цін, health-ендпоінти, /metrics.

Запуск: uvicorn --factory cinomir.api:create_app
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from . import __version__
from .chains import build_chains
from .config import Settings, get_settings
from .db import dispose, get_session, session_factory
from .logs import configure_logging, get_logger
from .metrics import HTTP_LATENCY, HTTP_REQUESTS
from .models import PriceSnapshot
from .schemas import SearchPage, SnapshotOut, SortKey
from .search import SearchService, paginate

log = get_logger("cinomir.api")
_QUIET_PATHS = {"/metrics", "/healthz", "/readyz"}


def create_app(
    settings: Settings | None = None,
    http: httpx.AsyncClient | None = None,
    redis: aioredis.Redis | None = None,
) -> FastAPI:
    """Фабрика: тести передають свої http/redis, продакшн — створює з налаштувань."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        own_http = http is None
        own_redis = redis is None
        client = http or httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
            # Трохи більше за таймаут мережі: спрацьовує wait_for у сервісі -> зрозуміла причина
            timeout=settings.chain_timeout_seconds + 1,
            follow_redirects=True,
        )
        r = redis or aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
        app.state.redis = r
        app.state.service = SearchService(
            settings, build_chains(settings), client, r, session_factory()
        )
        log.info("api started", extra={"chains": list(settings.enabled_chains)})
        yield
        if own_http:
            await client.aclose()
        if own_redis:
            await r.aclose()
        await dispose()

    app = FastAPI(title="cinomir", version=__version__, lifespan=lifespan)

    @app.middleware("http")
    async def observe_requests(request: Request, call_next):
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - started
            # Шаблон маршруту, а не сирий шлях — інакше вибух кардинальності метрик
            path = getattr(request.scope.get("route"), "path", "unmatched")
            HTTP_REQUESTS.labels(request.method, path, str(status_code)).inc()
            HTTP_LATENCY.labels(request.method, path).observe(duration)
            if path not in _QUIET_PATHS:
                log.info(
                    "request",
                    extra={
                        "method": request.method,
                        "path": path,
                        "status": status_code,
                        "duration_ms": round(duration * 1000, 2),
                    },
                )

    _register_routes(app, settings)
    return app


def _service(request: Request) -> SearchService:
    return request.app.state.service


SessionDep = Annotated[AsyncSession, Depends(get_session)]
ServiceDep = Annotated[SearchService, Depends(_service)]


def _register_routes(app: FastAPI, settings: Settings) -> None:
    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict:
        """Liveness: процес живий. Залежності НЕ перевіряємо (інакше каскадні рестарти)."""
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readyz(request: Request, session: SessionDep) -> JSONResponse:
        """Readiness: БД і Redis доступні. Мережі сюди НЕ входять: їхнє падіння ≠ наше."""
        checks: dict[str, str] = {}
        try:
            await session.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except (SQLAlchemyError, OSError) as exc:
            checks["database"] = f"error: {type(exc).__name__}"
        try:
            await request.app.state.redis.ping()
            checks["redis"] = "ok"
        except (aioredis.RedisError, OSError) as exc:
            checks["redis"] = f"error: {type(exc).__name__}"
        ready = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if ready else 503,
            content={"status": "ready" if ready else "not ready", "checks": checks},
        )

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/v1/search", response_model=SearchPage, tags=["search"])
    async def search(
        service: ServiceDep,
        q: Annotated[str, Query(min_length=2, max_length=100)],
        sort: SortKey = "price",
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=50)] = settings.page_size,
        include_out_of_stock: bool = False,
    ) -> SearchPage:
        if not q.strip():
            raise HTTPException(status_code=422, detail="empty query")
        snap, cached = await service.search(q)
        return paginate(
            snap,
            cached=cached,
            sort=sort,
            page=page,
            page_size=page_size,
            include_out_of_stock=include_out_of_stock,
        )

    @app.get("/api/v1/search/{search_id}", response_model=SearchPage, tags=["search"])
    async def search_page(
        search_id: str,
        service: ServiceDep,
        sort: SortKey = "price",
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=50)] = settings.page_size,
        include_out_of_stock: bool = False,
    ) -> SearchPage:
        """Наступні сторінки / інше сортування — з кешу, без нових запитів до мереж."""
        snap = await service.get_cached(search_id)
        if snap is None:
            raise HTTPException(status_code=404, detail="search expired")
        return paginate(
            snap,
            cached=True,
            sort=sort,
            page=page,
            page_size=page_size,
            include_out_of_stock=include_out_of_stock,
        )

    @app.get(
        "/api/v1/products/{product_id}/history",
        response_model=list[SnapshotOut],
        tags=["products"],
    )
    async def history(
        product_id: int,
        session: SessionDep,
        limit: Annotated[int, Query(ge=1, le=500)] = 50,
    ) -> list[SnapshotOut]:
        rows = await session.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.product_id == product_id)
            .order_by(PriceSnapshot.observed_at.desc(), PriceSnapshot.id.desc())
            .limit(limit)
        )
        return [
            SnapshotOut(
                observed_at=s.observed_at,
                price=float(s.price),
                old_price=float(s.old_price) if s.old_price is not None else None,
                promo=s.promo,
                in_stock=s.in_stock,
            )
            for s in rows
        ]

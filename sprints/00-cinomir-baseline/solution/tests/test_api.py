from __future__ import annotations

import httpx
import pytest

from cinomir.api import create_app

pytestmark = pytest.mark.anyio
Q = "тунець у власному соку"


@pytest.fixture
async def client(settings, http, redis, sessions):
    app = create_app(settings, http=http, redis=redis)
    # ASGITransport не запускає lifespan сам — запускаємо вручну
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


async def test_health(client):
    assert (await client.get("/healthz")).json() == {"status": "ok"}
    r = await client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["checks"] == {"database": "ok", "redis": "ok"}


async def test_readyz_fails_when_redis_down(client, redis, monkeypatch):
    async def broken():
        raise ConnectionError("redis down")

    monkeypatch.setattr(redis, "ping", broken)
    r = await client.get("/readyz")
    assert r.status_code == 503
    assert r.json()["checks"]["redis"].startswith("error")


async def test_search_then_page_from_cache(client, fake_chains):
    r = await client.get("/api/v1/search", params={"q": Q, "page_size": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["cached"] is False and body["total"] == 5 and body["pages"] == 2
    assert all(o["in_stock"] is not False for o in body["offers"])

    r2 = await client.get(
        f"/api/v1/search/{body['search_id']}", params={"page": 2, "sort": "unit", "page_size": 3}
    )
    assert r2.status_code == 200 and r2.json()["page"] == 2 and r2.json()["sort"] == "unit"
    assert fake_chains.calls["silpo"] == 1  # друга сторінка не ходила в мережі


async def test_validation_and_expired_search(client):
    assert (await client.get("/api/v1/search", params={"q": "т"})).status_code == 422
    assert (await client.get("/api/v1/search", params={"q": Q, "sort": "x"})).status_code == 422
    assert (await client.get("/api/v1/search/deadbeef")).status_code == 404


async def test_price_history(client):
    body = (await client.get("/api/v1/search", params={"q": Q})).json()
    pid = body["offers"][0]["product_id"]
    history = (await client.get(f"/api/v1/products/{pid}/history")).json()
    assert len(history) == 1 and history[0]["price"] == body["offers"][0]["price"]


async def test_metrics_use_route_template(client):
    await client.get("/api/v1/search/abc123")
    text = (await client.get("/metrics")).text
    assert 'path="/api/v1/search/{search_id}"' in text
    assert "abc123" not in text
    assert "cinomir_chain_requests_total" in text

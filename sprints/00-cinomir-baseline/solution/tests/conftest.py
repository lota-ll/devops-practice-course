from __future__ import annotations

import dataclasses

import fakeredis
import httpx
import pytest

from cinomir import db
from cinomir.chains import build_chains
from cinomir.config import Settings
from cinomir.search import SearchService

from .samples import FakeChains


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def settings(tmp_path) -> Settings:
    return dataclasses.replace(
        Settings.from_env(),
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        chain_timeout_seconds=2,
        allowed_user_ids=frozenset({42}),
    )


@pytest.fixture
async def sessions(settings):
    engine = db.configure_db(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.create_all)
    yield db.session_factory()
    await db.dispose()


@pytest.fixture
async def redis():
    r = fakeredis.FakeAsyncRedis(decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


@pytest.fixture
def fake_chains() -> FakeChains:
    return FakeChains()


@pytest.fixture
async def http(fake_chains):
    async with httpx.AsyncClient(transport=httpx.MockTransport(fake_chains)) as client:
        yield client


@pytest.fixture
def service(settings, http, redis, sessions) -> SearchService:
    return SearchService(settings, build_chains(settings), http, redis, sessions)

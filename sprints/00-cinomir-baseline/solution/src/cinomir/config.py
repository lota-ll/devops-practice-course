"""Конфігурація лише через змінні оточення (12-factor, принцип III)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from . import __version__


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _int_set(raw: str) -> frozenset[int]:
    return frozenset(int(x) for x in raw.replace(" ", "").split(",") if x)


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str
    log_level: str
    # --- мережі ---
    enabled_chains: tuple[str, ...]
    chain_timeout_seconds: float
    chain_concurrency: int
    search_limit_per_chain: int
    user_agent: str
    silpo_api: str
    silpo_branch: str
    fora_api: str
    fora_filial: int
    novus_api: str
    novus_store: int
    # --- пошук / кеш / черга ---
    cache_ttl_seconds: int
    enrich_queue: str
    enrich_per_search: int
    enrich_recheck_days: int
    # --- процеси ---
    worker_metrics_port: int
    # --- бот ---
    telegram_bot_token: str
    api_url: str
    allowed_user_ids: frozenset[int]
    page_size: int
    bot_metrics_port: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_url=_env(
                "DATABASE_URL",
                "postgresql+psycopg://cinomir:cinomir@localhost:5432/cinomir",
            ),
            redis_url=_env("REDIS_URL", "redis://localhost:6379/0"),
            log_level=_env("LOG_LEVEL", "INFO").upper(),
            enabled_chains=tuple(
                c.strip() for c in _env("ENABLED_CHAINS", "silpo,fora,novus").split(",") if c
            ),
            chain_timeout_seconds=float(_env("CHAIN_TIMEOUT_SECONDS", "8")),
            chain_concurrency=int(_env("CHAIN_CONCURRENCY", "2")),
            search_limit_per_chain=int(_env("SEARCH_LIMIT_PER_CHAIN", "60")),
            user_agent=_env(
                "CHAIN_USER_AGENT", f"cinomir/{__version__} (personal price comparison, low rate)"
            ),
            # Ідентифікатори — значення сайтів для гостя без адреси (Київ), 10.11.2026
            silpo_api=_env("SILPO_API", "https://sf-ecom-api.silpo.ua"),
            silpo_branch=_env("SILPO_BRANCH", "00000000-0000-0000-0000-000000000000"),
            fora_api=_env("FORA_API", "https://api.catalog.ecom.fora.ua"),
            fora_filial=int(_env("FORA_FILIAL", "3805")),
            novus_api=_env("NOVUS_API", "https://stores-api.zakaz.ua"),
            novus_store=int(_env("NOVUS_STORE", "48201031")),
            cache_ttl_seconds=int(_env("CACHE_TTL_SECONDS", "1800")),
            enrich_queue=_env("ENRICH_QUEUE", "cinomir:enrich"),
            enrich_per_search=int(_env("ENRICH_PER_SEARCH", "20")),
            enrich_recheck_days=int(_env("ENRICH_RECHECK_DAYS", "7")),
            worker_metrics_port=int(_env("WORKER_METRICS_PORT", "9100")),
            telegram_bot_token=_env("TELEGRAM_BOT_TOKEN", ""),
            api_url=_env("API_URL", "http://localhost:8000"),
            allowed_user_ids=_int_set(_env("ALLOWED_USER_IDS", "")),
            page_size=int(_env("PAGE_SIZE", "8")),
            bot_metrics_port=int(_env("BOT_METRICS_PORT", "9102")),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()

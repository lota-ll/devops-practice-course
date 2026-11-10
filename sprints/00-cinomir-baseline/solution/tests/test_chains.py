from __future__ import annotations

import httpx
import pytest

from cinomir.chains import BlockedError, ChainError, build_chains
from cinomir.chains.fora import parse_item as parse_fora
from cinomir.chains.novus import parse_item as parse_novus
from cinomir.chains.silpo import parse_item as parse_silpo

from .samples import (
    FORA_ITEM,
    FORA_PROMO_ITEM,
    NOVUS_ITEM,
    NOVUS_OOS_ITEM,
    SILPO_ITEM,
    SILPO_PROMO_ITEM,
)

pytestmark = pytest.mark.anyio


def test_silpo_item():
    o = parse_silpo(SILPO_ITEM)
    assert (o.price, o.pack_raw, o.chain_product_id) == (144, "160г", "919622")
    assert o.in_stock is True and o.stock_qty == 6
    assert o.url.endswith(SILPO_ITEM["slug"])


def test_silpo_promo():
    o = parse_silpo(SILPO_PROMO_ITEM)
    assert o.old_price == 99 and o.promo == "only_online"


def test_fora_shares_id_with_silpo_and_reports_stock():
    o = parse_fora(FORA_ITEM)
    assert o.chain_product_id == parse_silpo(SILPO_ITEM).chain_product_id
    assert o.in_stock is False  # quantity == 0
    promo = parse_fora(FORA_PROMO_ITEM)
    assert promo.promo == "Лайк ціна до 2026-11-16" and promo.in_stock is True


def test_novus_kopecks_discount_and_gtin():
    o = parse_novus(NOVUS_ITEM)
    assert (o.price, o.old_price) == (98.99, 116.5)
    assert o.ean == "4820235630591" and o.pack_raw == "160г"
    assert o.promo == "-15% до 2026-11-12"
    assert parse_novus(NOVUS_OOS_ITEM).in_stock is False


def test_unknown_chain_in_settings_fails_fast(settings):
    import dataclasses

    with pytest.raises(ValueError, match="atb"):
        build_chains(dataclasses.replace(settings, enabled_chains=("silpo", "atb")))


async def test_cloudflare_is_reported_as_blocked(settings):
    def cf(_):
        return httpx.Response(403, headers={"server": "cloudflare", "cf-ray": "1"})

    chain = build_chains(settings)["silpo"]
    async with httpx.AsyncClient(transport=httpx.MockTransport(cf)) as client:
        with pytest.raises(BlockedError):
            await chain.search(client, "тунець", 10)


async def test_changed_api_shape_is_chain_error(settings):
    def changed(_):
        return httpx.Response(200, json={"products": []})

    chain = build_chains(settings)["novus"]
    async with httpx.AsyncClient(transport=httpx.MockTransport(changed)) as client:
        with pytest.raises(ChainError):
            await chain.search(client, "тунець", 10)

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cinomir.bot import AllowlistMiddleware
from cinomir.botfmt import callback_data, keyboard, parse_callback, render_page
from cinomir.search import paginate

pytestmark = pytest.mark.anyio
Q = "тунець у власному соку"


async def _page(service, **kw) -> dict:
    snap, cached = await service.search(Q)
    return paginate(snap, cached=cached, **kw).model_dump(mode="json")


async def test_message_shows_price_and_weight_without_unit_price(service):
    text = render_page(await _page(service, page_size=8))
    assert "73.99 грн" in text and "<s>99.00</s>" in text
    assert "150 г" in text and "Сільпо" in text
    assert "грн/кг" not in text  # ціну за кг не показуємо — лише для сортування
    assert "Приховано відсутніх: 2" in text
    assert "Той самий товар у різних мережах" in text
    assert len(text) < 4096


async def test_chain_failure_is_visible(service, fake_chains):
    fake_chains.fail.add("novus")
    text = render_page(await _page(service))
    assert "⚠️ Novus: помилка" in text


def test_html_is_escaped():
    page = {
        "query": "<b>x</b>",
        "chains": [{"chain": "s", "title": "S", "ok": True, "relevant": 1}],
        "total": 1,
        "hidden_out_of_stock": 0,
        "page": 1,
        "pages": 1,
        "page_size": 8,
        "groups": [],
        "offers": [
            {
                "price": 1,
                "old_price": None,
                "pack": None,
                "chain_title": "S",
                "title": "A & B <script>",
                "url": None,
                "promo": None,
                "in_stock": True,
            }
        ],
    }
    text = render_page(page)
    assert "&lt;b&gt;x&lt;/b&gt;" in text and "A &amp; B &lt;script&gt;" in text


async def test_keyboard_toggles_sort_and_paginates(service):
    page = await _page(service, page_size=3)
    kb = keyboard(page)
    nav, sort_row = kb.inline_keyboard
    assert [b.text for b in nav] == ["▶️"]
    assert sort_row[0].text == "⚖️ вигідніше за вагою"
    assert parse_callback(sort_row[0].callback_data) == (page["search_id"], 1, "unit")

    unit_page = await _page(service, page_size=3, sort="unit", page=2)
    nav, sort_row = keyboard(unit_page).inline_keyboard
    assert [b.text for b in nav] == ["◀️"]
    assert sort_row[0].text == "💰 за ціною"


def test_callback_data_fits_telegram_limit_and_rejects_garbage():
    data = callback_data("0123456789abcdef", 12, "price")
    assert len(data.encode()) <= 64
    assert parse_callback(data) == ("0123456789abcdef", 12, "price")
    for bad in ("", "x:1:2:price", "p:sid:two:price", "p:sid:1:evil", "p:a:b"):
        assert parse_callback(bad) is None


async def test_allowlist_middleware():
    mw = AllowlistMiddleware(frozenset({42}))
    called = []

    async def handler(event, data):
        called.append(event)
        return "ok"

    event = object()  # ні Message, ні CallbackQuery — відповідати нікуди
    assert await mw(handler, event, {"event_from_user": SimpleNamespace(id=42)}) == "ok"
    assert await mw(handler, event, {"event_from_user": SimpleNamespace(id=7)}) is None
    assert await mw(handler, event, {}) is None
    assert called == [event]

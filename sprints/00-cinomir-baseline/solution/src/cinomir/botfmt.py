"""Форматування відповідей бота. Чисті функції: на вході dict від API, на виході текст/кнопки.

Окремо від bot.py, щоб тестувати без Telegram.
"""

from __future__ import annotations

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CALLBACK_PREFIX = "p"
SORT_LABELS = {"price": "💰 за ціною", "unit": "⚖️ вигідніше за вагою"}


def _money(value: float) -> str:
    return f"{value:.2f}"


def _availability(offer: dict) -> str:
    if offer.get("in_stock") is False:
        return " · ❌ немає"
    return ""


def render_offer(n: int, o: dict) -> str:
    price = f"<b>{_money(o['price'])} грн</b>"
    if o.get("old_price"):
        price += f" <s>{_money(o['old_price'])}</s>"
    meta = " · ".join(x for x in (o.get("pack"), escape(o["chain_title"])) if x)
    title = escape(o["title"])
    if o.get("url"):
        title = f'<a href="{escape(o["url"], quote=True)}">{title}</a>'
    line = f"{n}. {price} · {meta}{_availability(o)}\n    {title}"
    if o.get("promo"):
        line += f"\n    🏷 {escape(o['promo'])}"
    return line


def render_page(page: dict, max_groups: int = 3) -> str:
    """Текст повідомлення (HTML parse mode). Telegram обмежує 4096 символів — page_size ≤ 10."""
    lines = [f"🔎 <b>{escape(page['query'])}</b>"]

    by_chain: dict[str, int] = {}
    for c in page["chains"]:
        if c["ok"]:
            by_chain[c["title"]] = c["relevant"]
    summary = " · ".join(f"{escape(k)} {v}" for k, v in by_chain.items())
    lines.append(f"Знайдено в наявності: {page['total']} ({summary})")
    if page.get("hidden_out_of_stock"):
        lines.append(f"Приховано відсутніх: {page['hidden_out_of_stock']}")
    for c in page["chains"]:
        if not c["ok"]:
            lines.append(f"⚠️ {escape(c['title'])}: {escape(c.get('error') or 'недоступна')}")

    if not page["offers"]:
        lines.append("\nНічого не знайдено. Спробуйте коротший запит, напр. лише назву товару.")
        return "\n".join(lines)

    lines.append("")
    first = (page["page"] - 1) * page["page_size"] + 1
    for i, offer in enumerate(page["offers"], start=first):
        lines.append(render_offer(i, offer))

    groups = page.get("groups") or []
    if page["page"] == 1 and groups:
        lines.append("\n🔁 <b>Той самий товар у різних мережах</b>")
        for g in groups[:max_groups]:
            parts = []
            for item in g["items"]:
                mark = " ❌" if item.get("in_stock") is False else ""
                parts.append(f"{escape(item['chain_title'])} {_money(item['price'])}{mark}")
            line = f"• {escape(g['title'])}: " + " · ".join(parts)
            if g.get("saving") and g.get("cheapest_in_stock"):
                line += f" → дешевше в {escape(g['cheapest_in_stock'])} на {_money(g['saving'])}"
            lines.append(line)

    lines.append(f"\nСторінка {page['page']}/{page['pages']}")
    return "\n".join(lines)


def callback_data(search_id: str, page: int, sort: str) -> str:
    data = f"{CALLBACK_PREFIX}:{search_id}:{page}:{sort}"
    assert len(data.encode()) <= 64, "Telegram обмежує callback_data 64 байтами"
    return data


def parse_callback(data: str) -> tuple[str, int, str] | None:
    parts = data.split(":")
    if len(parts) != 4 or parts[0] != CALLBACK_PREFIX or parts[3] not in SORT_LABELS:
        return None
    try:
        return parts[1], int(parts[2]), parts[3]
    except ValueError:
        return None


def keyboard(page: dict) -> InlineKeyboardMarkup | None:
    sid, cur, pages, sort = page["search_id"], page["page"], page["pages"], page["sort"]
    rows: list[list[InlineKeyboardButton]] = []
    nav: list[InlineKeyboardButton] = []
    if cur > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=callback_data(sid, cur - 1, sort)))
    if cur < pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=callback_data(sid, cur + 1, sort)))
    if nav:
        rows.append(nav)
    if page["total"] > 1:
        other = "unit" if sort == "price" else "price"
        rows.append(
            [
                InlineKeyboardButton(
                    text=SORT_LABELS[other], callback_data=callback_data(sid, 1, other)
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


HELP_TEXT = (
    "Надішліть назву товару, напр. <b>тунець у власному соку</b>.\n\n"
    "Я перевірю Сільпо, Фору та Novus (Київ) і покажу товари в наявності "
    "від найдешевшого: ціну, вагу, акції.\n"
    "Кнопка «⚖️ вигідніше за вагою» пересортує той самий список з урахуванням фасовки."
)

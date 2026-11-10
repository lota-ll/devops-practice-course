"""Telegram-бот: тонкий клієнт до API. Long polling — не потрібна вхідна адреса і TLS.

⚠️ Long polling = лише ОДИН екземпляр бота на токен. Два екземпляри отримають від Telegram
409 Conflict (getUpdates). Тема спринту Kubernetes: replicas: 1 і чому HPA тут не можна.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message, TelegramObject
from prometheus_client import start_http_server

from .botfmt import HELP_TEXT, keyboard, parse_callback, render_page
from .config import Settings, get_settings
from .logs import configure_logging, get_logger
from .metrics import BOT_UPDATES

log = get_logger("cinomir.bot")


class AllowlistMiddleware(BaseMiddleware):
    """Приватний бот: обробляємо лише користувачів зі списку ALLOWED_USER_IDS.

    Незнайомцю повідомляємо його id — так власник налаштовує список без логів.
    """

    def __init__(self, allowed: frozenset[int]) -> None:
        self.allowed = allowed

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and user.id in self.allowed:
            return await handler(event, data)
        BOT_UPDATES.labels("denied").inc()
        log.warning("denied", extra={"user_id": getattr(user, "id", None)})
        text = f"⛔ Доступ обмежено. Ваш Telegram id: <code>{getattr(user, 'id', '?')}</code>"
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer("⛔ Доступ обмежено", show_alert=True)
        return None


def build_router(api: httpx.AsyncClient, page_size: int) -> Router:
    router = Router()

    @router.message(CommandStart())
    @router.message(Command("help"))
    async def start(message: Message) -> None:
        BOT_UPDATES.labels("help").inc()
        await message.answer(HELP_TEXT)

    @router.message(F.text & ~F.text.startswith("/"))
    async def on_query(message: Message) -> None:
        BOT_UPDATES.labels("search").inc()
        query = message.text.strip()
        if len(query) < 2:
            await message.answer("Запит закороткий.")
            return
        waiting = await message.answer("⏳ Шукаю в Сільпо, Форі та Novus…")
        try:
            r = await api.get("/api/v1/search", params={"q": query[:100], "page_size": page_size})
            r.raise_for_status()
        except httpx.HTTPError as exc:
            log.error("api error", extra={"error": repr(exc)})
            await waiting.edit_text("😕 Сервіс пошуку зараз недоступний. Спробуйте пізніше.")
            return
        page = r.json()
        await waiting.edit_text(render_page(page), reply_markup=keyboard(page))

    @router.callback_query(F.data.startswith("p:"))
    async def on_page(callback: CallbackQuery) -> None:
        BOT_UPDATES.labels("page").inc()
        parsed = parse_callback(callback.data or "")
        if parsed is None:
            await callback.answer()
            return
        search_id, page_no, sort = parsed
        try:
            r = await api.get(
                f"/api/v1/search/{search_id}",
                params={"page": page_no, "sort": sort, "page_size": page_size},
            )
        except httpx.HTTPError:
            await callback.answer("Сервіс недоступний", show_alert=True)
            return
        if r.status_code == 404:
            await callback.answer("Результати застаріли — надішліть запит ще раз", show_alert=True)
            return
        page = r.json()
        try:
            await callback.message.edit_text(render_page(page), reply_markup=keyboard(page))
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc):
                raise
        await callback.answer()

    return router


def build_dispatcher(settings: Settings, api: httpx.AsyncClient) -> Dispatcher:
    dp = Dispatcher()
    allow = AllowlistMiddleware(settings.allowed_user_ids)
    dp.message.outer_middleware(allow)
    dp.callback_query.outer_middleware(allow)
    dp.include_router(build_router(api, settings.page_size))
    return dp


async def amain() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    if not settings.allowed_user_ids:
        log.warning("ALLOWED_USER_IDS is empty: bot will deny everyone and reply with their id")
    start_http_server(settings.bot_metrics_port)

    bot = Bot(
        settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    async with httpx.AsyncClient(base_url=settings.api_url, timeout=30) as api:
        dp = build_dispatcher(settings, api)
        log.info("bot started", extra={"api_url": settings.api_url})
        # start_polling сам обробляє SIGTERM/SIGINT і коректно завершує роботу
        await dp.start_polling(bot)


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()

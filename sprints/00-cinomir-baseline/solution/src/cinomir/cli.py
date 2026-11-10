"""Пошук з терміналу через API — перевірити стек без Telegram.

cinomir-search "тунець у власному соку" [--sort unit] [--all]
"""

from __future__ import annotations

import argparse
import sys

import httpx

from .config import get_settings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Пошук цін через cinomir API")
    p.add_argument("query")
    p.add_argument("--sort", choices=["price", "unit"], default="price")
    p.add_argument("--page-size", type=int, default=20)
    p.add_argument("--all", action="store_true", help="показати й відсутні товари")
    p.add_argument("--api", default=get_settings().api_url)
    args = p.parse_args(argv)

    r = httpx.get(
        f"{args.api}/api/v1/search",
        params={
            "q": args.query,
            "sort": args.sort,
            "page_size": args.page_size,
            "include_out_of_stock": args.all,
        },
        timeout=30,
    )
    r.raise_for_status()
    page = r.json()

    for c in page["chains"]:
        state = f"{c['relevant']}/{c['received']}" if c["ok"] else f"❌ {c['error']}"
        print(f"{c['title']:<7} {state:<20} {c['latency_ms']} мс")
    print(f"\n{'кеш' if page['cached'] else 'свіжі дані'} · знайдено: {page['total']}\n")
    for o in page["offers"]:
        old = f" (було {o['old_price']:.2f})" if o["old_price"] else ""
        stock = " ❌" if o["in_stock"] is False else ""
        print(
            f"{o['price']:>8.2f}{old:<14} {o['pack'] or '—':<8} {o['chain_title']:<7}"
            f"{stock} {o['title']}"
        )
    for g in page["groups"]:
        items = " · ".join(
            f"{i['chain_title']} {i['price']:.2f}{' ❌' if i['in_stock'] is False else ''}"
            for i in g["items"]
        )
        print(f"\n🔁 {g['title']}: {items}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

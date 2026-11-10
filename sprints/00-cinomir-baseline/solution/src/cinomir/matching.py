"""Чисті функції без I/O: фасовка, релевантність, штрихкоди. Легко тестуються."""

from __future__ import annotations

import re

# ---------------------------------------------------------------- фасовка

_UNIT_RE = r"(кг|мл|гр|г|л|kg|ml|g|l)(?![a-zа-яіїєґ])"
_MULTI_RE = re.compile(r"(\d+)\s*[xх×*]\s*(\d+(?:[.,]\d+)?)\s*" + _UNIT_RE, re.I)
_SINGLE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*" + _UNIT_RE, re.I)
_FACTORS = {
    "кг": (1000, "кг"), "kg": (1000, "кг"),
    "г": (1, "кг"), "гр": (1, "кг"), "g": (1, "кг"),
    "л": (1000, "л"), "l": (1000, "л"),
    "мл": (1, "л"), "ml": (1, "л"),
}  # fmt: skip


def parse_quantity(*texts: str | None) -> tuple[float, str] | None:
    """(кількість у г або мл, база 'кг'|'л') з першого тексту, де знайшлось.

    "2*80г" -> (160, "кг"); "0,5 л" -> (500, "л"); "62.50 грн" -> None (грн ≠ грами).
    """
    for text in texts:
        if not text:
            continue
        m = _MULTI_RE.search(text)
        if m:
            factor, base = _FACTORS[m[3].lower()]
            return int(m[1]) * float(m[2].replace(",", ".")) * factor, base
        m = _SINGLE_RE.search(text)
        if m:
            amount = float(m[1].replace(",", "."))
            factor, base = _FACTORS[m[2].lower()]
            if amount > 0:
                return amount * factor, base
    return None


def format_pack(qty: float | None, base: str | None, fallback: str | None = None) -> str | None:
    """160 г / 1.5 кг / 500 мл / 1 л — однаково для всіх мереж."""
    if qty is None or base is None:
        return fallback
    if base == "кг":
        return f"{qty / 1000:g} кг" if qty >= 1000 else f"{qty:g} г"
    return f"{qty / 1000:g} л" if qty >= 1000 else f"{qty:g} мл"


# ---------------------------------------------------------------- релевантність

# Латинські двійники кирилиці трапляються в назвах ("подрiбнений" з латинською i)
_LOOKALIKES = str.maketrans({"i": "і", "a": "а", "e": "е", "o": "о", "c": "с", "p": "р", "x": "х"})


def _norm(text: str) -> str:
    return text.lower().replace("ʼ", "'").translate(_LOOKALIKES)


def query_tokens(query: str) -> list[str]:
    return [t for t in re.findall(r"\w+", query.lower()) if len(t) >= 3]


def main_word(query: str) -> str:
    """Що надсилаємо в пошук мережі: лише головне (перше значуще) слово.

    Пошук Фори вимагає збігу всіх слів (6 результатів замість 37), пошук Сільпо надто
    широкий — тому в мережу йде широкий запит, а точність забезпечуємо самі (relevance).
    """
    tokens = query_tokens(query)
    return tokens[0] if tokens else query.strip()


def relevance(query: str, title: str) -> float:
    """Частка значущих слів запиту в назві (за префіксом — грубо гасить відмінки).

    Перше слово обов'язкове: інакше «томати у власному соку» проходять на «тунець у власному
    соку». Префікс "туне" збігається з "Тунець", але не з "корм з тунцем" — це бажано.
    """
    tokens = [_norm(t) for t in query_tokens(query)]
    if not tokens:
        return 1.0
    hay = _norm(title)
    found = [t[: max(3, len(t) - 2)] in hay for t in tokens]
    if not found[0]:
        return 0.0
    return sum(found) / len(tokens)


# ---------------------------------------------------------------- штрихкоди (GS1)


def gtin_check_digit(body: str) -> int:
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10


def gtin_is_valid(code: str) -> bool:
    return code.isdigit() and gtin_check_digit(code[:-1]) == int(code[-1])


def normalize_gtin(code: str | None) -> str | None:
    """'04820235630591' і '4820235630591' -> один ключ. Биті коди -> None."""
    if not code:
        return None
    digits = re.sub(r"\D", "", str(code)).lstrip("0")
    if not 8 <= len(digits) <= 14:
        return None
    gtin = digits.zfill(13)
    return gtin if gtin_is_valid(gtin) else None


def is_internal_code(gtin: str) -> bool:
    """Префікси 020–029 — внутрішні коди мережі; між мережами не збігаються."""
    prefix = gtin[1:4] if len(gtin) == 14 else gtin[:3]
    return 20 <= int(prefix) <= 29


def case_to_unit_gtin(gtin14: str) -> str:
    """GTIN-14 ящика -> ймовірний EAN-13 банки (типова схема GS1; це евристика)."""
    body = gtin14[1:13]
    return body + str(gtin_check_digit(body))


def pick_public_ean(codes: list[str]) -> tuple[str | None, str | None]:
    """(ean, джерело). Сільпо часто ставить першим код ящика — пріоритет коду одиниці товару."""
    public = [c for c in (normalize_gtin(x) for x in codes) if c and not is_internal_code(c)]
    retail = next((c for c in public if len(c) == 13), None)
    if retail:
        return retail, "retail"
    case = next((c for c in public if len(c) == 14), None)
    if case:
        return case_to_unit_gtin(case), "from_case"
    return None, None

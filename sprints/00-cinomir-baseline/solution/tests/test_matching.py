from __future__ import annotations

import pytest

from cinomir.matching import (
    format_pack,
    gtin_is_valid,
    is_internal_code,
    main_word,
    normalize_gtin,
    parse_quantity,
    pick_public_ean,
    relevance,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("160г", (160, "кг")),
        ("185 г", (185, "кг")),
        ("1 кг", (1000, "кг")),
        ("0,5 л", (500, "л")),
        ("500мл", (500, "л")),
        ("Сік 4х200мл", (800, "л")),
        ("2*80г/уп", (160, "кг")),
        ("Тунець Fish Line у власному соці 160г", (160, "кг")),
        ("62.50 грн/шт", None),  # "грн" не повинно читатись як грами
        ("Тунець Fish Line", None),
        (None, None),
    ],
)
def test_parse_quantity(text, expected):
    assert parse_quantity(text) == expected


def test_parse_quantity_uses_first_source_that_matches():
    assert parse_quantity(None, "", "Назва 0.33 л") == (330, "л")


@pytest.mark.parametrize(
    ("qty", "base", "expected"),
    [(160, "кг", "160 г"), (1500, "кг", "1.5 кг"), (500, "л", "500 мл"), (1000, "л", "1 л")],
)
def test_format_pack(qty, base, expected):
    assert format_pack(qty, base) == expected


def test_format_pack_fallback():
    assert format_pack(None, None, "шт") == "шт"


def test_main_word_is_first_meaningful_token():
    assert main_word("тунець у власному соку") == "тунець"
    assert main_word("  Молоко 2,5% ") == "молоко"


def test_relevance_filters_cat_food_but_keeps_tuna():
    q = "тунець у власному соку"
    assert relevance(q, "Тунець Fish Line у власному соці") >= 0.6
    # латинська 'i' у "подрiбнений" не заважає
    assert relevance(q, "Консерви Своя Лінія Тунець подрiбнений у власному соку") == 1.0
    assert relevance(q, "Вологий корм Whiskas з тунцем в желе") < 0.6
    assert relevance(q, "Тунець в олії") < 0.6
    # перше слово обов'язкове
    assert relevance(q, "Томати Oscar очищені різані у власному соку") == 0.0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4820235630591", "4820235630591"),
        ("04820235630591", "4820235630591"),
        ("96385074", "0000096385074"),  # EAN-8 -> GTIN-13
        ("18436024298939", "18436024298939"),  # GTIN-14 ящика лишається 14-значним
        ("4820235630592", None),  # неправильна цифра перевірки
        ("abc", None),
        (None, None),
    ],
)
def test_normalize_gtin(raw, expected):
    assert normalize_gtin(raw) == expected


def test_internal_codes_are_not_used_for_matching():
    assert is_internal_code("0250015393127")
    assert not is_internal_code("4820235630591")
    assert pick_public_ean(["0250015393127", "4820235630591"]) == ("4820235630591", "retail")
    assert pick_public_ean(["0250015393127"]) == (None, None)


def test_case_gtin14_is_last_resort_and_marked():
    assert pick_public_ean(["18436024298939", "8436024298932"]) == ("8436024298932", "retail")
    ean, source = pick_public_ean(["18436024298939"])
    assert (ean, source) == ("8436024298932", "from_case")
    assert gtin_is_valid(ean)

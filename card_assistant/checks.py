"""Post-generation factuality checks."""

from __future__ import annotations

import re

from .models import Card, ProductInput

# "Цен" is matched only as a price word, never inside "центральная" or "ценный".
PRICE_PATTERN = r"\b(?:цена|цены|цене|цену|ценой|ценами|ценах|ценник\w*|ценов\w*)\b"
RISKY_PATTERNS = (
    PRICE_PATTERN,
    r"\bстоимост\w*",
    r"\bдоставк\w*",
    r"\bгаранти\w*",
    r"\bв\s+наличии\b",
    r"\bсертификат\w*",
    r"\bгост\b",
    r"\bтр\s*тс\b",
    r"\bгосреестр\w*",
    r"\bповерк\w*",
    r"\bсрок\s+службы\b",
    r"\bстран(?:а|ы|е|у|ой|ами|ах)\b",
    r"\bлучший\b|№\s*1|\bуникальн\w*|\bидеальн\w*|\bлидер\w*",
)
NUMBER = r"(\d+(?:\.\d+)?)"
WORD_UNITS = r"мпа|кпа|bar|°c|мм|ма|гц|кг"
SYMBOL_UNITS = r"%|℃"
UNIT_ALIASES = {"℃": "°c"}


def normalize(text: str) -> str:
    """Normalize punctuation used in numeric technical values."""
    value = text.lower().replace("ё", "е").replace(",", ".").replace("\u00a0", " ")
    return value.replace("°с", "°c")


def numeric_pairs(text: str) -> set[tuple[str, str]]:
    """Return normalized number-unit pairs, including percent and Celsius."""
    value = normalize(text)
    pairs = set(re.findall(rf"{NUMBER}\s*({WORD_UNITS})(?![а-яa-z0-9_])", value))
    pairs.update(
        (
            (number, UNIT_ALIASES.get(unit, unit))
            for number, unit in re.findall(rf"{NUMBER}\s*({SYMBOL_UNITS})", value)
        )
    )
    return pairs


def plain_numbers(text: str) -> set[str]:
    """Return numeric tokens."""
    return set(re.findall(r"\d+(?:\.\d+)?", normalize(text)))


def blocking_warnings(warnings: list[str]) -> list[str]:
    """Length warnings are advisory; factuality warnings block publication."""
    return [warning for warning in warnings if not warning.startswith("description_length")]


def check(card: Card, product: ProductInput) -> list[str]:
    """Return deterministic warnings for unsupported generated claims."""
    source = " ".join(
        [
            product.name,
            product.manufacturer,
            product.category,
            product.description,
            *product.specs.keys(),
            *product.specs.values(),
        ]
    )
    public = " ".join(
        [
            card.seo_title,
            card.seo_description,
            *card.search_queries,
            *card.commercial_block.suitable_for,
            *card.commercial_block.tasks_solved,
        ]
    )
    warnings: list[str] = []
    if len(card.seo_title) > 70:
        warnings.append("title_over_70")
    if len(card.seo_description) < 800:
        warnings.append("description_length_below_min")
    if len(card.seo_description) > 1200:
        warnings.append("description_length_over_max")
    for pair in numeric_pairs(public) - numeric_pairs(source):
        warnings.append(f"unsupported_number_unit:{pair[0]} {pair[1]}")
    for number in plain_numbers(public) - plain_numbers(source):
        warnings.append(f"unsupported_number:{number}")
    for pattern in RISKY_PATTERNS:
        if re.search(pattern, public, re.I) and not re.search(pattern, source, re.I):
            warnings.append(f"unsupported_claim:{pattern}")
    return list(dict.fromkeys(warnings))

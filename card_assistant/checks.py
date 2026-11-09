"""Post-generation factuality checks."""

from __future__ import annotations

import re

from .models import Card, ProductInput

RISKY_PATTERNS = (
    r"\bцен(?:а|ы|е|у|ой|ами|ах|ник|ов\w*)\b",
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
    r"\bстран\w*",
    r"\bлучший\b|№\s*1|\bуникальн\w*|\bидеальн\w*|\bлидер\w*",
)
UNITS = r"мпа|кпа|bar|°c|℃|мм|ма|гц|кг|%"


def normalize(text: str) -> str:
    """Normalize punctuation used in numeric technical values."""
    return text.lower().replace("ё", "е").replace(",", ".").replace("\u00a0", " ")


def numeric_pairs(text: str) -> set[tuple[str, str]]:
    """Return normalized number-unit pairs."""
    pattern = rf"(\d+(?:\.\d+)?)\s*({UNITS})(?!\w)"
    return {(number, unit) for number, unit in re.findall(pattern, normalize(text))}


def plain_numbers(text: str) -> set[str]:
    """Return numeric tokens."""
    return set(re.findall(r"\d+(?:\.\d+)?", normalize(text)))


def check(card: Card, product: ProductInput) -> list[str]:
    """Return deterministic warnings for unsupported generated claims."""
    source = " ".join(
        [
            product.name,
            product.manufacturer,
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

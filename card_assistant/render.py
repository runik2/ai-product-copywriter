import re
from pathlib import Path

from .models import Card

TRANSLIT = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)


def markdown(card: Card) -> str:
    rows = (
        "\n".join(f"| {x.name} | {x.value} |" for x in card.key_characteristics)
        or "| Данных нет | Данных нет |"
    )
    missing = (
        "\n".join(f"- **{x.severity}** — {x.field}: {x.reason}" for x in card.missing_data)
        or "- Нет"
    )
    warnings = "\n".join(f"- {x}" for x in card.validation.warnings) or "- Нет"
    return (
        f"# {card.product_name}\n\n## Заголовок ({card.validation.title_length} символов)\n{card.seo_title}\n\n## Описание ({card.validation.description_length} символов)\n{card.seo_description}\n\n## Ключевые характеристики\n| Характеристика | Значение |\n|---|---|\n{rows}\n\n## Поисковые запросы\n"
        + "\n".join(f"- {x}" for x in card.search_queries)
        + "\n\n## Commercial-блок\n**Кому подходит:** "
        + "; ".join(card.commercial_block.suitable_for)
        + "\n\n**Задачи:** "
        + "; ".join(card.commercial_block.tasks_solved)
        + f"\n\n**Менеджеру:** {card.commercial_block.manager_notes}\n\n## Что нужно уточнить\n{missing}\n\n## Проверить перед публикацией\n{warnings}\n"
    )


def slug(value: str) -> str:
    """Build a safe ASCII slug from a mixed Russian/Latin product name."""
    transliterated = value.lower().translate(TRANSLIT)
    safe = re.sub(r"[^a-z0-9]+", "-", transliterated).strip("-")
    return safe[:64].strip("-") or "product"


def save(cards: list[Card], out: Path, fmt: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for card in cards:
        name = f"{card.source.get('offer_id', 'unknown')}_{slug(card.product_name)}"
        if fmt in ("json", "both"):
            (out / f"{name}.json").write_text(card.model_dump_json(indent=2), encoding="utf8")
        if fmt in ("md", "both"):
            (out / f"{name}.md").write_text(markdown(card), encoding="utf8")

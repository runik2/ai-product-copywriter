import re
from pathlib import Path
from .models import Card
def markdown(card: Card) -> str:
    rows="\n".join(f"| {x.name} | {x.value} |" for x in card.key_characteristics) or "| Данных нет | Данных нет |"
    missing="\n".join(f"- **{x.severity}** — {x.field}: {x.reason}" for x in card.missing_data) or "- Нет"
    warnings="\n".join(f"- {x}" for x in card.validation.warnings) or "- Нет"
    return f"# {card.product_name}\n\n## Заголовок ({card.validation.title_length} символов)\n{card.seo_title}\n\n## Описание ({card.validation.description_length} символов)\n{card.seo_description}\n\n## Ключевые характеристики\n| Характеристика | Значение |\n|---|---|\n{rows}\n\n## Поисковые запросы\n"+"\n".join(f"- {x}" for x in card.search_queries)+f"\n\n## Commercial-блок\n**Кому подходит:** "+"; ".join(card.commercial_block.suitable_for)+f"\n\n**Задачи:** "+"; ".join(card.commercial_block.tasks_solved)+f"\n\n**Менеджеру:** {card.commercial_block.manager_notes}\n\n## Что нужно уточнить\n{missing}\n\n## Проверить перед публикацией\n{warnings}\n"
def save(cards: list[Card], out: Path, fmt: str) -> None:
    out.mkdir(parents=True,exist_ok=True)
    for card in cards:
        translit = card.product_name.encode("ascii", "ignore").decode().lower()
        safe = re.sub(r"[^a-z0-9]+", "-", translit).strip("-") or "product"
        safe = f"{card.source.get('offer_id', 'unknown')}_{safe[:48]}"
        if fmt in ("json","both"): (out/f"{safe}.json").write_text(card.model_dump_json(indent=2),encoding="utf8")
        if fmt in ("md","both"): (out/f"{safe}.md").write_text(markdown(card),encoding="utf8")

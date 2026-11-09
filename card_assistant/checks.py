from __future__ import annotations
import re
from .models import ProductInput, Card
RISKY = ("сертификат", "гост", "тр тс", "госреестр", "поверк", "гарант", "срок службы", "доставк", "в наличии", "цен", "страна", "лучший", "№1", "уникальн", "идеальн", "лидер")
ALWAYS_FORBIDDEN = ("гарант", "доставк", "срок", "в наличии", "цен")
def normalized(text: str) -> str: return re.sub(r"[\s\-–—,]", "", text.lower().replace("ё","е").replace("٫","."))
def numbers(text: str) -> set[str]:
    text=text.replace(",", ".").replace("–", " ").replace("—", " ").replace("-", " ").replace("\u00a0", " ")
    return set(re.findall(r"\d+(?:\.\d+)?", text))
def check(card: Card, product: ProductInput) -> list[str]:
    warnings=[]; source=" ".join([product.name, product.manufacturer, product.description, *product.specs.keys(), *product.specs.values()])
    text=" ".join([card.seo_title, card.seo_description, *card.search_queries, card.commercial_block.manager_notes, *card.commercial_block.suitable_for, *card.commercial_block.tasks_solved])
    if len(card.seo_title)>70: warnings.append("title_over_70")
    if not 800 <= len(card.seo_description) <= 1200: warnings.append("description_length_below_min" if len(card.seo_description)<800 else "description_length_over_max")
    source_numbers=numbers(source)
    for number in numbers(text):
        if number not in source_numbers: warnings.append(f"unsupported_number:{number}")
    lower_source, lower_text=source.lower(), text.lower()
    for term in ALWAYS_FORBIDDEN:
        if term in lower_text: warnings.append(f"forbidden_claim:{term}")
    for term in RISKY:
        if term not in ALWAYS_FORBIDDEN and term in lower_text and term not in lower_source: warnings.append(f"unsupported_claim:{term}")
    return list(dict.fromkeys(warnings))

"""Memory-safe YML downloading, parsing, selection and page enrichment."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path

import requests

from .errors import ApiError, InputError
from .models import ProductInput

UA = {"User-Agent": "card-assistant-test/1.0"}
NON_TECHNICAL_NAME = re.compile(
    r"(?:популярн\w*\s+подборк|подборк\w*|категор\w*|наличи\w*|цен[аы]?\b|"
    r"стоимост\w*|доставк\w*|рейтинг\w*|отзыв\w*|скидк\w*|акци\w*)",
    re.I,
)
PRICE_CLAUSE = re.compile(
    r"(?:привлекательн\w*\s+)?(?:цена|цены|цене|цену|ценой|ценами|ценах|"
    r"ценник\w*|ценов\w*)[^.!?]*[.!?]?",
    re.I,
)
AD_SENTENCE = re.compile(
    r"\b(?:стоимост\w*|скидк\w*|акци\w*|выгодн\w*|купить|приобрести|руб\w*)\b|₽",
    re.I,
)
BLOCK_CLOSE = re.compile(
    r"</(?:p|div|li|ul|ol|h[1-6]|tr|td|th|table|section|article|blockquote)\s*>",
    re.I,
)
BR = re.compile(r"<br\s*/?>", re.I)
TAG = re.compile(r"<[^>]+>")
GLUED_WORDS = re.compile(r"(?<=[а-яёa-z0-9C])(?=[А-ЯЁA-Z])")
SENTENCE_START = re.compile(r"(?<=[.!?:;])(?=[А-ЯЁA-Z])")


def clean_text(value: str | None) -> str:
    """Decode a short XML value without changing meaningful punctuation."""
    value = TAG.sub(" ", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _html_to_text(value: str) -> str:
    value = unescape(value or "")
    value = BR.sub("\n", value)
    value = BLOCK_CLOSE.sub("\n", value)
    value = TAG.sub(" ", value).replace("\u00a0", " ")
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    return re.sub(r"\n{2,}", "\n", value).strip()


def _split_glued_words(value: str) -> str:
    """Insert a separator at boundaries lost by the source page."""
    return SENTENCE_START.sub(" ", GLUED_WORDS.sub(" ", value))


def clean_description(value: str | None) -> str:
    """Convert simple HTML descriptions into readable sentences."""
    text = _html_to_text(value)
    lines = [re.sub(r"\s+", " ", line).strip(" .;") for line in text.splitlines()]
    joined = ". ".join(line for line in lines if line)
    joined = _split_glued_words(joined)
    return re.sub(r"(?:\.\s*){2,}", ". ", joined).strip(" .")


def _remove_advertising(value: str) -> str:
    value = PRICE_CLAUSE.sub(". ", value)
    sentences = re.split(r"(?<=[.!?])\s+", value)
    kept = [sentence for sentence in sentences if sentence and not AD_SENTENCE.search(sentence)]
    return " ".join(kept)


def clean_jsonld_description(value: str | None) -> str:
    """Clean JSON-LD text, preserving word boundaries and dropping ad sentences."""
    text = _remove_advertising(clean_description(value))
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    text = re.sub(r"\.{2,}", ".", text)
    return re.sub(r"\s+", " ", text).strip(" .")


def is_technical(name: str) -> bool:
    """Reject catalog navigation and marketing fields from product specs."""
    normalized = re.sub(r"\s+", " ", name).strip()
    return bool(normalized) and not NON_TECHNICAL_NAME.search(normalized)


def fetch(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, headers=UA, timeout=60, stream=True) as response:
            response.raise_for_status()
            with out.open("wb") as stream:
                for chunk in response.iter_content(65536):
                    stream.write(chunk)
    except requests.RequestException as exc:
        raise ApiError(f"Не удалось скачать фид: {exc}") from exc


def parse(path: Path) -> list[ProductInput]:
    products: list[ProductInput] = []
    try:
        for _, el in ET.iterparse(path, events=("end",)):
            if el.tag != "offer":
                continue
            if el.attrib.get("available", "true") == "false":
                el.clear()
                continue

            def text(tag: str) -> str:
                return clean_text(el.findtext(tag))

            params: dict[str, str] = {}
            for param in el.findall("param"):
                key, value = clean_text(param.get("name")), clean_text(param.text)
                if not key or not value or not is_technical(key):
                    continue
                value = f"{value} {param.get('unit', '').strip()}".strip()
                params[key] = f"{params[key]}; {value}" if key in params else value
            name, vendor, model, kind = (
                text("name"),
                text("vendor"),
                text("model"),
                text("typePrefix"),
            )
            name = name or " ".join(x for x in (kind, vendor, model) if x)
            if name:
                for key, value in (
                    ("Тип оборудования", kind),
                    ("Артикул производителя", text("vendorCode")),
                    ("Модель", model),
                    ("Страна происхождения", text("country_of_origin")),
                ):
                    if value and is_technical(key):
                        params.setdefault(key, value)
                products.append(
                    ProductInput(
                        name=name,
                        manufacturer=vendor or "Данных нет",
                        specs=params,
                        description=clean_description(el.findtext("description")),
                        offer_id=el.get("id", ""),
                        url=text("url"),
                        category=text("categoryId"),
                    )
                )
            el.clear()
    except ET.ParseError as exc:
        raise InputError(f"Битый XML-фид: {exc}") from exc
    return products


INSTRUMENTS = (
    "манометр",
    "термометр",
    "датчик",
    "преобразователь",
    "расходомер",
    "уровнемер",
    "термопар",
    "реле давления",
    "модуль",
)


def pick(products: list[ProductInput], ids: list[str] | None = None) -> list[ProductInput]:
    if ids:
        picked = [p for p in products if p.offer_id in ids]
        if len(picked) != 2:
            raise InputError("По --ids найдены не ровно два товара")
        return picked
    ranked = sorted(
        products,
        key=lambda p: (
            any(w in (p.name + p.category).lower() for w in INSTRUMENTS),
            len(p.specs) + len(p.description) / 100,
        ),
        reverse=True,
    )
    if not ranked:
        raise InputError("В фиде нет подходящих товаров")
    first = ranked[0]
    second = next(
        (
            p
            for p in reversed(ranked)
            if p.category != first.category and any(w in p.name.lower() for w in INSTRUMENTS)
        ),
        ranked[min(1, len(ranked) - 1)],
    )
    return [first, second]


def _find_product(data: object) -> dict | None:
    if isinstance(data, dict):
        kind = data.get("@type")
        if kind == "Product" or (isinstance(kind, list) and "Product" in kind):
            return data
        graph = data.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                found = _find_product(item)
                if found:
                    return found
    return None


def fetch_page_jsonld(url: str) -> dict | None:
    """Fetch the Product JSON-LD block from a public product page, if present."""
    if not url:
        return None
    try:
        response = requests.get(url, headers=UA, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return None
    blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>([\s\S]*?)</script>',
        response.text,
        re.I,
    )
    for block in blocks:
        try:
            data = json.loads(block, strict=False)
        except (json.JSONDecodeError, TypeError):
            continue
        found = _find_product(data)
        if found:
            return found
    return None


def enrich_from_page(product: ProductInput, data: dict | None = None) -> ProductInput:
    """Add confirmed JSON-LD description and properties from the public product page."""
    if data is None:
        data = fetch_page_jsonld(product.url)
    if not data:
        return product
    specs = dict(product.specs)
    for item in data.get("additionalProperty") or []:
        if not isinstance(item, dict):
            continue
        name = clean_text(item.get("name"))
        value = clean_text(item.get("value"))
        if name and value and is_technical(name):
            specs[name] = value
    description = clean_jsonld_description(data.get("description")) or product.description
    range_match = re.search(
        r"(-?\d+(?:[.,]\d+)?)\s*[…\-–—]\s*\+?(\d+(?:[.,]\d+)?)\s*(?:°\s*C|℃)",
        description,
        re.I,
    )
    if range_match:
        low, high = (part.replace(",", ".") for part in range_match.groups())
        specs.setdefault("Диапазон измерений", f"{low} … +{high} °C")
    return product.model_copy(update={"specs": specs, "description": description})

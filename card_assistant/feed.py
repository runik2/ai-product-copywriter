"""Memory-safe YML downloading, parsing and selection."""

from __future__ import annotations
from pathlib import Path
from html import unescape
import re
import xml.etree.ElementTree as ET
import json
import requests
from .models import ProductInput

UA = {"User-Agent": "card-assistant-test/1.0"}


def clean_text(value: str | None) -> str:
    """Decode a short XML value without changing meaningful punctuation."""
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()


def clean_description(value: str | None) -> str:
    """Convert simple HTML descriptions into readable sentences."""
    value = value or ""
    value = re.sub(r"</(?:li|p)\s*>|<br\s*/?>", ". ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"(?:\.\s*){2,}", ". ", re.sub(r"\s+", " ", unescape(value))).strip(" .")


def fetch(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, headers=UA, timeout=60, stream=True) as response:
            response.raise_for_status()
            with out.open("wb") as stream:
                for chunk in response.iter_content(65536):
                    stream.write(chunk)
    except requests.RequestException as exc:
        raise RuntimeError(f"Не удалось скачать фид: {exc}") from exc


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
            for p in el.findall("param"):
                key, value = clean_text(p.get("name")), clean_text(p.text)
                if not key or not value:
                    continue
                value = f"{value} {p.get('unit', '').strip()}".strip()
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
                    if value:
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
        raise RuntimeError(f"Битый XML-фид: {exc}") from exc
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
            raise RuntimeError("По --ids найдены не ровно два товара")
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
        raise RuntimeError("В фиде нет подходящих товаров")
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


def enrich_from_page(product: ProductInput) -> ProductInput:
    """Add confirmed JSON-LD description and properties from the public product page."""
    if not product.url:
        return product
    try:
        response = requests.get(product.url, headers=UA, timeout=30)
        response.raise_for_status()
        blocks = re.findall(
            r'<script type="application/ld\+json">\s*([\s\S]*?)</script>', response.text
        )
        data = next((json.loads(block) for block in blocks if '"@type": "Product"' in block), {})
    except (requests.RequestException, StopIteration, json.JSONDecodeError):
        return product
    specs = dict(product.specs)
    for item in data.get("additionalProperty", []):
        name = clean_text(item.get("name"))
        value = clean_text(item.get("value"))
        if name and value:
            specs[name] = value
    description = clean_description(data.get("description")) or product.description
    description = re.sub(r"[^.]*\bцен\w*[^.]*\.?", "", description, flags=re.IGNORECASE).strip()
    range_match = re.search(r"(-?\d+)\s*[…-]\s*\+?(\d+)\s*(°C|℃)", description)
    if range_match:
        specs["Диапазон измерений"] = " ".join(range_match.groups())
    return product.model_copy(update={"specs": specs, "description": description})

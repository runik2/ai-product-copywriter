"""Memory-safe YML downloading, parsing and selection."""
from __future__ import annotations
from pathlib import Path
from html import unescape
import re, xml.etree.ElementTree as ET
import requests
from .models import ProductInput

UA = {"User-Agent": "card-assistant-test/1.0"}
def clean_html(value: str | None) -> str:
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
                for chunk in response.iter_content(65536): stream.write(chunk)
    except requests.RequestException as exc: raise RuntimeError(f"Не удалось скачать фид: {exc}") from exc

def parse(path: Path) -> list[ProductInput]:
    products: list[ProductInput] = []
    try:
        for _, el in ET.iterparse(path, events=("end",)):
            if el.tag != "offer": continue
            if el.attrib.get("available", "true") == "false": el.clear(); continue
            text = lambda tag: clean_html(el.findtext(tag))
            params: dict[str, str] = {}
            for p in el.findall("param"):
                key, value = clean_html(p.get("name")), clean_html(p.text)
                if not key or not value: continue
                value = f"{value} {p.get('unit', '').strip()}".strip()
                params[key] = f"{params[key]}; {value}" if key in params else value
            name, vendor, model, kind = text("name"), text("vendor"), text("model"), text("typePrefix")
            name = name or " ".join(x for x in (kind, vendor, model) if x)
            if name:
                for key, value in (("Тип оборудования", kind), ("Артикул производителя", text("vendorCode")), ("Модель", model), ("Страна происхождения", text("country_of_origin"))):
                    if value: params.setdefault(key, value)
                products.append(ProductInput(name=name, manufacturer=vendor or "Данных нет", specs=params, description=text("description"), offer_id=el.get("id", ""), url=text("url"), category=text("categoryId")))
            el.clear()
    except ET.ParseError as exc: raise RuntimeError(f"Битый XML-фид: {exc}") from exc
    return products

INSTRUMENTS = ("манометр", "термометр", "датчик", "преобразователь", "расходомер", "уровнемер", "термопар", "реле давления", "модуль")
def pick(products: list[ProductInput], ids: list[str] | None = None) -> list[ProductInput]:
    if ids:
        picked = [p for p in products if p.offer_id in ids]
        if len(picked) != 2: raise RuntimeError("По --ids найдены не ровно два товара")
        return picked
    ranked = sorted(products, key=lambda p: (any(w in (p.name + p.category).lower() for w in INSTRUMENTS), len(p.specs) + len(p.description) / 100), reverse=True)
    if not ranked: raise RuntimeError("В фиде нет подходящих товаров")
    first = ranked[0]; second = next((p for p in reversed(ranked) if p.category != first.category and any(w in p.name.lower() for w in INSTRUMENTS)), ranked[min(1, len(ranked)-1)])
    return [first, second]

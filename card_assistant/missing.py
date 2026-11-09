from __future__ import annotations
import json
import re
from pathlib import Path
from .models import ProductInput, MissingData, KeyCharacteristic

PROFILES = json.loads(
    (Path(__file__).parents[1] / "config" / "expected_specs.json").read_text(encoding="utf8")
)


def profile(product: ProductInput) -> str:
    value = (product.name + " " + product.category).lower()
    if "манометр" in value:
        return "manometer"
    if "давлен" in value and "датчик" in value:
        return "pressure_sensor"
    if any(x in value for x in ("термометр", "термопар", "термопреобраз")):
        return "temperature"
    return "universal"


def norm(text: str) -> str:
    return re.sub(r"[^а-яa-z0-9]", "", text.lower())


def assess(product: ProductInput) -> list[MissingData]:
    found = " ".join(product.specs).lower()
    rules = PROFILES[profile(product)]
    result = []
    for severity in ("critical", "recommended"):
        for field in rules[severity]:
            if norm(field) not in norm(found):
                result.append(
                    MissingData(
                        field=field,
                        reason="В исходных данных значение не найдено",
                        severity=severity,
                    )
                )
    if not product.description.strip():
        result.append(
            MissingData(
                field="Техническое описание",
                reason="В фиде отсутствует описание",
                severity="recommended",
            )
        )
    return result


def characteristics(product: ProductInput) -> list[KeyCharacteristic]:
    return [KeyCharacteristic(name=k, value=v, source="specs") for k, v in product.specs.items()]

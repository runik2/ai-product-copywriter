from __future__ import annotations

from pydantic import ValidationError

from .checks import check
from .errors import ResultError
from .llm import complete
from .missing import assess, characteristics
from .models import Card, CommercialBlock, ProductInput, Validation

PROMPT_VERSION = "v2"
MAX_ATTEMPTS = 3


def deterministic(product: ProductInput) -> Card:
    missing = assess(product)
    status = "needs_clarification" if missing else "ok"
    return Card(
        product_name=product.name,
        source={"offer_id": product.offer_id, "url": product.url},
        status=status,
        missing_data=missing,
        key_characteristics=characteristics(product),
        seo_title="",
        seo_description="",
        search_queries=[],
        commercial_block=CommercialBlock(),
        validation=Validation(prompt_version=PROMPT_VERSION),
    )


def generate(product: ProductInput, dry_run: bool = False) -> Card:
    """Generate a card, retrying at most three times and keeping the best attempt."""
    base = deterministic(product)
    if not product.name or (not product.specs and not product.description):
        base.validation.warnings.append("llm_skipped: недостаточно исходных данных")
        return base
    if dry_run:
        return base
    payload = {
        "name": product.name,
        "manufacturer": product.manufacturer,
        "specs": product.specs,
        "description": product.description,
        "category": product.category,
        "missing_fields": [x.field for x in base.missing_data],
    }
    attempts: list[Card] = []
    for _ in range(MAX_ATTEMPTS):
        feedback = attempts[-1].validation.warnings if attempts else None
        data = complete(payload, feedback)
        if not isinstance(data, dict):
            raise ResultError("Модель вернула JSON, который не является объектом")
        data.update(
            {
                "product_name": product.name,
                "source": base.source,
                "status": base.status,
                "missing_data": [x.model_dump() for x in base.missing_data],
                "key_characteristics": [x.model_dump() for x in base.key_characteristics],
            }
        )
        try:
            card = Card.model_validate(data)
        except ValidationError as exc:
            raise ResultError(f"Модель вернула невалидную карточку: {exc}") from exc
        warnings = check(card, product)
        card.validation = Validation(
            title_length=len(card.seo_title),
            description_length=len(card.seo_description),
            prompt_version=PROMPT_VERSION,
            warnings=warnings,
        )
        attempts.append(card)
        if not warnings:
            break
    return min(attempts, key=lambda item: len(item.validation.warnings))

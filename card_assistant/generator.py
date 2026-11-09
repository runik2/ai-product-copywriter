from __future__ import annotations
from .models import ProductInput, Card, CommercialBlock, Validation
from .missing import assess, characteristics
from .checks import check
from .llm import complete


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
    )


def generate(product: ProductInput, dry_run: bool = False) -> Card:
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
    best: Card | None = None
    for _ in range(3):
        feedback = best.validation.warnings if best else None
        data = complete(payload, feedback)
        data.update(
            {
                "product_name": product.name,
                "source": base.source,
                "status": base.status,
                "missing_data": [x.model_dump() for x in base.missing_data],
                "key_characteristics": [x.model_dump() for x in base.key_characteristics],
            }
        )
        card = Card.model_validate(data)
        warnings = check(card, product)
        card.validation = Validation(
            title_length=len(card.seo_title),
            description_length=len(card.seo_description),
            prompt_version="v2",
            warnings=warnings,
        )
        if best is None or len(card.validation.warnings) < len(best.validation.warnings):
            best = card
        if not warnings:
            break
    assert best is not None
    return best

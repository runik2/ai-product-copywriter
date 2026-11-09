import pytest

from card_assistant.checks import check, numeric_pairs
from card_assistant.models import Card, CommercialBlock, ProductInput


def product() -> ProductInput:
    return ProductInput(
        name="Манометр X 1.6 МПа",
        manufacturer="Тест",
        specs={"Диапазон": "1,6 МПа", "Температура": "20 °C"},
        description="Подтвержденное описание.",
        offer_id="1",
        category="10",
    )


def card(description: str) -> Card:
    return Card(
        product_name="Манометр X 1.6 МПа",
        source={"offer_id": "1", "url": ""},
        status="ok",
        missing_data=[],
        seo_title="Манометр X",
        seo_description=description,
        key_characteristics=[],
        search_queries=[],
        commercial_block=CommercialBlock(),
    )


def unsupported(description: str) -> list[str]:
    return [
        warning
        for warning in check(card(description), product())
        if warning.startswith(("unsupported_number", "unsupported_claim"))
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Цена снижена.",
        "Цены указаны в рублях.",
        "Ценник на витрине.",
        "Ценовая политика.",
    ],
)
def test_price_word_forms_are_detected(text):
    assert any("unsupported_claim" in item for item in unsupported(text))


@pytest.mark.parametrize(
    "text",
    [
        "Центральная часть корпуса.",
        "Ценный прибор для лаборатории.",
        "Оценка точности приведена.",
        "Бесценный опыт.",
    ],
)
def test_price_false_positives_are_ignored(text):
    assert not any("unsupported_claim" in item for item in unsupported(text))


def test_percent_pair_is_detected():
    assert "unsupported_number_unit:10 %" in unsupported("Точность 10%.")


@pytest.mark.parametrize("text", ["Температура 60 °C.", "Температура 60℃."])
def test_celsius_pair_is_detected(text):
    assert "unsupported_number_unit:60 °c" in unsupported(text)


def test_supported_celsius_is_not_flagged():
    warnings = unsupported("Рабочая температура 20 °C.")
    assert not any(item.startswith("unsupported_number_unit") for item in warnings)


def test_foreign_number_and_temperature():
    warnings = unsupported("Значение 1.5 при 60 °C.")
    assert "unsupported_number:1.5" in warnings
    assert "unsupported_number_unit:60 °c" in warnings


def test_supported_values_are_not_flagged():
    assert unsupported("Диапазон 1.6 МПа, температура 20 °C.") == []


def test_volt_unit_is_not_parsed():
    assert numeric_pairs("Напряжение 5 В") == set()
    assert not any(
        item.startswith("unsupported_number_unit") for item in unsupported("Напряжение 5 В.")
    )


def test_risky_claim_is_detected():
    warnings = unsupported("Гарантия 2 года.")
    assert any(item.startswith("unsupported_claim") for item in warnings)

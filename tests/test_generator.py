import pytest

from card_assistant.errors import ResultError
from card_assistant.generator import generate
from card_assistant.models import ProductInput


def product() -> ProductInput:
    return ProductInput(
        name="Манометр X 1.6 МПа",
        manufacturer="Тест",
        specs={"Диапазон": "1,6 МПа", "Температура": "20 °C"},
        description="Подтвержденное описание.",
        offer_id="1",
    )


def response(description: str = "Т" * 800) -> dict:
    return {
        "seo_title": "Манометр X",
        "seo_description": description,
        "search_queries": ["Манометр X"],
        "commercial_block": {"suitable_for": [], "tasks_solved": [], "manager_notes": ""},
    }


def test_clean_response_uses_one_call_and_has_no_service_warnings(monkeypatch):
    calls = []

    def fake(*_args):
        calls.append(1)
        return response()

    monkeypatch.setattr("card_assistant.generator.complete", fake)
    result = generate(product())
    assert len(calls) == 1
    assert result.validation.warnings == []
    assert result.validation.prompt_version == "v2"
    assert not any("prompt_version" in item for item in result.validation.warnings)


def test_generator_returns_best_of_three_attempts(monkeypatch):
    variants = iter(
        [
            response("Т" * 800 + " 1.5 2.5"),
            response("Т" * 800 + " 1.5"),
            response("Т" * 800 + " 1.5 2.5 3.5"),
        ]
    )
    calls = []

    def fake(*_args):
        calls.append(1)
        return next(variants)

    monkeypatch.setattr("card_assistant.generator.complete", fake)
    result = generate(product())
    assert len(calls) == 3
    assert result.seo_description == "Т" * 800 + " 1.5"
    assert result.validation.warnings == ["unsupported_number:1.5"]


def test_generator_passes_warnings_back_as_feedback(monkeypatch):
    variants = iter([response("Т" * 800 + " 1.5"), response()])
    feedback: list[list[str] | None] = []

    def fake(_payload, warnings=None):
        feedback.append(warnings)
        return next(variants)

    monkeypatch.setattr("card_assistant.generator.complete", fake)
    result = generate(product())
    assert feedback[0] is None
    assert feedback[1] == ["unsupported_number:1.5"]
    assert result.validation.warnings == []


def test_invalid_card_result_is_validation_error(monkeypatch):
    monkeypatch.setattr(
        "card_assistant.generator.complete",
        lambda *_args: {"seo_title": "только заголовок"},
    )
    with pytest.raises(ResultError) as exc:
        generate(product())
    assert exc.value.exit_code == 5


def test_empty_specs_skip_llm(monkeypatch):
    def boom(*_args):
        raise AssertionError("LLM must not be called")

    monkeypatch.setattr("card_assistant.generator.complete", boom)
    result = generate(ProductInput(name="Прибор без данных"))
    assert "llm_skipped: недостаточно исходных данных" in result.validation.warnings
    assert result.validation.prompt_version == "v2"

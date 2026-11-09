from card_assistant.errors import ApiError
from card_assistant.models import Card, CommercialBlock, MissingData
from card_assistant.web import APP


def make_card() -> Card:
    return Card(
        product_name="Прибор",
        source={"offer_id": "1", "url": ""},
        status="needs_clarification",
        missing_data=[
            MissingData(field="Диапазон", reason="нет", severity="critical"),
            MissingData(field="Погрешность", reason="нет", severity="recommended"),
        ],
        seo_title="Прибор",
        seo_description="Описание",
        key_characteristics=[],
        search_queries=["Прибор"],
        commercial_block=CommercialBlock(manager_notes="Уточнить"),
        validation={
            "title_length": 6,
            "description_length": 8,
            "warnings": ["unsupported_number:1.5"],
        },
    )


def test_web_uses_blocks_copy_buttons_and_highlights(monkeypatch):
    monkeypatch.setattr("card_assistant.web.generate", lambda product: make_card())
    APP.testing = True
    response = APP.test_client().post("/", data={"data": '{"name":"Прибор"}'})
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "<pre" not in html.lower()
    assert html.count("Копировать") >= 7
    assert "missing-item critical" in html
    assert "missing-item recommended" in html
    assert "unsupported_number:1.5" in html
    assert "Скопировано" in html


def test_web_shows_api_error(monkeypatch):
    def fail(_product):
        raise ApiError("нет сети")

    monkeypatch.setattr("card_assistant.web.generate", fail)
    APP.testing = True
    response = APP.test_client().post("/", data={"data": '{"name":"Прибор"}'})
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "нет сети" in html
    assert "alert error" in html


def test_web_example_is_loaded_without_generation():
    APP.testing = True
    response = APP.test_client().post("/", data={"example": "1"})
    html = response.get_data(as_text=True)
    assert "Пример манометра" in html
    assert "Сгенерировать" in html

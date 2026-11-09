import json

import requests

from card_assistant.cli import main
from card_assistant.feed import enrich_from_page, fetch_page_jsonld, is_technical
from card_assistant.models import ProductInput


class FakePage:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_jsonld_text_gets_separators_and_ads_are_removed():
    data = {
        "description": (
            "<p>Поверхностный мини-термометр</p>"
            "<p>Привлекательная цена. Прибор оснащен наконечником. "
            "Диапазон -50 … +300 °C</p>"
        ),
        "additionalProperty": [
            {"name": "Популярные подборки", "value": "Термометры"},
            {"name": "Верхний предел измерений", "value": "300"},
            {"name": "Нижний предел измерений", "value": "-50"},
        ],
    }
    product = ProductInput(name="Термометр", url="https://example.test/1")
    enriched = enrich_from_page(product, data)
    assert "Привлекательная" not in enriched.description
    assert "термометрПривлекательная" not in enriched.description
    assert "Популярные подборки" not in enriched.specs
    assert enriched.specs["Верхний предел измерений"] == "300"
    assert enriched.specs["Диапазон измерений"] == "-50 … +300 °C"


def test_glued_words_are_split_at_string_boundaries():
    data = {
        "description": "Поверхностный мини-термометрПривлекательная цена.Прибор работает.",
        "additionalProperty": [],
    }
    enriched = enrich_from_page(ProductInput(name="Термометр", url="https://example.test/1"), data)
    assert (
        "термометр Привлекательная" in enriched.description or "термометр." in enriched.description
    )
    assert "Привлекательная цена" not in enriched.description


def test_fetch_page_jsonld_tolerates_control_characters(monkeypatch):
    raw = '{"@type":"Product","name":"X","description":"первая\tвторая"}'
    monkeypatch.setattr(
        "card_assistant.feed.requests.get",
        lambda *_args, **_kwargs: FakePage(f'<script type="application/ld+json">{raw}</script>'),
    )
    data = fetch_page_jsonld("https://example.test/1")
    assert data is not None
    assert data["description"] == "первая\tвторая"


def test_fetch_page_jsonld_returns_none_on_network_error(monkeypatch):
    def fail(*_args, **_kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr("card_assistant.feed.requests.get", fail)
    assert fetch_page_jsonld("https://example.test/1") is None


def test_nontechnical_fields_are_filtered():
    assert not is_technical("Популярные подборки")
    assert not is_technical("Цена")
    assert is_technical("Верхний предел измерений")


def test_feed_pick_enrich_applies_to_every_selected_product(monkeypatch, tmp_path):
    feed = tmp_path / "feed.xml"
    feed.write_text(
        """<?xml version="1.0"?><yml_catalog><shop><offers>
        <offer id="1"><name>Первый</name><url>https://example.test/1</url>
        <param name="Диапазон">1 МПа</param></offer>
        <offer id="2"><name>Второй</name><url>https://example.test/2</url>
        <param name="Диапазон">2 МПа</param></offer>
        </offers></shop></yml_catalog>""",
        encoding="utf8",
    )
    data = {
        "description": "Проверенное описание.",
        "additionalProperty": [{"name": "Предел", "value": "10"}],
    }
    monkeypatch.setattr("card_assistant.cli.fetch_page_jsonld", lambda _url: data)
    out = tmp_path / "out"
    assert (
        main(["feed", "pick", "--feed", str(feed), "--ids", "1,2", "--enrich", "--out", str(out)])
        == 0
    )
    assert (out / "raw" / "product_1.page.json").exists()
    assert (out / "raw" / "product_2.page.json").exists()
    first = json.loads((out / "product_1.json").read_text(encoding="utf8"))
    second = json.loads((out / "product_2.json").read_text(encoding="utf8"))
    assert first["description"] == "Проверенное описание"
    assert second["description"] == "Проверенное описание"
    assert first["specs"]["Предел"] == "10"
    assert second["specs"]["Предел"] == "10"

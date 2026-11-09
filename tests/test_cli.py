import json

from card_assistant.cli import main
from card_assistant.errors import ApiError
from card_assistant.models import Card, CommercialBlock, ProductInput


def make_card(name: str, warnings: list[str] | None = None, offer_id: str = "1") -> Card:
    return Card(
        product_name=name,
        source={"offer_id": offer_id, "url": ""},
        status="ok",
        missing_data=[],
        seo_title="Заголовок",
        seo_description="Описание",
        key_characteristics=[],
        search_queries=[],
        commercial_block=CommercialBlock(),
        validation={"title_length": 8, "description_length": 7, "warnings": warnings or []},
    )


def write_product(path, name: str, offer_id: str):
    path.write_text(
        json.dumps(
            {
                "name": name,
                "manufacturer": "Тест",
                "specs": {"Диапазон": "1 МПа"},
                "description": "Описание",
                "offer_id": offer_id,
            },
            ensure_ascii=False,
        ),
        encoding="utf8",
    )


def test_generate_continues_after_bad_input(monkeypatch, tmp_path):
    good = tmp_path / "good.json"
    bad = tmp_path / "bad.json"
    write_product(good, "Первый", "1")
    bad.write_text("{broken", encoding="utf8")
    monkeypatch.setattr(
        "card_assistant.cli.generate", lambda product, dry_run: make_card(product.name)
    )
    out = tmp_path / "out"
    code = main(["generate", str(good), str(bad), "--out", str(out), "--format", "json"])
    assert code == 2
    assert list(out.glob("*.json"))


def test_generate_returns_worst_api_code_and_keeps_success(monkeypatch, tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_product(first, "Первый", "1")
    write_product(second, "Второй", "2")

    def fake(product, dry_run):
        if product.name == "Первый":
            raise ApiError("нет сети")
        return make_card(product.name, offer_id=product.offer_id)

    monkeypatch.setattr("card_assistant.cli.generate", fake)
    out = tmp_path / "out"
    code = main(["generate", str(first), str(second), "--out", str(out), "--format", "json"])
    assert code == 4
    assert len(list(out.glob("*.json"))) == 1


def test_generate_returns_5_for_blocking_warning(monkeypatch, tmp_path):
    path = tmp_path / "one.json"
    write_product(path, "Первый", "1")
    monkeypatch.setattr(
        "card_assistant.cli.generate",
        lambda product, dry_run: make_card(
            product.name, warnings=["unsupported_number:1.5"], offer_id=product.offer_id
        ),
    )
    assert main(["generate", str(path), "--out", str(tmp_path), "--format", "json"]) == 5


def test_check_returns_5_for_blocking_warning(monkeypatch, tmp_path):
    path = tmp_path / "card.json"
    path.write_text(make_card("Первый").model_dump_json(), encoding="utf8")
    source = ProductInput(name="Первый", specs={"Диапазон": "1 МПа"}, offer_id="1")
    monkeypatch.setattr("card_assistant.cli._load_sources", lambda: [source])
    monkeypatch.setattr(
        "card_assistant.cli.check", lambda card, product: ["unsupported_claim:price"]
    )
    assert main(["check", str(tmp_path)]) == 5


def test_check_returns_0_for_length_warning_only(monkeypatch, tmp_path):
    path = tmp_path / "card.json"
    path.write_text(make_card("Первый").model_dump_json(), encoding="utf8")
    source = ProductInput(name="Первый", specs={"Диапазон": "1 МПа"}, offer_id="1")
    monkeypatch.setattr("card_assistant.cli._load_sources", lambda: [source])
    monkeypatch.setattr(
        "card_assistant.cli.check", lambda card, product: ["description_length_below_min"]
    )
    assert main(["check", str(tmp_path)]) == 0


def test_serve_dispatches_to_web(monkeypatch):
    called = {}
    monkeypatch.setattr(
        "card_assistant.web.main", lambda host, port: called.update(host=host, port=port)
    )
    assert main(["serve", "--host", "127.0.0.1", "--port", "5099"]) == 0
    assert called == {"host": "127.0.0.1", "port": 5099}

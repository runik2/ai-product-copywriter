from pathlib import Path

import pytest
from pydantic import ValidationError

from card_assistant.cli import product_file
from card_assistant.errors import InputError
from card_assistant.feed import clean_description, clean_text, parse, pick
from card_assistant.generator import generate
from card_assistant.models import ProductInput


def test_clean_description_keeps_sentence_boundaries():
    assert clean_description("<li>Один</li><li>Два</li>") == "Один. Два"


def test_clean_text_preserves_ellipsis():
    assert clean_text("ПРОМА (-50...+150)") == "ПРОМА (-50...+150)"


def test_parse_fixture():
    products = parse(Path("tests/fixtures/mini_feed.xml"))
    assert len(products) == 2


def test_pick_fixture():
    assert len(pick(parse(Path("tests/fixtures/mini_feed.xml")))) == 2


def test_empty_specs_dry_run_needs_clarification():
    result = generate(ProductInput(name="Прибор без данных"), dry_run=True)
    assert result.status == "needs_clarification"
    assert result.missing_data
    assert result.seo_title == ""


def test_empty_name_is_rejected():
    with pytest.raises(ValidationError):
        ProductInput(name=" ")


def test_wrong_types_are_rejected():
    with pytest.raises(ValidationError):
        ProductInput.model_validate({"name": 1, "manufacturer": [], "specs": "x"})


def test_broken_json_input_is_code_2(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf8")
    with pytest.raises(InputError) as exc:
        product_file(path)
    assert exc.value.exit_code == 2


def test_missing_name_in_json_is_code_2(tmp_path):
    path = tmp_path / "no_name.json"
    path.write_text('{"name": "", "specs": {}}', encoding="utf8")
    with pytest.raises(InputError) as exc:
        product_file(path)
    assert exc.value.exit_code == 2


def test_broken_xml_is_input_error(tmp_path):
    path = tmp_path / "bad.xml"
    path.write_text("<yml_catalog><shop><offers>", encoding="utf8")
    with pytest.raises(InputError):
        parse(path)

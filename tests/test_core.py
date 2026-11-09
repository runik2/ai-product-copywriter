from pathlib import Path
from card_assistant.feed import clean_html, parse, pick
from card_assistant.generator import generate
from card_assistant.models import ProductInput
def test_html_cleaning(): assert clean_html('<li>Один</li><li>Два</li>') == 'Один. Два'
def test_parse_and_pick():
    products=parse(Path('tests/fixtures/mini_feed.xml')); assert len(products)==2; assert products[0].specs['Диапазон измерений']=='0–1,6 МПа'; assert len(pick(products))==2
def test_dry_run_never_calls_llm():
    card=generate(ProductInput(name='X',manufacturer='Y',specs={'Тип оборудования':'модуль'}),dry_run=True); assert card.key_characteristics[0].value=='модуль'; assert card.seo_title==''

# AI Product Copywriter

Python MVP для создания честных черновиков B2B-карточек КИП. Главное правило: LLM не является источником технических фактов. Код строит характеристики из `specs` дословно, фиксирует отсутствующие поля и отклоняет неподтверждённые числа и рискованные заявления.

## Установка

Нужен Python 3.11+.

```bash
git clone https://github.com/runik2/ai-product-copywriter.git
cd ai-product-copywriter
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -e . pytest
Copy-Item .env.example .env
```

Для DeepSeek в `.env` задайте `OPENAI_API_KEY`, `OPENAI_MODEL=deepseek-flash` и `OPENAI_BASE_URL=https://api.deepseek.com`. Ключ не коммитится.

## Команды

```bash
# фид, потоковая загрузка в .gitignore-папку data/
python -m card_assistant feed fetch
# выбор двух приборов и преобразование в JSON
python -m card_assistant feed pick
# безопасный просмотр детерминированной части без API
python -m card_assistant generate examples/inputs/product_1.json examples/inputs/product_2.json --dry-run
# реальная генерация, JSON + Markdown
python -m card_assistant generate examples/inputs/product_1.json examples/inputs/product_2.json --out examples/outputs
# повторная проверка
python -m card_assistant check examples/outputs
# простая локальная форма: http://127.0.0.1:5000
python -m card_assistant.web
# тесты
pytest -q
```

## Как устроена защита от выдумок

1. `feed.py` очищает HTML и исключает цену/наличие из payload LLM.
2. `missing.py` строит `key_characteristics` из входных `specs` и создаёт `missing_data` по профилю прибора.
3. `prompts/system_ru.md` запрещает использовать знания вне JSON и защищает от инструкций в описании товара.
4. `checks.py` проверяет длины, все числа, рискованные утверждения и всегда запрещает обещания о цене, доставке, наличии и гарантии.
5. При замечаниях LLM получает до двух попыток исправления; предупреждения остаются в результате.

## Результат

Для каждой карточки создаётся JSON и Markdown с заголовком, описанием и счётчиками длины, таблицей характеристик, поисковыми запросами, commercial-блоком, списком уточнений и предупреждений. См. `docs/DECISIONS.md`, `docs/PRODUCT_SELECTION.md` и текст ответа работодателю в `docs/cover_message.md`.

## Ограничения

Это локальный MVP без CMS, БД и деплоя. Качество текста зависит от полноты фида; если фактов недостаточно, описание может быть короче 800 символов с явным предупреждением. Дальнейшие улучшения перечислены в `docs/DECISIONS.md`.

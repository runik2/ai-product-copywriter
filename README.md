# AI Product Copywriter

Python MVP для честных черновиков B2B-карточек КИП. Главное правило: LLM не является
источником технических фактов. Код строит характеристики из `specs` дословно, фиксирует
отсутствующие поля и отклоняет неподтверждённые числа и рискованные заявления.

## Что внутри

- `feed` — потоковый разбор YML, выбор двух товаров, явное обогащение из JSON-LD страницы.
- `generate` — до трёх попыток генерации, обратная связь по предупреждениям, лучшая попытка.
- `check` — повторная детерминированная проверка готовых JSON.
- `serve` — локальная веб-форма с отдельными блоками результата и копированием.
- `checks` — числа, единицы, цены и другие рискованные утверждения.
- `missing` — профили КИП и список `missing_data`.

## Установка

Нужен Python 3.11+.

### Windows PowerShell

```powershell
git clone https://github.com/runik2/ai-product-copywriter.git
cd ai-product-copywriter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

### Linux / macOS / bash

```bash
git clone https://github.com/runik2/ai-product-copywriter.git
cd ai-product-copywriter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
cp .env.example .env
```

В `.env` заполните `OPENAI_API_KEY`, `OPENAI_MODEL` и `OPENAI_BASE_URL`. Для DeepSeek:
`OPENAI_MODEL=deepseek-flash`, `OPENAI_BASE_URL=https://api.deepseek.com`. Файл `.env`
уже в `.gitignore`; ключ нельзя коммитить или печатать в отчётах.

## Команды

```bash
# скачать фид потоком в data/ (папка в .gitignore)
python -m card_assistant feed fetch

# выбрать два товара, обогатить каждый из JSON-LD и сохранить исходные блоки
python -m card_assistant feed pick --feed data/feed.xml --ids 73083,371262 --enrich

# безопасный просмотр без API
python -m card_assistant generate examples/inputs/product_1.json examples/inputs/product_2.json --dry-run

# реальная генерация, JSON + Markdown
python -m card_assistant generate examples/inputs/product_1.json examples/inputs/product_2.json --out examples/outputs

# повторная проверка (0 — ок)
python -m card_assistant check examples/outputs

# локальная форма: http://127.0.0.1:5000
python -m card_assistant serve
```

`feed pick --enrich` не привязан к первому товару: JSON-LD запрашивается для каждого
выбранного оффера, а исходный блок сохраняется в `examples/inputs/raw/product_N.page.json`.
Без флага обогащения нет — остаются только поля YML.

Имена результатов: `{offer_id}_{ascii-slug}.json` и `.md`, например
`73083_testo-mini-termometr.md`. Slug транслитерируется из названия.

## Коды возврата

| Код | Значение |
|---|---|
| 0 | Успех; для `generate` — нет блокирующих предупреждений |
| 2 | Ошибка входных данных (битый JSON/XML, нет `name`, не найден товар) |
| 3 | Ошибка конфигурации (нет ключа или модели) |
| 4 | Ошибка API, сети или прокси |
| 5 | Результат не прошёл проверку (невалидный ответ модели или блокирующие warnings) |

`generate` обрабатывает товары независимо: ошибка одного не прерывает остальные, статус
печатается по каждому, итоговый код — худший из кодов. Предупреждения о длине описания
(`description_length_*`) остаются в JSON, но не блокируют публикацию: честный короткий
текст важнее добивания до 800 символов выдумками.

## Проверки

```bash
pytest -q
ruff check .
ruff format --check .
```

Тесты не обращаются к реальному API: HTTP, время и LLM замокированы. Покрыты ложные
срабатывания «цен», чужие числа `1.5` и `60 °C`, проценты, `℃`, ретраи 429/5xx/таймаутов,
401/400/403 без ретраев, невалидный JSON, prompt injection, битый вход, пустые `specs`
и отсутствие `name`.

## Troubleshooting

**401 / «Неверный API-ключ».** Проверьте `OPENAI_API_KEY` в `.env` в корне проекта.
Ключ не печатайте; после правки перезапустите команду. Если ключ передан в другом
окружении, `python-dotenv` не перезапишет уже заданную переменную.

**400/404 / «Неверная модель или endpoint».** Сверьте `OPENAI_MODEL` с доступными именами
провайдера. Для DeepSeek используйте `deepseek-flash`, для OpenAI — актуальное имя модели.
`OPENAI_BASE_URL` указывается без `/chat/completions`: код сам добавляет этот путь.
Для DeepSeek рабочий вариант — `https://api.deepseek.com` (не `/v1`).

**Нет доступа к сети/прокси, 403.** Проверьте `HTTPS_PROXY`/`HTTP_PROXY`, доступ к домену
провайдера и права ключа. Код не повторяет 401/403 и не маскирует их под сетевую ошибку.

**Описание короче 800 символов.** Это ожидаемо для скудного фида. В `validation.warnings`
будет `description_length_below_min`, а в `missing_data` — чего не хватает. Не добавляйте
недостающие факты в промпт вручную: лучше дополните фид или страницу товара.

**`feed pick` не нашёл ровно два товара.** Проверьте `--ids`; для выбора другого набора
используйте id из фида. В репозитории лежит только компактная тестовая фикстура, полный
фид не коммитится.

## Ограничения

Это локальный MVP без CMS, БД и деплоя. Качество зависит от полноты фида и страницы;
JSON-LD может описывать группу товаров, а не конкретный вариант. LLM недетерминирован,
поэтому примеры в `examples/outputs` — снимок реального прогона, а не эталон на каждый
запуск. Подробности решений и улучшений — в `docs/DECISIONS.md`, выбор товаров — в
`docs/PRODUCT_SELECTION.md`.

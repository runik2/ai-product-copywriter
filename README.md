# AI Product Copywriter

Локальный MVP для подготовки черновика B2B-карточки контрольно-измерительного оборудования. Решение получает два товара из YML-фида СОЮЗ-ПРИБОР или из входного JSON, передаёт данные в OpenAI и возвращает готовый для контент-менеджера результат в JSON и Markdown.

## Требования задания: покрытие

| Требование | Реализация |
|---|---|
| Входной JSON | `--input examples/input-products.json` |
| Два товара из фида | запуск без `--input` загружает первые два доступных предложения YML |
| LLM API | OpenAI Chat Completions, JSON mode, retry с экспоненциальной задержкой |
| Результат | `seoTitle`, `seoDescription`, `specs`, `searchQueries`, `commercialBlock`, `missingFields` |
| JSON и Markdown | `products.json`, `products.md` |
| Недостающие данные | поле `missingFields` и метка «Данных нет» |
| Защита от выдуманных характеристик | строгий промпт и программная сверка характеристик с исходным JSON |
| Ошибки и невалидный JSON | понятное сообщение, ненулевой код выхода, проверка входа и ответа LLM |
| API-ключ | только в `.env`, файл игнорируется Git |

## Быстрый запуск

Требуется Node.js 20+; внешние npm-зависимости не нужны.

```bash
git clone https://github.com/runik2/ai-product-copywriter.git
cd ai-product-copywriter
cp .env.example .env
npm test
npm run lint
```

В PowerShell вместо `cp` используйте `Copy-Item .env.example .env`.

### Демо без ключа

```bash
npm run generate -- --input examples/input-products.json --demo
```

### Генерация через OpenAI

Добавьте в `.env` ключ, который не должен попадать в Git:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Затем запустите один из вариантов:

```bash
# Взять два актуальных доступных товара из YML-фида
npm run generate

# Использовать собственный JSON
npm run generate -- --input examples/input-products.json
```

Результат будет в `output/products.json` и `output/products.md`. Опция `--output путь` задаёт другую папку. Полный пример для двух реальных товаров находится в [examples/generated](examples/generated).

## Формат входа

Входной файл может быть массивом или объектом с `products`. Минимально обязательны `name` и `manufacturer`; `specs` и `description` допустимо передать как «Данных нет» — тогда это будет отражено в результате.

```json
{
  "products": [{
    "name": "МК110-224.8Д.4Р [М01]",
    "manufacturer": "ОВЕН",
    "specs": {"Артикул": "58953"},
    "description": "Данных нет",
    "sourceUrl": "https://www.souz-pribor.ru/product/mk110-8d-4r/"
  }]
}
```

## Промпт и принятые решения

System prompt требует вернуть чистый JSON, ограничивает SEO-заголовок 70 символами и описание 800-1200 символами, запрещает добавлять непереданные характеристики и предписывает помечать пробелы в данных. После ответа LLM проект дополнительно проверяет формат, длины, 3-5 поисковых запросов, структуру commercial-блока и совпадение всех технических параметров с входом. Это делает контроль качества независимым от одного лишь промпта.

## Архитектура

- `src/feed.js` — загрузка, разбор и фильтрация доступных предложений YML;
- `src/cli.js` — CLI, JSON-ввод, обработка ошибок и файловый вывод;
- `src/generator.js` — prompt, OpenAI API, retry и demo mode;
- `src/schema.js` — нормализация, валидация и source-fidelity check;
- `src/format.js` — Markdown для копирования контент-менеджером;
- `examples/` — входные данные и пример результата для двух товаров.

## Ограничения и дальнейшее развитие

Это локальный прототип, без CMS, БД и деплоя — в соответствии с заданием. В production стоит добавить JSON Schema, rate limiting по кодам ответа, кэширование, логирование, ручное подтверждение контент-менеджером и пакетную обработку каталога. Фид содержит ограниченный набор характеристик; решение честно фиксирует такие пробелы вместо их генерации.

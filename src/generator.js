import { NO_DATA, normalizeProduct, validateBatch, validateSourceFidelity } from './schema.js';

const systemPrompt = `Ты senior SEO-копирайтер B2B-магазина контрольно-измерительных приборов. Верни только валидный JSON, без markdown. Технические характеристики разрешено брать ТОЛЬКО из входных данных: ничего не выдумывай. Отсутствующее значение обозначай строкой «Данных нет», а его имя добавляй в missingFields. Для каждого товара верни: name, manufacturer, specs, seoTitle (до 70 символов), seoDescription (800-1200 русских символов), searchQueries (3-5 строк), commercialBlock {suitableFor, solvesTasks, cta}, missingFields. SEO-текст может объяснять назначение только если оно дано во входе; не приписывай точность, диапазон, степень защиты, интерфейсы и совместимость без источника.`;

function prompt(products) { return `${systemPrompt}\n\nВходные данные:\n${JSON.stringify(products.map(normalizeProduct), null, 2)}\n\nСтрогий формат: {"products":[...]}.`; }

export async function generateWithOpenAI(products, { apiKey, model = 'gpt-4o-mini', retries = 2 } = {}) {
  if (!apiKey) throw new Error('OPENAI_API_KEY is not set. Add it to .env or use --demo.');
  let lastError;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', { method: 'POST', headers: { 'content-type': 'application/json', authorization: `Bearer ${apiKey}` }, body: JSON.stringify({ model, temperature: 0.2, response_format: { type: 'json_object' }, messages: [{ role: 'system', content: systemPrompt }, { role: 'user', content: prompt(products) }] }) });
      if (!response.ok) throw new Error(`OpenAI API error ${response.status}: ${await response.text()}`);
      const data = await response.json(); const content = data.choices?.[0]?.message?.content;
      if (!content) throw new Error('OpenAI returned an empty response');
      let result; try { result = JSON.parse(content); } catch { throw new Error('OpenAI returned invalid JSON'); }
      const errors = [...validateBatch(result), ...validateSourceFidelity(products, result)]; if (errors.length) throw new Error(`LLM output validation failed: ${errors.join('; ')}`);
      return result;
    } catch (error) { lastError = error; if (attempt < retries) await new Promise(resolve => setTimeout(resolve, 500 * 2 ** attempt)); }
  } throw lastError;
}

function demoDescription(product) {
  return `${product.name} — позиция каталога для задач промышленной автоматизации. Производитель: ${product.manufacturer}. В исходных данных указано назначение: ${product.specs['Тип оборудования'] || NO_DATA}. При подборе оборудования важно сопоставить задачу проекта с паспортом изделия, схемой подключения, условиями эксплуатации и требованиями к действующей системе. В доступных данных отсутствуют часть технических сведений, поэтому этот черновик не заменяет документацию производителя и не содержит неподтверждённых параметров. Менеджер СОЮЗ-ПРИБОР поможет запросить актуальную спецификацию, проверить наличие, цену, срок поставки и подобрать комплектующие при наличии подтверждённой совместимости. Перед оформлением заказа рекомендуем уточнить модель, артикул и комплектацию. Такой подход помогает подготовить корректную карточку товара без риска указать неточную характеристику, а также быстро получить коммерческое предложение для закупки.`;
}

export function demoContent(products) {
  return { products: products.map(raw => { const p = normalizeProduct(raw); const type = p.specs['Тип оборудования'] || p.specs['Тип'] || 'оборудование'; return { name: p.name, manufacturer: p.manufacturer, specs: p.specs, seoTitle: `${p.name} ${p.manufacturer} — купить в СОЮЗ-ПРИБОР`.slice(0, 70), seoDescription: demoDescription(p), searchQueries: [`${p.name} купить`, `${type} ${p.manufacturer}`, `${p.name} цена`], commercialBlock: { suitableFor: `Подходит специалистам, которые подбирают ${type} для промышленного проекта.`, solvesTasks: `Помогает рассмотреть решение для задачи, указанной во входных данных: ${type}.`, cta: 'Запросите актуальную цену, наличие и техническую документацию у менеджера СОЮЗ-ПРИБОР.' }, missingFields: p.missingFields }; }) };
}

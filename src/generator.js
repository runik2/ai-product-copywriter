import { validateBatch } from './schema.js';

const systemPrompt = `Ты senior SEO-копирайтер для B2B-магазина промышленной автоматизации. Верни только валидный JSON без markdown-обёртки. Не выдумывай технические параметры: используй только данные товара, а если информации мало — формулируй аккуратно и явно не обещай неподтверждённые характеристики. Для каждого товара: name, manufacturer, specs (объект), seoTitle (до 70 символов), description (800-1200 русских символов), benefits (3-5 пунктов), commercialCta.`;

function prompt(products) { return `${systemPrompt}\n\nТовары:\n${JSON.stringify(products, null, 2)}\n\nФормат ответа: {"products":[...]}\nПроверь длину seoTitle и description перед ответом.`; }

export async function generateWithOpenAI(products, { apiKey, model = 'gpt-4o-mini', retries = 2 } = {}) {
  if (!apiKey) throw new Error('OPENAI_API_KEY is not set');
  let lastError;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', { method: 'POST', headers: { 'content-type': 'application/json', authorization: `Bearer ${apiKey}` }, body: JSON.stringify({ model, temperature: 0.35, response_format: { type: 'json_object' }, messages: [{ role: 'system', content: systemPrompt }, { role: 'user', content: prompt(products) }] }) });
      if (!response.ok) throw new Error(`OpenAI request failed: ${response.status} ${await response.text()}`);
      const data = await response.json();
      const result = JSON.parse(data.choices?.[0]?.message?.content || '{}');
      const errors = validateBatch(result);
      if (errors.length) throw new Error(`LLM output validation failed: ${errors.join('; ')}`);
      return result;
    } catch (error) { lastError = error; if (attempt < retries) await new Promise(r => setTimeout(r, 500 * 2 ** attempt)); }
  }
  throw lastError;
}

export function demoContent(products) {
  return { products: products.map(p => ({ name: p.name, manufacturer: p.vendor || 'Не указан', specs: { 'Тип': p.typePrefix || 'Промышленное устройство', 'Артикул': p.vendorCode || p.params['Артикул'] || 'Не указан', 'Цена': p.price ? `${p.price} ${p.currency || 'RUB'}` : 'По запросу' }, seoTitle: `${p.name} — купить в СОЮЗ-ПРИБОР`, description: `Оборудование ${p.name} от ${p.vendor || 'производителя'} для задач промышленной автоматизации. Товар представлен в каталоге СОЮЗ-ПРИБОР и подходит для применения на производственных объектах, в системах контроля, измерения и управления. Перед заказом рекомендуем сверить назначение устройства, требования к монтажу, условия эксплуатации и совместимость с вашей системой. Специалисты компании помогут подобрать решение под проект, уточнить наличие, стоимость, сроки поставки и необходимые комплектующие. Карточка товара содержит основные сведения, а подробные технические параметры и документацию можно запросить у менеджера. Оформите заявку на сайте, чтобы получить консультацию и коммерческое предложение по вашему проекту.`, benefits: ['Оригинальная продукция промышленного назначения', 'Консультация специалистов по подбору', 'Поставка и сопровождение заказа'], commercialCta: 'Запросите цену и срок поставки у специалиста СОЮЗ-ПРИБОР.' })) };
}

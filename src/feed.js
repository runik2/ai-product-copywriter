const decode = (value) => value
  .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
  .replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&lt;/g, '<')
  .replace(/&gt;/g, '>').replace(/&#39;/g, "'").trim();

const tag = (xml, name) => {
  const match = xml.match(new RegExp(`<${name}[^>]*>([\\s\\S]*?)</${name}>`, 'i'));
  return match ? decode(match[1]) : '';
};

const attr = (xml, name) => {
  const match = xml.match(new RegExp(`${name}="([^"]*)"`, 'i'));
  return match ? decode(match[1]) : '';
};

export function parseYml(xml, limit = 2) {
  const offers = [...xml.matchAll(/<offer\b[\s\S]*?<\/offer>/gi)].slice(0, limit);
  return offers.map(({ 0: offer }) => ({
    id: attr(offer, 'id'), available: attr(offer, 'available') !== 'false',
    name: tag(offer, 'name'), typePrefix: tag(offer, 'typePrefix'), url: tag(offer, 'url'),
    vendor: tag(offer, 'vendor'), vendorCode: tag(offer, 'vendorCode'), picture: tag(offer, 'picture'),
    price: Number(tag(offer, 'price')) || null, currency: tag(offer, 'currencyId'),
    params: Object.fromEntries([...offer.matchAll(/<param\s+name="([^"]*)">([\s\S]*?)<\/param>/gi)].map(m => [decode(m[1]), decode(m[2])]))
  }));
}

export async function loadProducts(url, limit = 2) {
  const response = await fetch(url, { headers: { 'user-agent': 'AI-Product-Copywriter/1.0' } });
  if (!response.ok) throw new Error(`Feed request failed: ${response.status} ${response.statusText}`);
  const products = parseYml(await response.text(), limit);
  if (products.length < limit) throw new Error(`Feed contains only ${products.length} products`);
  return products;
}

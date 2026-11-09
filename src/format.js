export function toMarkdown(result) {
  return ['# SEO-контент товаров', '', ...result.products.flatMap(p => [`## ${p.name}`, '', `**SEO-заголовок:** ${p.seoTitle}`, '', `**Производитель:** ${p.manufacturer}`, '', '**Характеристики:**', ...Object.entries(p.specs).map(([k, v]) => `- **${k}:** ${v}`), '', '**Описание:**', p.description, '', '**Преимущества:**', ...p.benefits.map(x => `- ${x}`), '', `**Призыв к действию:** ${p.commercialCta}`, ''])].join('\n');
}

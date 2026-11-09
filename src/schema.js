export function validateProductContent(value) {
  const errors = [];
  if (!value || typeof value !== 'object') return ['Response must be an object'];
  for (const key of ['name', 'manufacturer', 'seoTitle', 'description', 'commercialCta']) {
    if (typeof value[key] !== 'string' || !value[key].trim()) errors.push(`${key} must be a non-empty string`);
  }
  if (value.seoTitle?.length > 70) errors.push(`seoTitle is ${value.seoTitle.length} chars; maximum is 70`);
  if (!Array.isArray(value.benefits) || value.benefits.length < 3 || value.benefits.length > 5) errors.push('benefits must contain 3-5 items');
  if (!value.specs || typeof value.specs !== 'object' || Array.isArray(value.specs)) errors.push('specs must be an object');
  if (value.description && (value.description.length < 800 || value.description.length > 1200)) errors.push(`description must be 800-1200 chars; got ${value.description.length}`);
  return errors;
}

export function validateBatch(value) {
  if (!value || !Array.isArray(value.products)) return ['products must be an array'];
  return value.products.flatMap((product, i) => validateProductContent(product).map(error => `products[${i}]: ${error}`));
}

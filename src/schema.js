export const NO_DATA = 'Данных нет';

export function normalizeProduct(input) {
  const value = input && typeof input === 'object' ? input : {};
  const missingFields = [];
  const text = (field, fallback = NO_DATA) => {
    const v = typeof value[field] === 'string' ? value[field].trim() : '';
    if (!v || v === NO_DATA) missingFields.push(field);
    return v || fallback;
  };
  const specs = value.specs && typeof value.specs === 'object' && !Array.isArray(value.specs) ? value.specs : {};
  if (!Object.keys(specs).length) missingFields.push('specs');
  return { name: text('name'), manufacturer: text('manufacturer'), specs, description: text('description'), sourceUrl: typeof value.sourceUrl === 'string' ? value.sourceUrl : '', missingFields: [...new Set(missingFields)] };
}

export function validateInput(products) {
  if (!Array.isArray(products) || !products.length) return ['products must be a non-empty array'];
  return products.flatMap((product, i) => {
    if (!product || typeof product !== 'object' || Array.isArray(product)) return [`products[${i}] must be an object`];
    const errors = [];
    if (typeof product.name !== 'string' || !product.name.trim()) errors.push(`products[${i}].name is required`);
    if (typeof product.manufacturer !== 'string' || !product.manufacturer.trim()) errors.push(`products[${i}].manufacturer is required`);
    return errors;
  });
}

export function validateProductContent(value) {
  const errors = [];
  if (!value || typeof value !== 'object') return ['Response must be an object'];
  for (const key of ['name', 'manufacturer', 'seoTitle', 'seoDescription']) if (typeof value[key] !== 'string' || !value[key].trim()) errors.push(`${key} must be a non-empty string`);
  if (value.seoTitle?.length > 70) errors.push(`seoTitle is ${value.seoTitle.length} chars; maximum is 70`);
  if (value.seoDescription && (value.seoDescription.length < 800 || value.seoDescription.length > 1200)) errors.push(`seoDescription must be 800-1200 chars; got ${value.seoDescription.length}`);
  if (!value.specs || typeof value.specs !== 'object' || Array.isArray(value.specs)) errors.push('specs must be an object');
  if (!Array.isArray(value.searchQueries) || value.searchQueries.length < 3 || value.searchQueries.length > 5 || value.searchQueries.some(x => typeof x !== 'string' || !x.trim())) errors.push('searchQueries must contain 3-5 non-empty strings');
  if (!value.commercialBlock || typeof value.commercialBlock !== 'object') errors.push('commercialBlock must be an object');
  else for (const key of ['suitableFor', 'solvesTasks', 'cta']) if (typeof value.commercialBlock[key] !== 'string' || !value.commercialBlock[key].trim()) errors.push(`commercialBlock.${key} must be a non-empty string`);
  if (!Array.isArray(value.missingFields)) errors.push('missingFields must be an array');
  return errors;
}

export function validateBatch(value) {
  if (!value || !Array.isArray(value.products)) return ['products must be an array'];
  return value.products.flatMap((product, i) => validateProductContent(product).map(error => `products[${i}]: ${error}`));
}

export function validateSourceFidelity(input, result) {
  const source = input.map(normalizeProduct);
  if (source.length !== result.products.length) return ['LLM changed the number of products'];
  return result.products.flatMap((product, index) => {
    const expected = source[index]; const errors = [];
    if (product.name !== expected.name) errors.push(`products[${index}]: name differs from input`);
    if (product.manufacturer !== expected.manufacturer) errors.push(`products[${index}]: manufacturer differs from input`);
    for (const [key, value] of Object.entries(product.specs)) if (expected.specs[key] !== value) errors.push(`products[${index}]: unsupported specification ${key}`);
    for (const field of expected.missingFields) if (!product.missingFields.includes(field)) errors.push(`products[${index}]: missingFields omits ${field}`);
    return errors;
  });
}

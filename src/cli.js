import { existsSync, readFileSync } from 'node:fs';
import { mkdir, writeFile } from 'node:fs/promises';
import process from 'node:process';
import { loadProducts } from './feed.js';
import { toMarkdown } from './format.js';
import { demoContent, generateWithOpenAI } from './generator.js';
import { validateInput } from './schema.js';

function readEnv() {
  if (!existsSync('.env')) return {};
  return Object.fromEntries(readFileSync('.env', 'utf8').split(/\r?\n/).filter(line => line && !line.trimStart().startsWith('#')).map(line => { const i = line.indexOf('='); return [line.slice(0, i), line.slice(i + 1)]; }));
}
function arg(name) { const i = process.argv.indexOf(name); return i >= 0 ? process.argv[i + 1] : undefined; }
function help() { console.log('Usage: npm run generate -- [--input examples/input-products.json] [--demo] [--output output]'); }
function toInputProduct(product) { return { name: product.name, manufacturer: product.vendor || 'Данных нет', specs: { 'Тип оборудования': product.typePrefix || 'Данных нет', ...product.params }, description: 'Данных нет', sourceUrl: product.url }; }

async function main() {
  if (process.argv.includes('--help')) return help();
  const env = readEnv(); const inputPath = arg('--input'); const output = arg('--output') || env.OUTPUT_DIR || process.env.OUTPUT_DIR || 'output';
  const config = { feed: env.FEED_URL || process.env.FEED_URL || 'https://www.souz-pribor.ru/yml/any/feed.xml', apiKey: env.OPENAI_API_KEY || process.env.OPENAI_API_KEY, model: env.OPENAI_MODEL || process.env.OPENAI_MODEL || 'gpt-4o-mini' };
  let products;
  if (inputPath) { let parsed; try { parsed = JSON.parse(readFileSync(inputPath, 'utf8')); } catch (error) { throw new Error(`Invalid input JSON (${inputPath}): ${error.message}`); } products = Array.isArray(parsed) ? parsed : parsed.products; }
  else products = (await loadProducts(config.feed, 2)).map(toInputProduct);
  const inputErrors = validateInput(products); if (inputErrors.length) throw new Error(`Input validation failed: ${inputErrors.join('; ')}`);
  const demo = process.argv.includes('--demo') || !config.apiKey; const result = demo ? demoContent(products) : await generateWithOpenAI(products, config);
  await mkdir(output, { recursive: true }); const meta = { generatedAt: new Date().toISOString(), mode: demo ? 'demo' : 'openai', source: inputPath || config.feed, products: result.products };
  await writeFile(`${output}/products.json`, JSON.stringify(meta, null, 2), 'utf8'); await writeFile(`${output}/products.md`, toMarkdown(result), 'utf8');
  console.log(`Generated ${result.products.length} cards in ${output}/ (${demo ? 'demo mode' : `OpenAI: ${config.model}`}).`);
}
main().catch(error => { console.error(`Error: ${error.message}`); process.exitCode = 1; });

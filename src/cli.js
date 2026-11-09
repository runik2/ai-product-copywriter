import 'node:process';
import { mkdir, writeFile } from 'node:fs/promises';
import { existsSync, readFileSync } from 'node:fs';
import { loadProducts } from './feed.js';
import { demoContent, generateWithOpenAI } from './generator.js';
import { toMarkdown } from './format.js';

const env = existsSync('.env') ? Object.fromEntries(readFileSync('.env', 'utf8').split(/\r?\n/).filter(x => x && !x.startsWith('#')).map(x => { const i=x.indexOf('='); return [x.slice(0,i), x.slice(i+1)]; })) : {};
const config = { feed: env.FEED_URL || process.env.FEED_URL || 'https://www.souz-pribor.ru/yml/any/feed.xml', output: env.OUTPUT_DIR || 'output', apiKey: env.OPENAI_API_KEY || process.env.OPENAI_API_KEY, model: env.OPENAI_MODEL || process.env.OPENAI_MODEL || 'gpt-4o-mini' };
const products = await loadProducts(config.feed, 2);
const result = config.apiKey ? await generateWithOpenAI(products, config) : demoContent(products);
await mkdir(config.output, { recursive: true });
await writeFile(`${config.output}/products.json`, JSON.stringify({ generatedAt: new Date().toISOString(), source: config.feed, products: result.products }, null, 2));
await writeFile(`${config.output}/products.md`, toMarkdown(result));
console.log(`Generated ${result.products.length} products in ${config.output}/` + (config.apiKey ? ' (LLM mode)' : ' (demo mode; set OPENAI_API_KEY for LLM mode)'));

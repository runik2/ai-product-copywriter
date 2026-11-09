import test from 'node:test';
import assert from 'node:assert/strict';
import { parseYml } from '../src/feed.js';
import { demoContent } from '../src/generator.js';
import { normalizeProduct, validateBatch, validateInput } from '../src/schema.js';
test('parses YML offers and parameters', () => { const [p] = parseYml('<offer id="1"><name>A &amp; B</name><vendor>ACME</vendor><param name="Артикул">42</param></offer>'); assert.equal(p.name, 'A & B'); assert.equal(p.params['Артикул'], '42'); });
test('reports missing nontechnical input fields explicitly', () => { const p = normalizeProduct({ name: 'X', manufacturer: 'Y', specs: {} }); assert.deepEqual(p.missingFields.sort(), ['description', 'specs']); });
test('rejects malformed input JSON shape', () => { assert.ok(validateInput([{ manufacturer: 'Y' }]).length); });
test('demo output fulfils the required output contract', () => { const result = demoContent([{ name: 'X', manufacturer: 'Y', specs: { 'Тип оборудования': 'модуль' }, description: 'Данных нет' }]); assert.deepEqual(validateBatch(result), []); });

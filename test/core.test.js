import test from 'node:test';
import assert from 'node:assert/strict';
import { parseYml } from '../src/feed.js';
import { validateProductContent } from '../src/schema.js';

test('parses YML offers and parameters', () => { const [p] = parseYml('<offer id="1"><name>A &amp; B</name><vendor>ACME</vendor><param name="Артикул">42</param></offer>'); assert.equal(p.name, 'A & B'); assert.equal(p.params['Артикул'], '42'); });
test('rejects malformed content', () => { assert.ok(validateProductContent({ seoTitle: 'x' }).length > 0); });

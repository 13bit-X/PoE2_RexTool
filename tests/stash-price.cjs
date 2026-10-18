// Run: node tests/stash-price.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '..', 'PoE2_RexTool.html'), 'utf8');
const context = vm.createContext({ window: {} });
for (const [, script] of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
  new vm.Script(script); // Also syntax-check UI scripts without a fake DOM.
  if (script.includes('window.POE2_PRICE =') || script.includes('root.POE2_REGEX =')) vm.runInContext(script, context);
}
const P = context.window.POE2_PRICE;
assert.equal(context.window.POE2_REGEX.selfTest().ok, true);
const compile = (min, max, extra = {}) => P.compile({ min: String(min), max: String(max), mode: 'between', currency: 'exalted', ...extra });
const pattern = result => new RegExp(result.source.slice(1, -1));
let checks = 0;
// Exhaustive small ranges catch factoring and digit-boundary errors.
for (let lo = 1; lo <= 99; lo++) {
  for (let hi = lo; hi <= 105; hi++) {
    const result = compile(lo, hi), re = pattern(result);
    assert.equal(result.error, '');
    for (let n = 0; n <= 125; n++) {
      assert.equal(re.test(`~b/o ${n} exalted`), n >= lo && n <= hi, `${lo}..${hi}, ${n}: ${result.source}`);
      checks++;
    }
  }
}
// Deterministic larger samples cross powers of ten and the old affix 999 cap.
let seed = 918273;
function random() { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed; }
for (let i = 0; i < 300; i++) {
  const lo = random() % 1000000 + 1, hi = lo + random() % 1000000;
  const result = compile(lo, hi), re = pattern(result);
  for (const n of [0, 1, lo - 1, lo, lo + 1, hi - 1, hi, hi + 1, hi * 10, random() % 3000000]) {
    assert.equal(re.test(`~b/o ${n} exalted`), n >= lo && n <= hi, `${lo}..${hi}, ${n}: ${result.source}`);
    checks++;
  }
}
for (const lo of [1, 2, 9, 10, 19, 99, 100, 999, 1000, 10001, Number.MAX_SAFE_INTEGER]) {
  const result = compile(lo, '', { mode: 'min' }), re = pattern(result);
  for (const n of [0n, BigInt(lo) - 1n, BigInt(lo), BigInt(lo) + 1n, 10n ** 40n]) {
    assert.equal(re.test(`~b/o ${n} exalted`), n >= BigInt(lo), `at least ${lo}, ${n}: ${result.source}`);
    checks++;
  }
}
for (const hi of [1, 2, 10, 99, 1000, Number.MAX_SAFE_INTEGER]) {
  const result = compile('', hi, { mode: 'max' }), re = pattern(result);
  for (const n of [0n, 1n, BigInt(hi), BigInt(hi) + 1n]) {
    assert.equal(re.test(`~b/o ${n} exalted`), n >= 1n && n <= BigInt(hi)); checks++;
  }
}
for (const value of ['0', '-1', '1.5', '1e3', 'NaN', 'Infinity', '1/10', '5x', '9007199254740992', '<img onerror=alert(1)>']) {
  assert.equal(compile(value, '10').error, 'integer', value);
  assert.equal(compile(value, '10').source, '');
}
assert.equal(compile('20', '10').error, 'order');
assert.equal(compile('', '').error, 'empty');
assert.equal(compile(' 001 ', '002').source, '"~b/o [12] ex"');
assert.equal(compile('bad', '2', { mode: 'max' }).error, '');
assert.equal(compile('2', 'bad', { mode: 'min' }).error, '');
const codes = { exalted: 'exalted', divine: 'divine', chaos: 'chaos' };
for (const currency of Object.keys(codes)) {
  const result = compile('1', '2', { currency }), re = pattern(result);
  assert.equal(result.length, result.source.length);
  assert.ok(!result.over);
  for (const other of Object.keys(codes)) assert.equal(re.test(`~b/o 1 ${codes[other]}`), other === currency);
  for (const bad of ['~price 1', '~b/o 0', '~b/o 10', '~b/o 11', '~b/o 100', '~b/o 1.0', '~b/o 1/2', '~b/o 01', '~b/o -1']) {
    assert.equal(re.test(`${bad} ${codes[currency]}`), false, `${bad} ${codes[currency]}`);
  }
}
assert.equal(compile('1', '2', { currency: 'divine' }).source, '"~b/o [12] div"');
assert.equal(compile('1', '2', { currency: 'divine' }).length, 15);
assert.equal(compile('1', '10').length, 20);
assert.ok(compile('10', '19').length < '"~b/o (10|11|12|13|14|15|16|17|18|19) ex"'.length);
const huge = compile('1234567890123456', '8765432109876543');
assert.equal(huge.over, huge.length > 250);
assert.ok(huge.over, 'Complex ranges must be flagged, never truncated or widened');
for (const n of [1234567890123455n, 1234567890123456n, 5555555555555555n, 8765432109876543n, 8765432109876544n]) {
  assert.equal(pattern(huge).test(`~b/o ${n} exalted`), n >= 1234567890123456n && n <= 8765432109876543n);
}
assert.equal(P.sanitize({ currency: '__proto__', mode: '<script>', min: '3' }).currency, 'exalted');
assert.equal(P.sanitize({ min: '9'.repeat(10000) }).min.length, 32);
console.log(`Price engine: ${checks} numeric comparisons passed; validation, currencies, length, syntax and existing affix self-test passed.`);

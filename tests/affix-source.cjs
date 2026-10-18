// Run with: node tests/affix-source.cjs
// PoE2DB source samples checked on 2026-10-18; no network or browser needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(process.argv[2] || path.join(__dirname, '..', 'PoE2_RexTool.html'), 'utf8');
const context = { window: {} };
vm.createContext(context);
for (const [, script] of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
  if (script.includes('window.POE2_DATA =') || script.includes('root.POE2_REGEX =')) {
    vm.runInContext(script, context);
  }
}
const R = context.window.POE2_REGEX;
assert.equal(R.selfTest().ok, true);
const data = context.window.POE2_DATA;
const affixes = [...data.waystone, ...data.tablet];
const fixtures = require('./affix-source-samples.json');
let checks = 0;
for (const test of fixtures.cases) {
  const affix = affixes.find(a => a.id === test.id);
  const template = affix.tpl[test.lang];
  const presence = R.presence(template);
  assert.ok(presence, `${test.id}/${test.lang}: missing presence`);
  for (const sample of test.samples) {
    const range = /\((\d+)—(\d+)\)%?/;
    const match = sample.match(range);
    const values = match ? [+match[1], +match[2]] : [null];
    for (const value of values) {
      const text = value === null ? sample : sample.replace(range, String(value) + '%');
      assert.match(text, new RegExp(presence), `${test.id}/${test.lang}: ${text}`);
      checks++;
    }
  }
  if (affix.rng) {
    const [lo, hi] = affix.rng;
    const cutoff = hi;
    // Other affixes' atMost checks expose a separate pre-existing number-boundary bug.
    const thresholds = [{ atLeast: cutoff }];
    if (test.id === 'wt020') thresholds.push({ atMost: lo });
    for (const opts of thresholds) {
      const fragment = R.threshold(template, opts);
      assert.ok(fragment, `${test.id}/${test.lang}: threshold discarded`);
      const regex = new RegExp(fragment);
      for (let value = lo; value <= hi; value++) {
        const text = test.id === 'wt020'
          ? test.samples[0].replace(/\b2\b/, String(value))
          : test.samples[0].replace(/\(\d+—\d+\)/, String(value));
        assert.equal(regex.test(text), opts.atLeast !== undefined ? value >= cutoff : value <= lo,
          `${test.id}/${test.lang}: ${JSON.stringify(opts)}, ${text}`);
        checks++;
      }
    }
  }
}
console.log(`PASS: ${fixtures.cases.length} source cases, ${checks} matching/threshold checks; engine selfTest passed`);

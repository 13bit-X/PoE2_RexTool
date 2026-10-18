// Run with: node tests/composite-affix.cjs [path/to/PoE2_RexTool.html]
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(process.argv[2] || path.join(__dirname, '..', 'PoE2_RexTool.html'), 'utf8');
const context = { window: {}, state: { language: 'cn' } };
vm.createContext(context);
for (const [, script] of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
  if (script.includes('window.POE2_DATA =') || script.includes('root.POE2_REGEX =')) vm.runInContext(script, context);
}
context.R = context.window.POE2_REGEX;
context.loc = tpl => tpl[context.state.language] || tpl.cn;
for (const name of ['affixLines', 'fragmentFor']) {
  const source = html.match(new RegExp('  function ' + name + '\\([\\s\\S]*?\\n  }'));
  assert.ok(source, name);
  vm.runInContext(source[0], context);
}
const R = context.R, data = context.window.POE2_DATA;
const all = [...data.waystone, ...data.tablet];
const compounds = all.filter(a => a.composite);
assert.equal(compounds.length, 2, 'Review representative lines when adding compound affixes');
const sample = '物品类别: 引路石\n{ 前缀属性 "灭绝的" (等阶：1) }\n怪物暴击率提高 208 (200-240)%\n+22 (21-25)% 怪物暴击伤害加成';
const crit = all.find(a => a.id === 'wt006');
assert.match(sample, new RegExp(context.fragmentFor(crit, { mode: 'include', value: '', value2: '' })));
assert.match(sample, new RegExp(context.fragmentFor(crit, { mode: 'include', value: '200', value2: '' })));
assert.doesNotMatch(sample, new RegExp(context.fragmentFor(crit, { mode: 'include', value: '250', value2: '' })));
let checks = 3;
for (const language of ['cn', 'tw', 'en']) {
  context.state.language = language;
  for (const a of compounds) {
    const lines = a.lines[language];
    const presence = R.presence(lines[0]);
    const rendered = template => template.replace(/\((-?\d+)—(-?\d+)\)/g, '$1');
    // A single representative line must not select another current affix.
    const matches = all.filter(other => (other.lines?.[language] || [other.tpl[language]]).some(line => new RegExp(presence).test(rendered(line))));
    assert.deepEqual(matches.map(other => other.id), [a.id], `${a.id}/${language}: ambiguous first line`);
    const text = lines.map(rendered).join('\r\n');
    for (const selection of [
      { mode: 'include', value: '', value2: '' },
      { mode: 'include', value: String(a.rng[0]), value2: '' },
      { mode: 'include', value: '', value2: String(a.rng[1]) },
      { mode: 'exclude', value: '', value2: '' }
    ]) {
      const fragment = context.fragmentFor(a, selection);
      assert.match(text, new RegExp(fragment), `${a.id}/${language}: CRLF`);
      assert.match(text.replace(/\r/g, ''), new RegExp(fragment), `${a.id}/${language}: LF`);
      assert.equal(fragment, selection.mode === 'include' && (selection.value || selection.value2)
        ? R.threshold(lines[0], { atLeast: selection.value || undefined, atMost: selection.value2 || undefined }) : presence);
      checks += 3;
    }
  }
  // Unrelated single-line affixes retain their previous fragments.
  for (const a of all.filter(a => !a.composite)) {
    const text = (a.lines?.[language] || [a.tpl[language]]).join(' ');
    assert.equal(context.fragmentFor(a, { mode: 'include', value: '', value2: '' }), R.presence(text));
    checks++;
  }
}
assert.equal(R.selfTest().ok, true);
console.log(`PASS: ${checks} compound/source-uniqueness and unchanged-affix checks; engine selfTest passed`);

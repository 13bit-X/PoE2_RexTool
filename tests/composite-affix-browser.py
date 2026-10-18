"""Run with Python + Playwright; uses an isolated Chrome profile."""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / 'PoE2_RexTool.html'
artifacts = root / 'docs/project-memory'
artifacts.mkdir(parents=True, exist_ok=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(target.as_uri())
    data = page.evaluate('window.POE2_DATA.waystone')
    affixes = {a['id']: a for a in data}
    results = []

    def row(affix_id):
        return page.locator(f'#affix-list [data-id="{affix_id}"]')

    def choose(affix_id, mode='include'):
        row(affix_id).locator('button.inc' if mode == 'include' else 'button.exc').click()

    def output():
        source = page.locator('#regex-source').inner_text()
        assert source and not page.locator('#copy').is_disabled(), source
        assert len(source) <= 250, source
        return source

    def matches(source, text):
        return page.evaluate(r"""([source, text]) => [...source.matchAll(/"([^\"]+)"/g)].every(match => {
            const negative = match[1][0] === '!';
            const hit = new RegExp(negative ? match[1].slice(1) : match[1]).test(text);
            return negative ? !hit : hit;
        })""", [source, text])

    for language in ['cn', 'tw', 'en']:
        page.locator('#language').select_option(language)
        page.locator('#tab-waystone').click()
        page.locator('#clear-selected').click()
        page.locator('#match-all').click()
        samples = {}
        for affix_id in ['wt006', 'wt014']:
            a = affixes[affix_id]
            values = [208, 22] if affix_id == 'wt006' else [50, 50]
            samples[affix_id] = '\n'.join(re.sub(r'\(\d+—\d+\)', str(value), line)
                                                  for line, value in zip(a['lines'][language], values))
            page.locator('#clear-selected').click()
            choose(affix_id)
            assert row(affix_id).locator('.ln').count() == 2
            assert row(affix_id).locator('.ln').all_text_contents() == a['lines'][language]
            source = output()
            assert matches(source, samples[affix_id]), (language, affix_id, source)
            # Only first-line text belongs in search output; both remain visible above.
            assert source.count('"') == 2, source
            field = row(affix_id).locator('[data-thr="value"]')
            field.focus()
            field.fill('200' if affix_id == 'wt006' else '40')
            field.press('Tab')
            assert matches(output(), samples[affix_id]), output()
            field.focus()
            field.fill('250' if affix_id == 'wt006' else '60')
            field.press('Tab')
            assert not matches(output(), samples[affix_id]), output()
            field.focus()
            field.fill('')
            field.press('Tab')
            upper = row(affix_id).locator('[data-thr="value2"]')
            upper.focus()
            upper.fill('240' if affix_id == 'wt006' else '60')
            upper.press('Tab')
            assert matches(output(), samples[affix_id]), output()
            results.append({'language': language, 'affix': affix_id, 'source': source})

        page.locator('#clear-selected').click()
        choose('wt006')
        choose('wt014')
        both = samples['wt006'] + '\n' + samples['wt014']
        assert matches(output(), both)
        assert not matches(output(), samples['wt006'])
        page.locator('#match-any').click()
        assert matches(output(), samples['wt006'])
        assert matches(output(), samples['wt014'])
        assert not matches(output(), 'unrelated item')
        page.locator('#match-all').click()
        page.locator('#clear-selected').click()
        choose('wt006', 'exclude')
        choose('wt014')
        assert not matches(output(), both)
        assert matches(output(), samples['wt014'])

    page.locator('#language').select_option('cn')
    page.locator('#clear-selected').click()
    choose('wt006')
    lower = row('wt006').locator('[data-thr="value"]')
    lower.focus()
    lower.fill('200')
    lower.press('Tab')
    actual = '怪物暴击率提高 208 (200-240)%\n+22 (21-25)% 怪物暴击伤害加成'
    assert matches(output(), actual)
    page.reload()
    assert row('wt006').locator('[data-thr="value"]').input_value() == '200'
    assert matches(output(), actual)
    page.screenshot(path=str(artifacts / 'composite-affix-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    assert row('wt006').locator('.ln').count() == 2
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    row('wt006').scroll_into_view_if_needed()
    page.screenshot(path=str(artifacts / 'composite-affix-mobile.png'))
    assert not errors, errors
    (artifacts / 'composite-affix-browser-results.json').write_text(json.dumps({
        'cases': results, 'actualSample': actual, 'actualOutput': output(), 'pageErrors': errors
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    browser.close()
    print('PASS: 6 Chrome compound/language cases; thresholds, all/any/exclude, actual advanced sample, persistence and mobile')

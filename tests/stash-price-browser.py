"""python tests/stash-price-browser.py — requires Playwright and Chrome."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import re
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/PoE2_RexTool.html'
screens = ROOT / 'docs' / 'project-memory'
screens.mkdir(parents=True, exist_ok=True)

def matches(source, text):
    blocks = re.findall(r'"([^\"]+)"', source)
    assert blocks
    return all((not re.search(b[1:], text, re.I)) if b.startswith('!') else bool(re.search(b, text, re.I)) for b in blocks)

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1100}, permissions=['clipboard-read', 'clipboard-write'])
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url)
    assert page.locator('#tabs button').count() == 2
    expect(page.locator('#price-card')).to_be_visible()
    expect(page.locator('#price-reset')).to_have_text('清除')
    assert page.locator('#price-card #price-share').count() == 0
    assert page.locator('#price-intro, #price-budget').count() == 0
    assert page.locator('#price-card').bounding_box()['height'] <= 160, 'Price controls must fit a compact desktop row'
    print(f"Desktop price card: {page.locator('#price-card').bounding_box()['height']}px", flush=True)
    expect(page.locator('#copy')).to_be_disabled()
    page.locator('#price-min').fill('1')
    page.locator('#price-max').fill('2')
    page.locator('[data-price-currency=divine]').click()
    expect(page.locator('#regex-source')).to_have_text('"~b/o [12] div"')
    expect(page.locator('#regex-length')).to_have_text('15 / 250')
    expect(page.locator('#summary')).to_contain_text('1–2 神圣石')
    page.locator('#tier-min').fill('10')
    combined = page.locator('#regex-source').inner_text()
    assert len(re.findall(r'"([^\"]+)"', combined)) == 2
    assert matches(combined, '10阶\n~b/o 1 divine')
    assert not matches(combined, '9阶\n~b/o 1 divine')
    assert not matches(combined, '10阶\n~b/o 3 divine')
    expect(page.locator('#regex-length')).to_have_text(f'{len(combined)} / 250')
    page.locator('#copy').click()
    expect(page.locator('#status')).to_contain_text('已复制')
    assert page.evaluate('navigator.clipboard.readText()') == combined
    for invalid in ['1.5', '-1', '0', '1e3', 'abc', '<img src=x onerror=alert(1)>', '9007199254740992']:
        page.locator('#price-min').fill(invalid)
        expect(page.locator('#price-min')).to_have_value(invalid)
        expect(page.locator('#price-feedback')).to_contain_text('售价条件未生效')
        assert '~b/o' not in page.locator('#regex-source').inner_text()
        expect(page.locator('#copy')).to_be_enabled()  # Tier remains effective.
    page.locator('#price-min').fill('3')
    expect(page.locator('#price-feedback')).to_contain_text('最低价不能高于最高价')
    page.locator('#price-min').fill('1')
    page.reload()
    expect(page.locator('#regex-source')).to_have_text(combined)
    page.locator('#fav-name').fill('price-and-tier')
    page.locator('#fav-save').click()
    page.locator('#price-reset').click()
    expect(page.locator('#tier-min')).to_have_value('10')
    page.locator('#fav-list .fav-name').first.click()
    expect(page.locator('#regex-source')).to_have_text(combined)
    page.locator('#price-share').click()
    expect(page.locator('#status')).to_contain_text('已复制')
    link = page.evaluate('navigator.clipboard.readText()')
    assert '#tool=filters&data=' in link
    other = browser.new_context()
    shared = other.new_page()
    shared.goto(link)
    expect(shared.locator('#regex-source')).to_have_text(combined)
    expect(shared.locator('#tier-min')).to_have_value('10')
    # Shared ordinary basic filters must survive reload too.
    shared.locator('[data-revives="2"]').click()
    shared.locator('[data-rarity="rare"]').click()
    basic_source = shared.locator('#regex-source').inner_text()
    shared.reload()
    expect(shared.locator('#regex-source')).to_have_text(basic_source)
    shared.locator('#price-max').fill('9')
    shared.reload()
    expect(shared.locator('#price-max')).to_have_value('9')
    expect(shared.locator('#tier-min')).to_have_value('10')
    other.close()
    # Price must remain AND even when included affixes are OR.
    page.locator('#language').select_option('en')
    for affix in ['wt001', 'wt002']:
        page.locator(f'[data-id={affix}] [data-act=include]').click()
    page.locator('#match-any').click()
    source = page.locator('#regex-source').inner_text()
    assert matches(source, 'Tier 10\nMonsters deal 5% of Damage as Extra Fire\n~b/o 1 divine')
    assert not matches(source, 'Tier 10\nMonsters deal 5% of Damage as Extra Fire\n~b/o 100 divine')
    assert not matches(source, 'Tier 10\n~b/o 1 divine')
    # Combined budget cannot trigger the original lossy affix fitting path.
    page.locator('#clear-selected').click()
    ids = page.locator('#affix-list [data-id]').evaluate_all('(rows) => rows.slice(0, 12).map(row => row.getAttribute("data-id"))')
    for affix in ids:
        page.locator(f'[data-id="{affix}"] [data-act=include]').click()
    page.locator('#match-all').click()
    assert len(page.locator('#regex-source').inner_text()) > 250
    expect(page.locator('#copy')).to_be_disabled()
    expect(page.locator('#regex-source')).to_contain_text('"~b/o [12] div"')
    page.locator('#clear-selected').click()
    for affix in ['wt001', 'wt002']:
        page.locator(f'[data-id={affix}] [data-act=include]').click()
    page.locator('#match-any').click()
    # Separate per-tab prices and original tablet type conditions.
    page.locator('#tab-tablet').click()
    expect(page.locator('#price-min')).to_have_value('')
    page.locator('#primary-body [data-type]').first.click()
    page.locator('#price-max').fill('10')
    tablet = page.locator('#regex-source').inner_text()
    assert '~b/o' in tablet and len(re.findall(r'"([^\"]+)"', tablet)) == 2
    page.locator('#tab-waystone').click()
    expect(page.locator('#price-min')).to_have_value('1')
    expect(page.locator('#price-max')).to_have_value('2')
    expect(page.locator('#regex-source')).to_have_text(source)
    for lang, title in [('tw', '售價篩選'), ('en', 'Price filter'), ('cn', '售价筛选')]:
        page.locator('#language').select_option(lang)
        expect(page.locator('#price-title')).to_have_text(title)
        expect(page.locator('#regex-source')).to_contain_text('"~b/o [12] div"')
    page.locator('[data-price-mode=min]').click()
    expect(page.locator('#price-max-field')).to_be_hidden()
    page.locator('#price-min').fill('1000')
    expect(page.locator('#summary')).to_contain_text('≥ 1000')
    page.locator('[data-price-mode=max]').click()
    expect(page.locator('#price-min-field')).to_be_hidden()
    page.locator('#price-max').fill('10')
    page.locator('[data-price-mode=between]').click()
    page.locator('#price-min').fill('1234567890123456')
    page.locator('#price-max').fill('8765432109876543')
    expect(page.locator('#regex-message')).to_contain_text('250')
    expect(page.locator('#copy')).to_be_disabled()
    assert '~b/o' in page.locator('#regex-source').inner_text()
    page.locator('#clear').click()
    expect(page.locator('#price-min')).to_have_value('')
    expect(page.locator('#tier-min')).to_have_value('')
    expect(page.locator('#copy')).to_be_disabled()
    page.locator('#price-max').fill('10')
    page.locator('#tier-min').fill('10')
    page.screenshot(path=str(screens / 'stash-price-integrated-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
    assert page.locator('#price-card').bounding_box()['height'] <= 270, 'Compact mobile controls'
    print(f"Mobile price card: {page.locator('#price-card').bounding_box()['height']}px", flush=True)
    page.screenshot(path=str(screens / 'stash-price-integrated-mobile.png'), full_page=True)
    assert not errors, errors
    blocked = browser.new_context()
    blocked.add_init_script("Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } });")
    blocked_page = blocked.new_page()
    blocked_page.goto(url)
    blocked_page.locator('#price-max').fill('10')
    expect(blocked_page.locator('#copy')).to_be_enabled()
    blocked.close()
    legacy = browser.new_context()
    legacy.add_init_script("localStorage.setItem('poe2.price.v1', JSON.stringify({min:'1',max:'2',currency:'divine',mode:'between',active:true}));")
    legacy_page = legacy.new_page()
    legacy_page.goto(url)
    expect(legacy_page.locator('#regex-source')).to_have_text('"~b/o [12] div"')
    legacy_page.locator('#tab-tablet').click()
    expect(legacy_page.locator('#price-min')).to_have_value('')
    legacy.close()
    browser.close()
server.shutdown()
print('Chrome passed: both tabs, combined AND/affix OR, invalid price keeps other conditions, per-tab state, presets, clipboard, full-filter links, reload, languages, over-budget, mobile, blocked storage; no page errors.')

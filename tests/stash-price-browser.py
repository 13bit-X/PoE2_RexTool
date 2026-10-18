"""Optional browser checks: python tests/stash-price-browser.py (Playwright + Chrome)."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
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
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, permissions=['clipboard-read', 'clipboard-write'])
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url)
    expect(page.locator('#affix-workspace')).to_be_visible()
    expect(page.locator('#price-workspace')).to_be_hidden()
    page.locator('#tab-price').click()
    expect(page.locator('#affix-workspace')).to_be_hidden()
    expect(page.locator('#price-workspace')).to_be_visible()
    expect(page.locator('#price-copy')).to_be_disabled()
    page.locator('#price-min').fill('1')
    page.locator('#price-max').fill('2')
    page.locator('[data-price-currency=divine]').click()
    expect(page.locator('#price-source')).to_have_text('"~b/o [12] div"')
    expect(page.locator('#price-length')).to_have_text('15 / 250')
    expect(page.locator('#price-budget')).to_contain_text('235')
    page.locator('#price-copy').click()
    expect(page.locator('#price-status')).to_have_text('已复制')
    assert page.evaluate('navigator.clipboard.readText()') == '"~b/o [12] div"'
    page.screenshot(path=str(screens / 'stash-price-desktop.png'), full_page=True)
    for invalid in ['1.5', '-1', '0', '1e3', 'abc', '<img src=x onerror=alert(1)>', '9007199254740992']:
        page.locator('#price-min').fill(invalid)
        expect(page.locator('#price-min')).to_have_value(invalid)
        expect(page.locator('#price-source')).to_have_text('')
        expect(page.locator('#price-feedback')).to_contain_text('售价条件未生效')
        expect(page.locator('#price-copy')).to_be_disabled()
        expect(page.locator('#price-share')).to_be_disabled()
    page.locator('#price-min').fill('3')
    expect(page.locator('#price-feedback')).to_contain_text('最低价不能高于最高价')
    page.locator('#price-min').fill('1')
    page.locator('#price-copy').click()
    expect(page.locator('#price-status')).to_have_text('已复制')
    page.reload()
    expect(page.locator('#price-workspace')).to_be_visible()
    expect(page.locator('#price-min')).to_have_value('1')
    expect(page.locator('#price-source')).to_have_text('"~b/o [12] div"')
    page.locator('#price-share').click()
    expect(page.locator('#price-status')).to_have_text('已复制')
    link = page.evaluate('navigator.clipboard.readText()')
    assert '#tool=price&mode=between&min=1&max=2&cur=divine' in link
    other = browser.new_context(viewport={'width': 1440, 'height': 1000})
    shared = other.new_page()
    shared.goto(link)
    expect(shared.locator('#price-source')).to_have_text('"~b/o [12] div"')
    shared.locator('#price-max').fill('9')
    shared.reload()
    expect(shared.locator('#price-max')).to_have_value('9')
    expect(shared.locator('#price-source')).to_have_text('"~b/o [1-9] div"')
    other.close()
    for lang, title in [('tw', '售價篩選'), ('en', 'Price filter'), ('cn', '售价筛选')]:
        page.locator('#language').select_option(lang)
        expect(page.locator('#tab-price')).to_have_text(title)
        expect(page.locator('#tab-price')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#price-source')).to_have_text('"~b/o [12] div"')
    page.locator('[data-price-mode=min]').click()
    expect(page.locator('#price-max-field')).to_be_hidden()
    page.locator('#price-min').fill('1000')
    expect(page.locator('#price-summary')).to_contain_text('≥ 1000')
    assert page.locator('#price-source').inner_text() != '"~b/o 999 div"'
    page.locator('[data-price-mode=max]').click()
    expect(page.locator('#price-min-field')).to_be_hidden()
    page.locator('#price-max').fill('10')
    expect(page.locator('#price-summary')).to_contain_text('1–10')
    page.locator('[data-price-mode=between]').click()
    page.locator('#price-min').fill('1234567890123456')
    page.locator('#price-max').fill('8765432109876543')
    expect(page.locator('#price-budget')).to_contain_text('超出 250')
    expect(page.locator('#price-copy')).to_be_disabled()
    page.locator('#price-reset').click()
    expect(page.locator('#price-min')).to_have_value('')
    expect(page.locator('#price-max')).to_have_value('')
    expect(page.locator('#price-copy')).to_be_disabled()
    # Existing module state and controls survive entering/leaving the new tab.
    page.locator('#tab-waystone').click()
    expect(page.locator('#affix-workspace')).to_be_visible()
    expect(page.locator('#price-workspace')).to_be_hidden()
    page.locator('#tier-min').fill('10')
    before = page.locator('#regex-source').inner_text()
    assert before
    page.locator('#tab-price').click()
    page.locator('#price-max').fill('10')
    page.locator('#price-reset').click()
    page.locator('#tab-waystone').click()
    expect(page.locator('#tier-min')).to_have_value('10')
    expect(page.locator('#regex-source')).to_have_text(before)
    page.locator('#tab-tablet').click()
    expect(page.locator('#primary-heading')).to_have_text('石板')
    page.locator('#tab-price').click()
    page.locator('#price-min').fill('1')
    page.locator('#price-max').fill('10')
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
    expect(page.locator('#price-copy')).to_be_visible()
    page.screenshot(path=str(screens / 'stash-price-mobile.png'), full_page=True)
    assert not errors, errors
    # Disabled storage must not make the feature unusable.
    blocked = browser.new_context()
    blocked.add_init_script("Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } });")
    blocked_page = blocked.new_page()
    blocked_page.goto(url)
    blocked_page.locator('#tab-price').click()
    blocked_page.locator('#price-max').fill('10')
    expect(blocked_page.locator('#price-copy')).to_be_enabled()
    expect(blocked_page.locator('#price-status')).to_contain_text('无法保存')
    blocked.close()
    browser.close()
server.shutdown()
print('Chrome passed: inputs, integer ranges, currencies, clipboard, sharing, reload, three languages, old tabs, over-budget, mobile and blocked storage; no page errors.')

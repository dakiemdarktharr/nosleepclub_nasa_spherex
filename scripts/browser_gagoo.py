"""Check the shipped mascot, science navigation and blank learning route together.

Runs against an isolated local static server by default. No live API writes.
"""
import argparse
from contextlib import contextmanager
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading

from playwright.sync_api import expect, sync_playwright

from scripts.browser_smoke import QuietHandler, ROOT


@contextmanager
def serve():
    class Server(ThreadingHTTPServer):
        request_queue_size = 128
        daemon_threads = True
    server = Server(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'web')))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def check_case(browser, base, output, width, language, light=False):
    mobile = width < 620
    name = f'{width}-{language}-{"light" if light else "dark"}'
    context = browser.new_context(viewport={'width': width, 'height': 844 if mobile else 920},
                                  is_mobile=mobile, has_touch=mobile, reduced_motion='reduce')
    if light:
        context.add_init_script("localStorage.setItem('spherex.theme','light')")
    page = context.new_page()
    page.set_default_timeout(15000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    for endpoint in ('reviews', 'observations', 'frame'):
        context.route(f'**/api/{endpoint}*', lambda route: route.abort())
    try:
        page.goto(f'{base}/?lang={language}#orbit')
        target = page.locator('#gagoo-target')
        expect(target).to_have_attribute('data-model', '3d')
        page.screenshot(path=str(output / f'home-{name}.png'))
        before = target.bounding_box()
        # A drag crossing the click threshold must leave the user on the home page.
        if mobile:
            session = context.new_cdp_session(page)
            x, y = before['x'] + before['width'] / 2, before['y'] + before['height'] / 2
            session.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
            for i in range(1, 9):
                session.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x + i * 6, 'y': y - i * 4}]})
            session.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        else:
            page.mouse.move(before['x'] + before['width'] / 2, before['y'] + before['height'] / 2)
            page.mouse.down()
            page.mouse.move(before['x'] + before['width'] / 2 + 100, before['y'] + before['height'] / 2 - 65, steps=12)
            page.mouse.up()
        expect(page).to_have_url(re.compile(r'#orbit$'))
        expect(page.locator('.gagoo-entrance')).to_have_count(0)
        page.wait_for_function('(x) => Math.abs(document.querySelector("#gagoo-target").getBoundingClientRect().x-x)>30', arg=before['x'])
        rope = page.locator('.gagoo-tether path').last.get_attribute('d')
        assert rope and 'NaN' not in rope and 'Infinity' not in rope
        page.wait_for_timeout(450)  # Explicit drag-to-click suppression interval.
        if mobile:
            target.tap()
            expect(target).to_have_attribute('data-tap-preview', 'true')
            expect(page).to_have_url(re.compile(r'#orbit$'))
            target.tap()
        else:
            target.focus()
            page.keyboard.press('Enter')
        expect(page).to_have_url(re.compile(r'#learn$'))
        expect(page.locator('.gagoo-entrance')).to_have_count(0)
        expect(page.locator('#learn')).to_be_visible()
        expect(page.locator('#learn-title')).to_be_focused()
        expect(page).to_have_title(re.compile(r'sphere x learn'))
        assert page.locator('#learn').inner_text() == 'sphere x learn'
        page.screenshot(path=str(output / f'learn-{name}.png'))

        # The new public route must remain public after the research router loads.
        page.goto(f'{base}/?lang={language}&flow_source=wise#compare-step')
        page.wait_for_function('window.SkyApp?.context().ready === true')
        expect(page).to_have_title(re.compile(r'sphere x search'))
        expect(page.locator('.workflow-header .brand')).to_contain_text('sphere x search')
        page.locator('.workflow-header [data-iris-home]').click()
        expect(page.locator('#orbit')).to_be_visible()
        expect(target).to_have_attribute('data-model', '3d')
        target.focus()
        page.keyboard.press('Enter')
        expect(page.locator('#learn')).to_be_visible()
        expect(page.locator('#workflow-main')).not_to_be_visible()
        expect(page).to_have_title(re.compile(r'sphere x learn'))

        # A direct science permalink and its contents links may not open the workbench.
        page.goto(f'{base}/?lang={language}#ss-1-orbit')
        expect(page.locator('#spherex-science.spherex-science')).to_be_visible()
        expect(page.locator('.about-story')).to_have_count(1)
        assert page.evaluate('document.querySelector(".about-story").compareDocumentPosition(document.querySelector("#spherex-science")) & Node.DOCUMENT_POSITION_FOLLOWING')
        expect(page.locator('#about')).to_be_visible()
        orbit_button = page.locator('[data-science-action="orbit"][data-value="1"]')
        orbit_button.click()
        expect(orbit_button).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#ss-1-orbit-panel')).to_contain_text('91°')
        page.screenshot(path=str(output / f'orientation-{name}.png'))
        page.locator('[data-science-action="engineering"][data-value="3"]').click()
        expect(page.locator('#ss-1-engineering-panel')).to_contain_text('750')
        page.locator('[data-science-action="detector"][data-value="5"]').click()
        slider = page.locator('[data-science-range]')
        slider.focus()
        page.keyboard.press('End')
        expect(slider).to_have_value('4')
        expect(page.locator('[data-position-output]')).to_have_text('5 / 5')
        page.locator('.ss-jump a[href="#ss-1-results"]').click()
        expect(page.locator('#about')).to_be_visible()
        expect(page.locator('#workflow-main')).not_to_be_visible()
        expect(page.locator('#ss-1-results')).to_be_in_viewport()
        page.locator('.public-header [data-language]').click()
        expect(page.locator('#spherex-science')).to_have_attribute('lang', 'vi' if language == 'en' else 'en')
        expect(page.locator('[data-science-action="detector"][data-value="5"]')).to_have_attribute('aria-pressed', 'true')
        expect(slider).to_have_value('4')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        assert not errors, errors
        return {'case': name, 'passed': True, 'page_errors': errors}
    except Exception:
        page.screenshot(path=str(output / f'failure-{name}.png'))
        raise
    finally:
        context.close()


def cinema_case(browser, base, output):
    """Run the real home-to-Learn transition without reducing its animation."""
    context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(f'{base}/?lang=en#orbit')
        target = page.locator('#gagoo-target')
        expect(target).to_have_attribute('data-model', '3d', timeout=15000)
        target.tap()
        expect(target).to_have_attribute('data-tap-preview', 'true')
        target.tap()
        expect(page.locator('.gagoo-entrance')).to_be_visible()
        expect(page.locator('#learn')).to_be_visible(timeout=15000)
        expect(page.locator('.gagoo-entrance')).to_have_count(0)
        expect(page.locator('#learn-title')).to_be_focused()
        page.go_back()
        expect(page.locator('#orbit')).to_be_visible()
        expect(target).to_have_attribute('data-model', '3d')
        assert not errors, errors
        return {'case': 'mobile-full-cinematic-route', 'passed': True, 'page_errors': errors}
    except Exception:
        page.screenshot(path=str(output / 'failure-cinematic-route.png'))
        raise
    finally:
        context.close()


def fallback_case(browser, base, output):
    """The actual-model poster and two-tap entrance survive a blocked 3D module."""
    context = browser.new_context(viewport={'width': 320, 'height': 844}, is_mobile=True,
                                  has_touch=True, reduced_motion='reduce')
    context.route('**/gagoo-scene.js*', lambda route: route.abort())
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(f'{base}/?lang=vi#orbit')
        target = page.locator('#gagoo-target')
        expect(target).to_have_attribute('data-model', 'fallback')
        page.wait_for_function('document.querySelector("#gagoo-fallback").naturalWidth > 0')
        page.screenshot(path=str(output / 'fallback-320.png'))
        target.tap()
        expect(target).to_have_attribute('data-tap-preview', 'true')
        expect(page).to_have_url(re.compile(r'#orbit$'))
        target.tap()
        expect(page.locator('#learn')).to_be_visible()
        expect(page.locator('#learn-title')).to_be_focused()
        assert not errors, errors
        return {'case': 'mobile-model-fallback', 'passed': True, 'page_errors': errors}
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/raw/gagoo-integrated')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    with serve() as local, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for width, language, light in [(1366, 'en', False), (390, 'vi', False), (320, 'en', True)]:
                results.append(check_case(browser, args.base or local, args.output, width, language, light))
                print(results[-1], flush=True)
            for check in (cinema_case, fallback_case):
                results.append(check(browser, args.base or local, args.output))
                print(results[-1], flush=True)
        finally:
            browser.close()
            (args.output / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

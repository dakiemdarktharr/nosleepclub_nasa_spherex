"""Exercise the independent control-room prototype with the production CSP.

No API writes. Tests movement, two reachable interactions, answer feedback,
mobile screen/control separation and a recoverable WebGL failure.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts.browser_gagoo import serve
from scripts.browser_smoke import ROOT


def position(page):
    return page.locator('#room-canvas').evaluate('(node) => [Number(node.dataset.playerX), Number(node.dataset.playerZ)]')


def run_case(browser, base, output, width, height, language, mobile):
    name = f'{width}x{height}-{language}'
    context = browser.new_context(viewport={'width': width, 'height': height},
                                  is_mobile=mobile, has_touch=mobile, reduced_motion='reduce')
    page = context.new_page()
    page.set_default_timeout(15000)
    errors, writes = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def read_only(route):
        if route.request.method not in ('GET', 'HEAD'):
            writes.append(route.request.method)
            route.abort()
        else:
            route.continue_()
    context.route('**/*', read_only)
    try:
        page.goto(f'{base}/control-room.html?lang={language}')
        expect(page.locator('body')).to_have_attribute('data-scene-state', 'ready')
        expect(page.locator('body')).to_have_attribute('data-game-state', 'room')
        expect(page.locator('#room-prompt')).not_to_be_visible()
        expect(page.locator('#room-context-key')).not_to_be_visible()
        page.keyboard.press('e')
        expect(page.locator('body')).to_have_attribute('data-game-state', 'room')
        expect(page.locator('#room-canvas')).to_have_attribute('data-shadow-map', 'enabled')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        if mobile:
            screen = page.locator('#room-screen').bounding_box()
            controls = page.locator('#room-controls').bounding_box()
            assert abs(screen['height'] - height / 2) <= 2, screen
            assert abs(controls['height'] - height / 2) <= 2, controls
            assert abs(screen['y'] + screen['height'] - controls['y']) <= 2
        page.screenshot(path=str(output / f'room-{name}.png'))

        # Reduced motion freezes decorative drift, so this observable change
        # must come from real player contact and retained momentum.
        prop_states = lambda: page.locator('#room-canvas').evaluate('(node) => JSON.parse(node.dataset.floatingProps)')
        initial_props = prop_states()
        assert {'mug', 'book', 'pen'} <= {prop['kind'] for prop in initial_props}
        page.keyboard.down('ArrowUp')
        try:
            page.wait_for_function('() => Number(document.querySelector("#room-canvas").dataset.propPlayerCollisions) > 0', timeout=7000)
        finally:
            page.keyboard.up('ArrowUp')
        struck = next(prop for prop in prop_states() if prop['playerContacts'] > 0)
        assert sum(v*v for v in struck['velocity']) > .01, struck
        page.wait_for_timeout(250)
        drifting = next(prop for prop in prop_states() if prop['id'] == struck['id'])
        assert sum(abs(a-b) for a,b in zip(struck['position'], drifting['position'])) > .01
        page.screenshot(path=str(output / f'prop-contact-{name}.png'))

        # Real keyboard movement must change world position, then stop on keyup.
        before = position(page)
        page.keyboard.down('ArrowDown')
        page.wait_for_timeout(450)
        page.keyboard.up('ArrowDown')
        after = position(page)
        assert sum(abs(a - b) for a, b in zip(before, after)) > .1, (before, after)
        page.wait_for_timeout(150)
        stopped = position(page)
        page.wait_for_timeout(200)
        assert sum(abs(a - b) for a, b in zip(stopped, position(page))) < .02

        if mobile:
            # Real touchscreen hold/cancel, not an artificial click handler.
            pad = page.locator('[data-direction="up"]').bounding_box()
            touch = context.new_cdp_session(page)
            before_touch = position(page)
            touch.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [
                {'x': pad['x'] + pad['width'] / 2, 'y': pad['y'] + pad['height'] / 2}]})
            page.wait_for_timeout(250)
            touch.send('Input.dispatchTouchEvent', {'type': 'touchCancel', 'touchPoints': []})
            assert sum(abs(a - b) for a, b in zip(before_touch, position(page))) > .1
            page.wait_for_timeout(120)
            cancelled = position(page)
            page.wait_for_timeout(200)
            assert position(page) == cancelled, 'Touch cancellation left movement active'

        page.locator('#room-tablet-shortcut').click()
        page.wait_for_function('''() => document.querySelector('#room-canvas').dataset.near === 'tablet'
            && document.body.dataset.gameState === 'room' ''')
        # Cancel automatic walking inside the interaction radius, then use the
        # actual context prompt. It must not be a permanent decorative E badge.
        page.keyboard.press('Escape')
        expect(page.locator('#room-prompt')).to_be_visible()
        expect(page.locator('#room-interact')).to_be_enabled()
        page.locator('#room-prompt').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'tablet', timeout=20000)
        expect(page.locator('#room-prompt')).not_to_be_visible()
        page.screenshot(path=str(output / f'tablet-{name}.png'))
        held_position = position(page)
        held_props = prop_states()
        page.keyboard.down('ArrowLeft')
        page.wait_for_timeout(180)
        page.keyboard.up('ArrowLeft')
        assert position(page) == held_position, 'Movement must pause during the tablet overlay'
        assert prop_states() == held_props, 'Prop motion must pause while reading an overlay'
        page.keyboard.press('Escape')
        expect(page.locator('body')).to_have_attribute('data-game-state', 'room')

        page.locator('#room-alien-shortcut').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'dialogue', timeout=20000)
        page.screenshot(path=str(output / f'dialogue-{name}.png'))
        for _ in range(5):
            if page.locator('#room-test-choice').is_visible():
                break
            page.locator('#room-dialogue-next').click()
        expect(page.locator('#room-test-choice')).to_be_visible()
        page.locator('#room-test-choice').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'study')

        # An incorrect answer must explain the distinction; retry accepts a
        # correct answer and advances without persisting a fabricated score.
        options = page.locator('#room-quiz-options button[data-answer]')
        expect(options).to_have_count(4)
        page.locator('#room-quiz-options button:not([data-answer="infrared"])').first.click()
        expect(page.locator('#room-quiz-feedback')).to_have_attribute('data-correct', 'false')
        assert len(page.locator('#room-quiz-feedback').inner_text()) > 40
        page.locator('#room-quiz-retry').click()
        page.locator('#room-quiz-options [data-answer="infrared"]').click()
        expect(page.locator('#room-quiz-feedback')).to_have_attribute('data-correct', 'true')
        page.screenshot(path=str(output / f'quiz-{name}.png'))
        page.locator('#room-quiz-next').click()
        expect(options).to_have_count(4)
        page.locator('#room-language').click()
        expect(page.locator('html')).to_have_attribute('lang', 'vi' if language == 'en' else 'en')
        expect(page.locator('body')).to_have_attribute('data-game-state', 'study')
        page.locator('#room-quiz-options [data-answer="channels"]').click()
        expect(page.locator('#room-quiz-feedback')).to_have_attribute('data-correct', 'true')
        page.locator('#room-quiz-next').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'room')
        page.locator('#room-alien-shortcut').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'dialogue')
        page.locator('#room-close').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'room')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        assert not errors, errors
        assert not writes, writes
        return {'case': name, 'passed': True, 'page_errors': errors, 'api_writes': writes}
    except Exception:
        page.screenshot(path=str(output / f'failure-{name}.png'))
        raise
    finally:
        context.close()


def fallback_case(browser, base, output):
    context = browser.new_context(viewport={'width': 390, 'height': 844},
                                  is_mobile=True, has_touch=True, reduced_motion='reduce')
    context.add_init_script('''
        const original = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(kind, ...args) {
            return kind.includes('webgl') ? null : original.call(this, kind, ...args);
        };
    ''')
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(f'{base}/control-room.html?lang=vi')
        expect(page.locator('body')).to_have_attribute('data-scene-state', 'error')
        expect(page.locator('#room-error')).to_be_visible()
        page.locator('#room-tablet-shortcut').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'tablet')
        assert page.locator('.room-tablet-display').inner_text() == ''
        page.keyboard.press('Escape')
        page.locator('#room-alien-shortcut').click()
        page.locator('#room-dialogue-next').click()
        page.locator('#room-test-choice').click()
        page.locator('[data-answer="infrared"]').click()
        expect(page.locator('#room-quiz-feedback')).to_have_attribute('data-correct', 'true')
        page.screenshot(path=str(output / 'webgl-fallback.png'))
        assert not errors, errors
        return {'case': 'webgl-unavailable', 'passed': True, 'page_errors': errors}
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/raw/control-room-review')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    with serve() as local, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for width, height, language, mobile in [(1366, 900, 'en', False),
                                                    (390, 844, 'vi', True),
                                                    (320, 740, 'en', True),
                                                    (844, 390, 'en', True)]:
                result = run_case(browser, args.base or local, args.output, width, height, language, mobile)
                results.append(result)
                print(json.dumps(result), flush=True)
            result = fallback_case(browser, args.base or local, args.output)
            results.append(result)
            print(json.dumps(result), flush=True)
        finally:
            browser.close()
            (args.output / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

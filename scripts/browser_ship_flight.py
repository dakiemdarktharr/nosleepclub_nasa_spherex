"""Real UI journey: encounter, learning, earned fuel, thruster and both flights."""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from scripts.browser_gagoo import serve
from scripts.browser_control_room import finish_lesson, start_quiz


def run_case(browser, base, output, width, tier):
    context = browser.new_context(viewport={'width': width, 'height': 844 if width < 600 else 900},
                                  is_mobile=width < 600, has_touch=width < 600)
    context.add_init_script('''
        window.flightTiming={};
        new MutationObserver(()=>{
          const state=document.body?.dataset.gameState;
          if(state==='flight'&&!window.flightTiming.start)window.flightTiming.start=performance.now();
          if(state==='report'&&!window.flightTiming.end)window.flightTiming.end=performance.now();
        }).observe(document,{subtree:true,attributes:true,attributeFilter:['data-game-state']});
    ''')
    page = context.new_page()
    page.set_default_timeout(30000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    name = f'{width}-{tier}'
    try:
        page.goto(f'{base}/control-room.html?lang={"vi" if width < 600 else "en"}')
        expect(page.locator('body')).to_have_attribute('data-game-state', 'encounter')
        expect(page.locator('#room-tablet-shortcut')).to_be_disabled()
        page.wait_for_timeout(1400)
        page.screenshot(path=str(output / f'portal-{name}.png'))
        expect(page.locator('body')).to_have_attribute('data-game-state', 'room')
        page.locator('#room-alien-shortcut').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'dialogue')
        page.screenshot(path=str(output / f'dialogue-{name}.png'))
        page.locator('#room-dialogue-next').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'tablet')
        finish_lesson(page)
        start_quiz(page)
        # Closing/reopening preserves the first response AND its explanation.
        page.locator('[data-answer="0"]').click()
        page.locator('#room-close').click()
        start_quiz(page)
        expect(page.locator('#room-quiz-feedback')).to_be_visible()
        expect(page.locator('#room-quiz-count')).to_have_text('1 / 6')
        page.locator('#room-quiz-next').click()
        for index, answer in enumerate([1, 2, 0, 1, 2], 1):
            if tier == 'normal' and index == 5:
                answer = 0
            page.locator(f'[data-answer="{answer}"]').click()
            page.locator('#room-quiz-next').click()
        expect(page.locator('body')).to_have_attribute('data-reward-tier', tier)
        page.locator('#room-claim-fuel').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'room')
        expect(page.locator('body')).to_have_attribute(f'data-fuel-{tier}', '1')
        # Reload after reward cannot lose fuel or replay the introduction.
        page.reload()
        expect(page.locator('body')).to_have_attribute('data-scene-state', 'ready')
        expect(page.locator('body')).to_have_attribute('data-game-state', 'room')
        expect(page.locator('body')).to_have_attribute(f'data-fuel-{tier}', '1')
        page.locator('#room-engine-shortcut').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'engine', timeout=45000)
        page.locator(f'#room-load-{tier}').click()
        expect(page.locator('body')).to_have_attribute('data-engine-fuel', tier)
        expect(page.locator('body')).to_have_attribute(f'data-fuel-{tier}', '0')
        expect(page.locator(f'#room-load-{tier}')).to_be_disabled()
        expect(page.locator('#room-fuel-meter')).to_have_attribute('value', '100')
        page.wait_for_timeout(1100)
        page.screenshot(path=str(output / f'engine-{name}.png'))
        page.locator('#room-close').click()
        page.screenshot(path=str(output / f'thruster-{name}.png'))
        page.locator('#room-bridge-shortcut').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'bridge', timeout=60000)
        page.locator('#room-close').click()
        expect(page.locator('#room-launch')).to_be_visible()
        page.locator('#room-launch').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'flight')
        page.wait_for_timeout(800)
        page.screenshot(path=str(output / f'flight-{name}.png'))
        page.keyboard.press('Escape')
        expect(page.locator('body')).to_have_attribute('data-game-state', 'flight')
        expect(page.locator('body')).to_have_attribute('data-game-state', 'report')
        elapsed = page.evaluate('(window.flightTiming.end-window.flightTiming.start)/1000')
        assert (3 if tier == 'normal' else 4) <= elapsed < (6 if tier == 'normal' else 7), elapsed
        expect(page.locator('#room-flight-progress')).to_have_attribute('aria-valuenow', '1' if tier == 'normal' else '2')
        expect(page.locator('body')).to_have_attribute('data-engine-fuel', 'none')
        page.screenshot(path=str(output / f'report-{name}.png'))
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#room-report-close').click()
        page.locator('#room-tablet-shortcut').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'tablet', timeout=60000)
        page.locator('#room-close').click()
        page.locator('#room-alien-shortcut').click()
        expect(page.locator('body')).to_have_attribute('data-game-state', 'dialogue')
        page.locator('#room-test-choice').click()
        expect(page.locator('#room-claim-fuel')).not_to_be_visible()
        expect(page.locator('#room-quiz-retry')).to_be_visible()
        assert not errors, errors
        return {'width': width, 'tier': tier, 'flight_seconds_observed': round(elapsed, 2), 'page_errors': errors}
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base')
    parser.add_argument('--output', type=Path, default=Path('data/raw/flight-review'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    # Assertions have their own timeout; page.set_default_timeout only covers
    # actions. Software-rendered walking can take longer than its default 5 s.
    expect.set_options(timeout=30000)
    results = []
    with serve() as base, sync_playwright() as p:
        browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] if sys.platform == 'win32' else [])
        try:
            for width, tier in [(1366, 'normal'), (390, 'super')]:
                result = run_case(browser, args.base or base, args.output, width, tier)
                results.append(result)
                print(json.dumps(result), flush=True)
            result = lifecycle_case(browser, args.base or base)
            results.append(result)
            print(json.dumps(result), flush=True)
        finally:
            browser.close()
            (args.output / 'journey-results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


def lifecycle_case(browser, base):
    """A saved reward fixture exercises host suspension and an interrupted flight."""
    context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    context.add_init_script('''
      if(!localStorage.getItem('spherex.room.lesson1.v1'))
        localStorage.setItem('spherex.room.lesson1.v1',JSON.stringify({completed:true,best:5,
          journey:{normal:1,super:0,loaded:'none',progress:0,encounterSeen:false}}));
    ''')
    page = context.new_page()
    page.set_default_timeout(30000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(f'{base}/?lang=vi#learn')
        game = page.frame_locator('#learn-game-frame')
        expect(page.locator('.public-brand')).to_have_text('Touch The Sky')
        expect(game.locator('body')).to_have_attribute('data-game-state', 'encounter')
        page.locator('#learn-qr-open').click()
        expect(game.locator('#room-canvas')).to_have_attribute('data-suspended', 'true')
        frozen = game.locator('#room-canvas').get_attribute('data-cinematic-time')
        page.wait_for_timeout(500)
        expect(game.locator('#room-canvas')).to_have_attribute('data-cinematic-time', frozen)
        page.locator('#learn-qr-dialog button').click()
        expect(game.locator('#room-canvas')).to_have_attribute('data-suspended', 'false')
        game.locator('#room-cinema-skip').click()
        game.locator('#room-engine-shortcut').click()
        expect(game.locator('body')).to_have_attribute('data-game-state', 'engine', timeout=45000)
        game.locator('#room-load-normal').click()
        # Loss during a hardware dialog must expose recovery, keeping loaded fuel.
        game.locator('#room-canvas').evaluate("node=>node.dispatchEvent(new Event('webglcontextlost',{cancelable:true}))")
        expect(game.locator('body')).to_have_attribute('data-game-state', 'room')
        expect(game.locator('body')).to_have_attribute('data-scene-state', 'error')
        expect(game.locator('#room-engine-panel')).not_to_be_visible()
        expect(game.locator('body')).to_have_attribute('data-engine-fuel', 'normal')
        page.reload()
        expect(game.locator('body')).to_have_attribute('data-scene-state', 'ready')
        expect(game.locator('body')).to_have_attribute('data-engine-fuel', 'normal')
        game.locator('#room-bridge-shortcut').click()
        expect(game.locator('body')).to_have_attribute('data-game-state', 'bridge', timeout=60000)
        game.locator('#room-bridge-launch').click()
        expect(game.locator('body')).to_have_attribute('data-game-state', 'flight')
        page.locator('#learn-qr-open').click()
        expect(game.locator('#room-canvas')).to_have_attribute('data-suspended', 'true')
        frozen = game.locator('#room-canvas').get_attribute('data-cinematic-time')
        page.wait_for_timeout(700)
        expect(game.locator('#room-canvas')).to_have_attribute('data-cinematic-time', frozen)
        # Reload while suspended. The paid flight resumes once; no extra fuel is used.
        page.reload()
        expect(game.locator('body')).to_have_attribute('data-game-state', 'flight')
        expect(game.locator('body')).to_have_attribute('data-fuel-normal', '0')
        expect(game.locator('body')).to_have_attribute('data-game-state', 'report')
        expect(game.locator('#room-flight-progress')).to_have_attribute('aria-valuenow', '1')
        assert not errors, errors
        return {'case': 'host-QR-suspension-and-flight-reload', 'passed': True, 'page_errors': errors}
    finally:
        context.close()


if __name__ == '__main__':
    main()

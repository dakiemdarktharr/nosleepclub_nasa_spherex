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


def traverse_ship(page):
    """Walk through the room graph with the game's real keyboard input loop.

    The driver follows grid waypoints using keyboard events; it never sets the
    actor position. A separate touchscreen hold/cancel test covers the pad.
    """
    page.set_default_timeout(90000)
    result = page.evaluate('''async () => {
      const {shipPath,SHIP_DOORS,SHIP_ROOMS} = await import('./ship-layout.js');
      const canvas = document.querySelector('#room-canvas');
      const targets = [['cockpit',6,0], ['sleep',3.5,0], ['kitchen',.5,0],
        ['living',-3,0], ['airlock',-6,1.25], ['living',-3,0], ['fuel',-6,-1.25]];
      const pos = () => ({x:Number(canvas.dataset.playerX),z:Number(canvas.dataset.playerZ)});
      const held = new Set();
      const setKeys = keys => {
        for (const k of held) if (!keys.includes(k)) {canvas.dispatchEvent(new KeyboardEvent('keyup',{key:k,bubbles:true}));held.delete(k);}
        for (const k of keys) if (!held.has(k)) {canvas.dispatchEvent(new KeyboardEvent('keydown',{key:k,bubbles:true}));held.add(k);}
      };
      const frame = () => new Promise(resolve => requestAnimationFrame(resolve));
      const visited=[];
      try {
        for (const [room,x,z] of targets) {
          let route=shipPath(pos(),{x,z});
          if (!route.length) throw new Error('No path to '+room);
          let index=0, ticks=0, wasCorridor=false;
          while(index<route.length) {
            if (++ticks>2200) throw new Error('Stuck walking to '+room+' at '+JSON.stringify(pos()));
            const p=pos(), phase=canvas.dataset.roomPhase;
            if (phase==='room'&&wasCorridor) {route=shipPath(p,{x,z});index=0;wasCorridor=false;if(!route.length)throw new Error('No path after corridor to '+room);}
            let target=route[index];
            if (phase!=='room') {
              wasCorridor=true;
              const from=canvas.dataset.room, to=canvas.dataset.destination;
              const door=SHIP_DOORS.find(d=>(d.from===from&&d.to===to)||(d.from===to&&d.to===from));
              const a=SHIP_ROOMS.find(r=>r.id===from), b=SHIP_ROOMS.find(r=>r.id===to);
              if(!door||!a||!b)throw new Error('Invalid corridor state '+from+' -> '+to);
              const sign=Math.sign((b.x0+b.x1)-(a.x0+a.x1));
              target={x:door.at+sign*.9,z:(door.start+door.end)/2};
            }
            const dx=target.x-p.x, dz=target.z-p.z;
            if (phase==='room'&&Math.hypot(dx,dz)<.12) {index++;continue;}
            const sx=.9285*dx-.3714*dz, sy=.3714*dx+.9285*dz, keys=[];
            if (Math.abs(sx)>.414*Math.abs(sy)) keys.push(sx>0?'ArrowRight':'ArrowLeft');
            if (Math.abs(sy)>.414*Math.abs(sx)) keys.push(sy>0?'ArrowDown':'ArrowUp');
            setKeys(keys);await frame();
          }
          setKeys([]);await frame();
          if (canvas.dataset.room!==room) throw new Error('Expected '+room+' got '+canvas.dataset.room);
          if (canvas.dataset.roomPhase!=='room' || canvas.dataset.visibleRooms!==room || canvas.dataset.corridorVisible!=='false')
            throw new Error('Expected the destination alone after entering '+room+': '+JSON.stringify(canvas.dataset));
          await window.captureShipRoom(room,visited.length);
          visited.push(room);
        }
      } finally {setKeys([]);}
      return visited;
    }''')
    assert result == ['cockpit', 'sleep', 'kitchen', 'living', 'airlock', 'living', 'fuel'], result
    page.set_default_timeout(15000)
    return result


def run_case(browser, base, output, width, height, language, mobile):
    name = f'{width}x{height}-{language}'
    context = browser.new_context(viewport={'width': width, 'height': height},
                                  is_mobile=mobile, has_touch=mobile, reduced_motion='reduce')
    page = context.new_page()
    page.set_default_timeout(15000)
    errors, writes = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.expose_binding('captureShipRoom', lambda source, room, index: source['page'].screenshot(
        path=str(output / f'ship-{name}-{index}-{room}.png')))

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

        # The full hull inspection is not gameplay: both sides must be visible
        # while keyboard/touch movement and station shortcuts are disabled.
        before_exterior = position(page)
        page.locator('#room-view').click()
        expect(page.locator('#room-canvas')).to_have_attribute('data-view', 'exterior')
        expect(page.locator('#room-view-side')).to_be_visible()
        expect(page.locator('[data-direction="up"]')).to_be_disabled()
        expect(page.locator('#room-tablet-shortcut')).to_be_disabled()
        first_side = page.locator('#room-canvas').get_attribute('data-exterior-side')
        page.screenshot(path=str(output / f'ship-exterior-hatch-{name}.png'))
        page.locator('#room-view-side').click()
        expect(page.locator('#room-canvas')).not_to_have_attribute('data-exterior-side', first_side)
        page.keyboard.down('ArrowUp')
        page.wait_for_timeout(200)
        page.keyboard.up('ArrowUp')
        assert position(page) == before_exterior, 'Exterior inspection moved the player'
        page.screenshot(path=str(output / f'ship-exterior-{name}.png'))
        page.locator('#room-view').click()
        expect(page.locator('#room-canvas')).to_have_attribute('data-view', 'cutaway')
        expect(page.locator('#room-view-side')).not_to_be_visible()
        expect(page.locator('[data-direction="up"]')).to_be_enabled()
        expect(page.locator('#room-tablet-shortcut')).to_be_enabled()

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
        expect(page.locator('body')).to_have_attribute('data-game-state', 'tablet', timeout=20000)
        # After the shortcut completes and the overlay closes, use the actual
        # context prompt. No timing race with auto-arrival is involved.
        page.keyboard.press('Escape')
        expect(page.locator('body')).to_have_attribute('data-game-state', 'room')
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
        visited = traverse_ship(page) if width in (1366, 390) else []
        if visited:
            page.screenshot(path=str(output / f'ship-fuel-{name}.png'))
            # A station shortcut from the far branch must cross the narrow
            # fuel/living doorway and finish, not stall at an old waypoint.
            page.locator('#room-tablet-shortcut').click()
            expect(page.locator('body')).to_have_attribute('data-game-state', 'tablet', timeout=30000)
            page.keyboard.press('Escape')
            expect(page.locator('body')).to_have_attribute('data-game-state', 'room')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        assert not errors, errors
        assert not writes, writes
        return {'case': name, 'passed': True, 'page_errors': errors, 'api_writes': writes, 'rooms_visited': visited}
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


def corridor_case(browser, base, output):
    """Hold a real destination module fetch, then fail and retry it.

    The initial living room must load normally. Gagoo reaches the kitchen
    doorway through keyboard input, never by changing world coordinates.
    """
    context = browser.new_context(viewport={'width': 1366, 'height': 900}, reduced_motion='no-preference')
    page = context.new_page()
    page.set_default_timeout(20000)
    errors, requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def defer_kitchen(route):
        if 'room=kitchen' in route.request.url and 'attempt=1' in route.request.url:
            requests.append(route)
        else:
            route.continue_()

    context.route('**/ship-room-assets.js?*', defer_kitchen)
    try:
        page.goto(f'{base}/control-room.html?lang=vi')
        expect(page.locator('body')).to_have_attribute('data-scene-state', 'ready')
        canvas = page.locator('#room-canvas')
        expect(canvas).to_have_attribute('data-room-phase', 'room')
        expect(canvas).to_have_attribute('data-room', 'living')
        # Diagonal screen input advances along world +X toward the kitchen.
        page.keyboard.down('ArrowRight')
        page.keyboard.down('ArrowDown')
        try:
            expect(canvas).to_have_attribute('data-room-phase', 'loading')
            expect(page.locator('#room-transition')).to_be_visible()
            expect(canvas).to_have_attribute('data-visible-rooms', '')
            expect(canvas).to_have_attribute('data-corridor-visible', 'true')
            page.wait_for_timeout(250)
            assert requests, 'Expected deferred kitchen asset request'
            # Door is closed until destination assets are available.
            assert position(page)[0] <= -.84, position(page)
            page.screenshot(path=str(output / 'corridor-loading.png'))
        finally:
            page.keyboard.up('ArrowRight')
            page.keyboard.up('ArrowDown')
        requests.pop().abort()
        expect(canvas).to_have_attribute('data-room-phase', 'error')
        expect(page.locator('#room-transition-retry')).to_be_visible()
        page.screenshot(path=str(output / 'corridor-error.png'))
        page.locator('#room-transition-retry').click()
        expect(canvas).to_have_attribute('data-room-phase', 'opening')
        expect(canvas).to_have_attribute('data-visible-rooms', '')
        expect(canvas).to_have_attribute('data-door-open', 'false')
        expect(canvas).to_have_attribute('data-room-phase', 'ready')
        expect(canvas).to_have_attribute('data-visible-rooms', 'kitchen')
        expect(canvas).to_have_attribute('data-corridor-visible', 'true')
        expect(canvas).to_have_attribute('data-door-open', 'true')
        page.screenshot(path=str(output / 'corridor-ready.png'))
        page.keyboard.down('ArrowRight')
        page.keyboard.down('ArrowDown')
        try:
            expect(canvas).to_have_attribute('data-room', 'kitchen')
            expect(canvas).to_have_attribute('data-room-phase', 'room')
        finally:
            page.keyboard.up('ArrowRight')
            page.keyboard.up('ArrowDown')
        expect(canvas).to_have_attribute('data-visible-rooms', 'kitchen')
        expect(canvas).to_have_attribute('data-corridor-visible', 'false')
        assert not errors, errors
        page.screenshot(path=str(output / 'corridor-entered.png'))
        return {'case': 'corridor-loading-error-retry', 'passed': True, 'page_errors': errors}
    finally:
        for route in requests:
            route.abort()
        context.close()


def corridor_retreat_case(browser, base, output):
    """A late response after turning around must never reveal its room."""
    context = browser.new_context(viewport={'width': 390, 'height': 844},
                                  is_mobile=True, has_touch=True, reduced_motion='reduce')
    page = context.new_page()
    page.set_default_timeout(20000)
    errors, pending = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def delay_kitchen(route):
        if 'room=kitchen' in route.request.url:
            pending.append(route)
        else:
            route.continue_()

    context.route('**/ship-room-assets.js?*', delay_kitchen)
    try:
        page.goto(f'{base}/control-room.html?lang=vi')
        expect(page.locator('body')).to_have_attribute('data-scene-state', 'ready')
        canvas = page.locator('#room-canvas')
        page.keyboard.down('ArrowRight')
        page.keyboard.down('ArrowDown')
        try:
            expect(canvas).to_have_attribute('data-room-phase', 'loading')
        finally:
            page.keyboard.up('ArrowRight')
            page.keyboard.up('ArrowDown')
        assert pending, 'Expected a pending request for the kitchen'
        expect(canvas).to_have_attribute('data-visible-rooms', '')
        expect(canvas).to_have_attribute('data-corridor-visible', 'true')
        page.screenshot(path=str(output / 'corridor-mobile-loading.png'))
        page.keyboard.down('ArrowLeft')
        page.keyboard.down('ArrowUp')
        try:
            expect(canvas).to_have_attribute('data-room-phase', 'room')
        finally:
            page.keyboard.up('ArrowLeft')
            page.keyboard.up('ArrowUp')
        expect(canvas).to_have_attribute('data-room', 'living')
        expect(canvas).to_have_attribute('data-visible-rooms', 'living')
        expect(canvas).to_have_attribute('data-corridor-visible', 'false')
        pending.pop().continue_()
        page.wait_for_timeout(500)
        expect(canvas).to_have_attribute('data-room-phase', 'room')
        expect(canvas).to_have_attribute('data-room', 'living')
        expect(canvas).to_have_attribute('data-visible-rooms', 'living')
        expect(canvas).to_have_attribute('data-corridor-visible', 'false')
        assert not errors, errors
        page.screenshot(path=str(output / 'corridor-mobile-retreat.png'))
        return {'case': 'corridor-retreat-late-response', 'passed': True, 'page_errors': errors}
    finally:
        for route in pending:
            route.abort()
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
            result = corridor_case(browser, args.base or local, args.output)
            results.append(result)
            print(json.dumps(result), flush=True)
            result = corridor_retreat_case(browser, args.base or local, args.output)
            results.append(result)
            print(json.dumps(result), flush=True)
        finally:
            browser.close()
            (args.output / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

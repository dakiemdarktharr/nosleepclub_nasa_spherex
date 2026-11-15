"""Browser lifecycle checks for the local Gagoo entrance. No live API requests."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import json
import threading

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
HARNESS = b'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<link rel="stylesheet" href="/gagoo-entrance.css"><button id="start">Open Gagoo</button>
<script type="module">
import {playGagooEntrance,cancelGagooEntrance,sampleGagooEntrance} from '/gagoo-entrance.js';
window.api={playGagooEntrance,cancelGagooEntrance,sampleGagooEntrance};
new MutationObserver(records=>{
  const canvas=document.querySelector('.gagoo-entrance-canvas');
  if(!canvas)return;
  const sample=()=>({...canvas.dataset,at:performance.now()-window.started});
  if(records.some(record=>record.target===canvas))window.frameSamples?.push(sample());
  if(records.some(record=>record.target.matches?.('dialog[data-stage="blinds"]')))window.blindsSample=sample();
}).observe(document.body,{subtree:true,attributes:true,attributeFilter:['data-actor-x','data-stage']});
window.start=(options={})=>{
  window.done=null; window.covered=0; window.failure=null;
  window.frameSamples=[]; window.blindsSample=null;
  window.started=performance.now();
  window.controller=new AbortController();
  playGagooEntrance({language:'en',signal:controller.signal,...options,onCovered:()=>{
    if(options.fail)throw new Error('intentional route failure');
    covered++; const oldURL=location.href; history.pushState(null,'','#learn');
    dispatchEvent(new HashChangeEvent('hashchange',{oldURL,newURL:location.href}));
  }}).then(result=>{done=result;window.elapsed=performance.now()-started;}).catch(error=>{window.failure=String(error)});
};
</script>'''


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/__gagoo_test.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HARNESS)
        else:
            try:
                super().do_GET()
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                # Cancellation tests intentionally close requests during imports.
                pass

    def log_message(self, *args):
        pass


def home_continuity_case(browser, base, output, width):
    context = browser.new_context(viewport={'width': width, 'height': 844},
                                  is_mobile=width < 620, has_touch=width < 620)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(f'{base}/?lang=en#orbit')
        target = page.locator('#gagoo-target')
        expect(target).to_have_attribute('data-model', '3d', timeout=15000)
        page.wait_for_function("() => document.querySelector('#orbit').dataset.model === '3d'")
        page.locator('#orbit-motion').click()
        expect(page.locator('#orbit-motion')).to_have_attribute('aria-pressed', 'true')
        target.focus()
        page.keyboard.press('Alt+ArrowRight')
        page.keyboard.press('Alt+ArrowRight')
        page.keyboard.press('Alt+ArrowDown')
        page.wait_for_timeout(80)
        before = page.evaluate("""() => {
          window.originalOrbit = document.querySelector('#orbit');
          return {transform: originalOrbit.style.transform, origin: originalOrbit.style.transformOrigin,
            targetVisibility: document.querySelector('#gagoo-target').style.visibility,
            targetTransform: document.querySelector('#gagoo-target').style.transform,
            headerOpacity: document.querySelector('.public-header').style.opacity};
        }""")
        page.screenshot(path=str(output / f'home-{width}-before.png'))
        target.focus()
        page.keyboard.press('Enter')
        page.wait_for_function("() => document.querySelector('.gagoo-entrance-canvas')?.dataset.phase === 'pullback'", polling=10)
        expect(page.locator('.gagoo-entrance-canvas')).to_have_attribute('data-continuity', 'home')
        assert page.evaluate("() => originalOrbit === document.querySelector('#orbit')")
        assert page.evaluate("() => getComputedStyle(document.querySelector('.gagoo-entrance')).backgroundColor === 'rgba(0, 0, 0, 0)'")
        page.screenshot(path=str(output / f'home-{width}-pullback.png'))
        page.wait_for_function("() => document.querySelector('.gagoo-entrance-canvas')?.dataset.phase === 'contact'", polling=10)
        page.screenshot(path=str(output / f'home-{width}-contact.png'))
        expect(target).to_have_css('visibility', 'hidden')
        page.keyboard.press('Escape')
        expect(page.locator('.gagoo-entrance')).to_have_count(0)
        expect(page).to_have_url(f'{base}/?lang=en#orbit')
        after = page.evaluate("""() => ({transform: originalOrbit.style.transform, origin: originalOrbit.style.transformOrigin,
          targetVisibility: document.querySelector('#gagoo-target').style.visibility,
          targetTransform: document.querySelector('#gagoo-target').style.transform,
          headerOpacity: document.querySelector('.public-header').style.opacity})""")
        assert before == after, {'before': before, 'after': after}
        expect(page.locator('#orbit-motion')).to_have_attribute('aria-pressed', 'true')
        expect(target).to_be_focused()
        page.screenshot(path=str(output / f'home-{width}-restored.png'))
        page.keyboard.press('Enter')
        expect(page.locator('#learn')).to_be_visible(timeout=15000)
        expect(page.locator('.gagoo-entrance')).to_have_count(0)
        expect(page.locator('#learn-title')).to_be_focused()
        assert not errors, errors
        return {'case': f'home-continuity-{width}', 'passed': True, 'same_home_nodes': True,
                'cancel_restores_styles': True, 'moved_position_preserved': True,
                'paused_state_preserved': True, 'page_errors': errors}
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='data/raw/gagoo-entrance-check')
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    class Server(ThreadingHTTPServer):
        request_queue_size = 128
        daemon_threads = True
    server = Server(('127.0.0.1', 0), partial(Handler, directory=str(ROOT / 'web')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for name in ['reduced', 'full', 'mobile', 'mobile-small', 'ultrawide', 'zero-canvas', 'clearance-timeout', 'skip', 'escape', 'cancel-button', 'signal', 'route', 'import-cancel', 'renderer-fallback', 'reentry', 'blinds-cancel', 'route-failure']:
                context = browser.new_context(viewport={'width': 3200 if name == 'ultrawide' else 320 if name == 'mobile-small' else 390 if name == 'mobile' else 1200, 'height': 80 if name == 'ultrawide' else 844})
                page = context.new_page()
                errors = []
                pending_routes = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                if name == 'import-cancel':
                    page.route('**/gagoo-scene.js*', lambda route: pending_routes.append(route))
                if name == 'renderer-fallback':
                    page.add_init_script("HTMLCanvasElement.prototype.getContext=function(){return null}")
                page.goto(f'http://127.0.0.1:{server.server_port}/__gagoo_test.html#orbit')
                page.wait_for_function('() => !!window.api')
                if name == 'clearance-timeout':
                    # Simulate an unusable projection without altering product code.
                    # The cinema must return home, not transition while uncleared.
                    page.evaluate("async () => {const T=await import('/assets/three-0.187.0/three.module.js');T.Vector3.prototype.project=function(){this.x=0;return this}}")
                page.locator('#start').focus()
                page.evaluate('(test)=>{window.start({reduced:test==="reduced"||test==="route-failure",fail:test==="route-failure"})}', name)
                if name not in ['reduced', 'route-failure']:
                    expect(page.locator('.gagoo-entrance')).to_be_visible()
                if name in ['full', 'mobile', 'mobile-small', 'ultrawide']:
                    page.wait_for_function("() => document.querySelector('canvas')?.dataset.phase === 'contact'", polling=10)
                    page.screenshot(path=str(output / f'{name}-contact.png'))
                    occupancy = json.loads(page.locator('canvas').get_attribute('data-window-occupancy'))
                    assert occupancy['width'] > .75 and occupancy['height'] > .75, occupancy
                    page.wait_for_function("() => document.querySelector('canvas')?.dataset.phase === 'slide'", polling=10)
                    page.wait_for_timeout(500)
                    assert float(page.locator('canvas').get_attribute('data-actor-x')) > .15
                    page.screenshot(path=str(output / f'{name}-slide.png'))
                    page.wait_for_function("() => document.querySelector('canvas')?.dataset.actorClear === 'true'", polling=10)
                    page.screenshot(path=str(output / f'{name}-clear.png'))
                elif name == 'skip':
                    page.get_by_role('button', name='Skip animation').click()
                elif name == 'zero-canvas':
                    page.wait_for_function("() => document.querySelector('canvas')?.dataset.phase === 'flight'", polling=10)
                    page.locator('canvas').evaluate("node=>{node.style.height='0px'}")
                elif name in ['escape', 'import-cancel']:
                    if name == 'import-cancel':
                        for _ in range(100):
                            if pending_routes:
                                break
                            page.wait_for_timeout(10)
                        assert pending_routes, 'The dynamic import must be pending before cancellation'
                    page.keyboard.press('Escape')
                elif name == 'cancel-button':
                    page.get_by_role('button', name='Cancel and go back').click()
                elif name == 'signal':
                    page.evaluate('window.controller.abort()')
                elif name == 'route':
                    page.evaluate("location.hash='elsewhere'")
                elif name == 'reentry':
                    page.evaluate("window.start({reduced:true})")
                elif name == 'blinds-cancel':
                    page.wait_for_function("() => document.querySelector('dialog')?.dataset.stage === 'blinds'", polling=10)
                    page.keyboard.press('Escape')
                page.wait_for_function('() => window.done?.completed === true' if name == 'reentry' else '() => window.done !== null || window.failure !== null', timeout=12000)
                if name == 'route-failure':
                    assert 'intentional route failure' in page.evaluate('window.failure')
                    expect(page.locator('.gagoo-entrance')).to_have_count(0)
                    expect(page.locator('#start')).to_be_focused()
                    results.append({'case': name, 'passed': True})
                    context.close()
                    continue
                assert page.evaluate('window.failure') is None
                if name in ['full', 'mobile', 'mobile-small', 'ultrawide']:
                    samples = page.evaluate('window.frameSamples')
                    held = [sample for sample in samples if sample.get('phase') in ['contact', 'slide', 'clear']]
                    assert len(held) > 10, 'The glass contact and slide must be rendered, not skipped'
                    # Loose joint motion cannot move the helmet away from or through
                    # the window. Character translation is horizontal to the right.
                    assert all(abs(float(sample['frontSurfaceZ']) - 2.92) < 1e-5 for sample in held)
                    assert all(abs(float(sample['actorY'])) < 1e-7 for sample in held)
                    xs = [float(sample['actorX']) for sample in held]
                    assert all(after >= before - 1e-7 for before, after in zip(xs, xs[1:])), xs
                    blinds = page.evaluate('window.blindsSample')
                    assert blinds['actorClear'] == 'true', 'Blinds started before Gagoo disappeared'
                    assert float(blinds['actorLeftEdge']) > float(blinds['clearanceEdge'])
                    (output / f'{name}-motion.json').write_text(json.dumps(samples, indent=2), encoding='utf-8')
                expect(page.locator('.gagoo-entrance')).to_have_count(0)
                cancelled = name in ['escape', 'cancel-button', 'signal', 'route', 'import-cancel', 'blinds-cancel', 'zero-canvas', 'clearance-timeout']
                if name != 'reentry':
                    assert page.evaluate('window.done.cancelled') == cancelled
                    assert page.evaluate('window.covered') == (0 if cancelled else 1)
                if name in ['escape', 'signal', 'import-cancel']:
                    expect(page.locator('#start')).to_be_focused()
                if name in ['zero-canvas', 'clearance-timeout']:
                    assert page.evaluate('window.blindsSample') is None
                    expect(page.locator('#start')).to_be_focused()
                    if name == 'clearance-timeout':
                        assert page.evaluate('window.elapsed') < 9000, 'Unclear actor left an unbounded animation loop'
                assert not errors, errors
                for route in pending_routes:
                    route.abort()
                if pending_routes:
                    page.wait_for_timeout(30)
                results.append({'case': name, 'passed': True, 'elapsed_ms': round(page.evaluate('window.elapsed'))})
                context.close()
            for width in (1366, 390):
                results.append(home_continuity_case(browser, f'http://127.0.0.1:{server.server_port}', output, width))
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    (output / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()

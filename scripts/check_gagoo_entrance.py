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
window.start=(options={})=>{
  window.done=null; window.covered=0; window.failure=null;
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
            super().do_GET()

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='data/raw/gagoo-entrance-check')
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT / 'web')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for name in ['reduced', 'full', 'mobile', 'mobile-small', 'skip', 'escape', 'cancel-button', 'signal', 'route', 'import-cancel', 'renderer-fallback', 'reentry', 'blinds-cancel', 'route-failure']:
                context = browser.new_context(viewport={'width': 320 if name == 'mobile-small' else 390 if name == 'mobile' else 1200, 'height': 844})
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                if name == 'import-cancel':
                    page.route('**/gagoo-scene.js', lambda route: None)
                if name == 'renderer-fallback':
                    page.add_init_script("HTMLCanvasElement.prototype.getContext=function(){return null}")
                page.goto(f'http://127.0.0.1:{server.server_port}/__gagoo_test.html#orbit')
                page.wait_for_function('!!window.api')
                page.locator('#start').focus()
                page.evaluate('(test)=>{window.start({reduced:test==="reduced"||test==="route-failure",fail:test==="route-failure"})}', name)
                if name not in ['reduced', 'route-failure']:
                    expect(page.locator('.gagoo-entrance')).to_be_visible()
                if name in ['full', 'mobile', 'mobile-small']:
                    page.wait_for_function("document.querySelector('canvas')?.dataset.phase === 'contact'", polling=10)
                    page.screenshot(path=str(output / f'{name}-contact.png'))
                elif name == 'skip':
                    page.get_by_role('button', name='Skip animation').click()
                elif name in ['escape', 'import-cancel']:
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
                    page.wait_for_function("document.querySelector('dialog')?.dataset.stage === 'blinds'", polling=10)
                    page.keyboard.press('Escape')
                page.wait_for_function('window.done?.completed === true' if name == 'reentry' else 'window.done !== null || window.failure !== null', timeout=12000)
                if name == 'route-failure':
                    assert 'intentional route failure' in page.evaluate('window.failure')
                    expect(page.locator('.gagoo-entrance')).to_have_count(0)
                    expect(page.locator('#start')).to_be_focused()
                    results.append({'case': name, 'passed': True})
                    context.close()
                    continue
                assert page.evaluate('window.failure') is None
                expect(page.locator('.gagoo-entrance')).to_have_count(0)
                cancelled = name in ['escape', 'cancel-button', 'signal', 'route', 'import-cancel', 'blinds-cancel']
                if name != 'reentry':
                    assert page.evaluate('window.done.cancelled') == cancelled
                    assert page.evaluate('window.covered') == (0 if cancelled else 1)
                if name in ['escape', 'signal', 'import-cancel']:
                    expect(page.locator('#start')).to_be_focused()
                assert not errors, errors
                results.append({'case': name, 'passed': True, 'elapsed_ms': round(page.evaluate('window.elapsed'))})
                context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    (output / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()

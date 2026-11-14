"""Desktop/mobile smoke checks against shipped data; no live IRSA or private writes.

Install requirements-browser.txt and run `python -m playwright install chromium`.
The default starts an ephemeral loopback static server, not the production API.
"""
import argparse
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import threading

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
mimetypes.add_type('image/webp', '.webp')


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Fault-injection tests and navigation intentionally cancel downloads.
            pass


@contextmanager
def local_site():
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'web')))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run_case(browser, base, output, mobile, language):
    name = f'{"mobile" if mobile else "desktop"}-{language}'
    context = browser.new_context(viewport={'width': 390 if mobile else 1366, 'height': 844 if mobile else 920},
                                  is_mobile=mobile, has_touch=mobile, reduced_motion='reduce')
    page = context.new_page()
    page.set_default_timeout(15000)
    errors, live_calls = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def refuse_live(route):
        live_calls.append(route.request.url.split('?')[0])
        route.abort()

    context.route('**/api/observations*', refuse_live)
    context.route('**/api/frame*', refuse_live)
    context.route('**/api/reviews*', refuse_live)
    context.tracing.start(screenshots=True, snapshots=True)
    try:
        page.goto(f'{base}/?lang={language}#orbit')
        earth = page.locator('.earth-target')
        if mobile:
            earth.tap(position={'x': 50, 'y': 80})
            expect(page).to_have_url(re.compile(r'#orbit$'))
            earth.tap(position={'x': 50, 'y': 80})
        else:
            earth.click(position={'x': 60, 'y': 80})
        expect(page).to_have_url(re.compile(r'#night-sky$'))
        expect(page.locator('#sky-targets button')).to_have_count(5)

        # Open the guided real-image lesson and verify both answer branches.
        page.goto(f'{base}/?lang={language}#field-guide')
        page.locator('#guided-open').click()
        expect(page.locator('#guided-body')).to_be_visible()
        cases = json.loads((ROOT / 'web/assets/mission/epsilon-sequence/activities.json').read_bytes())['cases']
        for index, item in enumerate(cases):
            for _ in range(8):
                if not page.locator('#guided-tour').is_visible():
                    break
                page.locator('#guided-tour-next').click()
            expect(page.locator('#guided-form')).to_be_visible()
            correct = item['answer']
            wrong = next(option['id'] for option in item['options'] if option['id'] != correct)
            page.locator(f'input[name="guided-answer"][value="{wrong}"]').check()
            expect(page.locator('#guided-feedback')).to_have_attribute('data-correct', 'false')
            page.locator('#guided-try-again').click()
            page.locator(f'input[name="guided-answer"][value="{correct}"]').check()
            expect(page.locator('#guided-feedback')).to_have_attribute('data-correct', 'true')
            if index + 1 < len(cases):
                page.locator('#guided-next').click()
        page.screenshot(path=str(output / f'{name}-lesson.png'))
        page.keyboard.press('Escape')
        expect(page.locator('#guided-activity')).not_to_be_visible()
        expect(page.locator('#guided-open')).to_be_focused()

        # Follow the public two-step workflow after the bundled image set is ready.
        page.goto(f'{base}/?lang={language}&flow_source=wise#home')
        page.wait_for_function('window.SkyApp?.context().ready === true')
        expect(page.locator('#workflow-data-next')).to_be_enabled()
        page.locator('#workflow-data-next').focus()
        page.keyboard.press('Enter')
        expect(page).to_have_url(re.compile(r'#compare-step$'))
        expect(page.locator('#step-compare-title')).to_be_visible()
        page.locator('[data-mode="side"]').click()
        canvas = page.locator('#sky')
        expect(canvas).to_be_visible()
        box = canvas.bounding_box()
        assert box['width'] >= 300 and box['height'] >= 140, 'Comparison image is too small'
        if mobile:
            heading = page.locator('#step-compare-title').bounding_box()
            nav = page.locator('.workflow-sidebar').bounding_box()
            assert heading['y'] >= nav['y'] + nav['height'] - 2, 'Mobile navigation covers the title'
        expect(page.locator('.workflow-sidebar [data-step-link]')).to_have_count(2)
        page.screenshot(path=str(output / f'{name}-images.png'))
        page.locator('.workflow-header [data-language]').click()
        expect(page.locator('html')).to_have_attribute('lang', 'vi' if language == 'en' else 'en')
        expect(page.locator('#step-compare-title')).to_be_visible()
        page.locator('.workflow-header [data-language]').click()
        expect(page.locator('html')).to_have_attribute('lang', language)
        expect(page.locator('.workflow-sidebar [data-step-link]')).to_have_count(2)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'Horizontal overflow'
        assert not errors, f'Browser errors: {errors}'
        assert not live_calls, f'Unexpected live API requests: {live_calls}'
        return {'case': name, 'passed': True, 'guided_cases': len(cases), 'page_errors': 0}
    except Exception:
        page.screenshot(path=str(output / f'{name}-failure.png'), full_page=True)
        raise
    finally:
        context.tracing.stop(path=str(output / f'{name}-trace.zip'))
        context.close()


def timeline_case(browser, base, output):
    context = browser.new_context(viewport={'width': 1366, 'height': 920}, reduced_motion='reduce')
    page = context.new_page()
    page.set_default_timeout(15000)
    errors, live_calls, full_frames, failed_requests = [], [], {}, []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('requestfailed', lambda request: failed_requests.append(request.url))

    def refuse_live(route):
        live_calls.append(route.request.url.split('?')[0])
        route.abort()

    context.route('**/api/observations*', refuse_live)
    context.route('**/api/frame*', refuse_live)

    def record_full_frame(response):
        marker = '/assets/mission/full-sequence/wise0855/'
        if marker in response.url:
            full_frames[response.url.split(marker, 1)[1]] = {
                'status': response.status,
                'content_type': response.headers.get('content-type', ''),
            }

    page.on('response', record_full_frame)
    try:
        page.goto(f'{base}/?lang=en&flow_source=irsa#home')
        expect(page.locator('#explorer-form')).to_be_visible()
        page.locator('#explorer-preset').select_option('wise0855')
        page.locator('#explorer-fov').select_option('0.10')
        page.locator('#explorer-release').select_option('dr1')
        page.locator('#explorer-detector').select_option('6')
        page.locator('#explorer-search').click()
        expect(page.locator('#explorer-image')).to_be_visible()
        expect(page.locator('#explorer-image')).to_have_js_property('naturalWidth', 2040)
        expect(page.locator('#explorer-image')).to_have_js_property('naturalHeight', 2040)
        expect(page.locator('#explorer-timeline')).to_be_enabled()
        page.locator('#explorer-timeline').focus()
        page.keyboard.press('Enter')
        expect(page.locator('#explorer-sequence-summary')).to_contain_text('All 5 frames are loaded', timeout=30000)
        expect(page.locator('#explorer-timeline')).to_have_text('Pause sequence')
        assert len(full_frames) == 5, f'Expected five full-resolution local images, got {len(full_frames)}'
        assert all(frame['status'] == 200 and frame['content_type'].startswith('image/webp')
                   for frame in full_frames.values()), f'Full-resolution image requests failed: {full_frames}'
        first_src = page.locator('#explorer-image').get_attribute('src')
        page.wait_for_function("first => document.querySelector('#explorer-image').src !== first", arg=first_src, timeout=5000)
        page.locator('#explorer-timeline').click()
        expect(page.locator('#explorer-timeline')).to_have_text('Resume sequence (5)')
        assert not errors, f'Browser errors: {errors}'
        assert not live_calls, f'Unexpected live API requests: {live_calls}'
        page.screenshot(path=str(output / 'desktop-en-timeline.png'))
        return {'case': 'desktop-en-timeline', 'passed': True, 'full_resolution_frames': len(full_frames), 'page_errors': 0}
    except Exception as error:
        print(json.dumps({
            'case': 'desktop-en-timeline',
            'error': str(error),
            'full_frame_responses': full_frames,
            'status': page.locator('#explorer-status').inner_text(),
            'failed_requests': failed_requests,
        }), flush=True)
        page.screenshot(path=str(output / 'desktop-en-timeline-failure.png'), full_page=True)
        raise
    finally:
        context.close()


def recovery_case(browser, base):
    context = browser.new_context(reduced_motion='reduce')
    page = context.new_page()
    requests = []

    def fail_once(route):
        requests.append(True)
        if len(requests) == 1:
            route.fulfill(status=503, content_type='application/json', body='{}')
        else:
            route.continue_()

    try:
        context.route('**/assets/mission/full-fields/provenance.json', fail_once)
        page.goto(f'{base}/?lang=en#night-sky')
        page.locator('#sky-retry').click()
        expect(page.locator('#sky-targets button')).to_have_count(5)
        assert len(requests) == 2, 'Retry did not issue exactly one new metadata request'
        return {'case': 'sky-retry', 'passed': True}
    finally:
        context.close()


def script_recovery_case(browser, base):
    context = browser.new_context(reduced_motion='reduce')
    page = context.new_page()
    requests = []

    def fail_once(route):
        requests.append(True)
        if len(requests) == 1:
            route.abort()
        else:
            route.continue_()

    try:
        context.route('**/app.js*', fail_once)
        page.goto(f'{base}/?lang=en&flow_source=wise#compare-step')
        page.locator('[data-copy="reloadPage"]').click()
        page.wait_for_function('window.SkyApp?.context().ready === true && !!window.SkyWorkflow')
        expect(page.locator('#workspace-progress')).not_to_be_visible()
        assert len(requests) == 2, 'Reload should retry the failed module exactly once'
        assert page.locator('script[src^="app.js"]').count() == 1, 'Duplicate module execution'
        page.locator('.workflow-header [data-language]').click()
        expect(page.locator('html')).to_have_attribute('lang', 'vi')
        return {'case': 'workspace-script-reload', 'passed': True}
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/raw/browser-smoke')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    with local_site() as base, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for mobile in (False, True):
                for language in ('en', 'vi'):
                    results.append(run_case(browser, base, args.output, mobile, language))
                    print(json.dumps(results[-1]), flush=True)
            results.append(timeline_case(browser, base, args.output))
            print(json.dumps(results[-1]), flush=True)
            results.append(recovery_case(browser, base))
            results.append(script_recovery_case(browser, base))
        finally:
            browser.close()
            (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print('Browser smoke passed: desktop/mobile, VI/EN, guided lesson, comparison, drafts and retry.')


if __name__ == '__main__':
    main()

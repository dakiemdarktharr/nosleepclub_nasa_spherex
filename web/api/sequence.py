"""Load a small, chronological group of public SPHEREx cutouts in parallel."""
from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler
import json
import math
import os
import re
import secrets
import time
from urllib.parse import urlencode

try:
    from api._access_control import AccessDenied, guard, identity
    from api._response_cache import cache_key
    from api.frame import FRAME_CONTRACT, MASK_POLICY, FrameError, parse_params, produce_frame, response_cache
    from api._telemetry import emit_request, request_logger
    from api._upstream_diagnostics import emit as emit_upstream
except ModuleNotFoundError as exc:
    if exc.name not in ('api', 'api._access_control', 'api._response_cache', 'api.frame', 'api._telemetry', 'api._upstream_diagnostics'):
        raise
    from web.api._access_control import AccessDenied, guard, identity
    from web.api._response_cache import cache_key
    from web.api.frame import FRAME_CONTRACT, MASK_POLICY, FrameError, parse_params, produce_frame, response_cache
    from web.api._telemetry import emit_request, request_logger
    from web.api._upstream_diagnostics import emit as emit_upstream

MAX_BODY_BYTES = 64_000
MAX_FRAMES = 10
MAX_CONCURRENT_FRAMES = 5
MAX_TOTAL_PNG_BYTES = 1_800_000
logger = request_logger('sequence_api')


def retry_delay(value):
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        seconds = .7
    if not math.isfinite(seconds):
        seconds = .7
    return min(2, max(.5, seconds))


def parse_request(body):
    if not isinstance(body, dict) or set(body) != {'ra', 'dec', 'fov_deg', 'zodi', 'low', 'high', 'frames'}:
        raise ValueError('invalid_parameters')
    frames = body['frames']
    if not isinstance(frames, list) or not 1 <= len(frames) <= MAX_FRAMES or body['zodi'] != 'subtract':
        raise ValueError('invalid_parameters')
    if any(isinstance(body[key], bool) for key in ('ra', 'dec', 'fov_deg', 'low', 'high')):
        raise ValueError('invalid_parameters')
    try:
        ra, dec, fov = float(body['ra']), float(body['dec']), float(body['fov_deg'])
        low, high = float(body['low']), float(body['high'])
    except (TypeError, ValueError):
        raise ValueError('invalid_parameters') from None
    if not (0 <= ra < 360 and -90 <= dec <= 90 and 0 < fov <= 0.40
            and low < high and abs(low) <= 1e9 and abs(high) <= 1e9):
        raise ValueError('invalid_parameters')
    parsed, indices, ids = [], set(), set()
    for item in frames:
        if not isinstance(item, dict) or set(item) != {'index', 'url'}:
            raise ValueError('invalid_parameters')
        index, url = item['index'], item['url']
        if (isinstance(index, bool) or not isinstance(index, int) or not 0 <= index <= 999
                or index in indices or not isinstance(url, str) or len(url) > 1200):
            raise ValueError('invalid_parameters')
        p = parse_params(urlencode({'url': url, 'ra': ra, 'dec': dec, 'fov_deg': fov, 'zodi': 'subtract',
                                    'low': low, 'high': high}))
        if p['obs_id'] in ids:
            raise ValueError('duplicate_observation')
        if parsed and (p['release'] != parsed[0][1]['release'] or p['detector'] != parsed[0][1]['detector']):
            raise ValueError('mixed_release_or_detector')
        parsed.append((index, p))
        indices.add(index)
        ids.add(p['obs_id'])
    return parsed


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, status, content, category=None, error_code=None):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Request-ID', self.request_id)
        commit = os.environ.get('VERCEL_GIT_COMMIT_SHA', '')
        if re.fullmatch(r'[0-9a-f]{40}', commit):
            self.send_header('X-App-Commit', commit)
        if status == 405:
            self.send_header('Allow', 'POST')
        if getattr(self, 'retry_after', None):
            self.send_header('Retry-After', str(self.retry_after))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(content)
        emit_request(logger, {'event': 'sequence_request', 'request_id': self.request_id, 'status': status,
                              'category': category or ('ok' if status < 400 else 'request_rejected'),
                              'error_code': error_code, 'method': self.command,
                              'latency_ms': round((time.monotonic() - self.started) * 1000, 2),
                              'frame_count': getattr(self, 'frame_count', 0)})

    def dispatch(self, method):
        self.request_id, self.started = secrets.token_hex(16), time.monotonic()
        if method != 'POST':
            return self.respond(405, b'{"error":"method_not_allowed"}', 'method', 'method_not_allowed')
        try:
            length = self.headers.get('Content-Length', '')
            if not re.fullmatch(r'[0-9]{1,6}', length) or int(length) > MAX_BODY_BYTES:
                raise ValueError('invalid_parameters')
            if self.headers.get('Content-Type', '').split(';', 1)[0].strip().lower() != 'application/json':
                raise ValueError('invalid_parameters')
            request = json.loads(self.rfile.read(int(length)))
            frames = parse_request(request)
            self.frame_count = len(frames)
            namespace, _ = identity(self.headers, self.client_address)
            guard('sequence', self.headers, self.client_address)
        except AccessDenied as exc:
            self.retry_after = exc.retry_after
            payload = json.dumps({'error': exc.code}, separators=(',', ':')).encode()
            return self.respond(exc.status, payload, 'rate_limit' if exc.status == 429 else 'rate_unavailable', exc.code)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return self.respond(400, b'{"error":"invalid_parameters"}', 'validation', 'invalid_parameters')

        def render_cached(params):
            key = cache_key(namespace, FRAME_CONTRACT + '/' + MASK_POLICY, params)
            for attempt in range(2):
                try:
                    return response_cache.run(key, lambda: produce_frame(params))
                except Exception as exc:
                    code, status = getattr(exc, 'code', None), getattr(exc, 'status', None)
                    transient = status in (502, 504) and code in (
                        'upstream_http_error', 'upstream_timeout', 'upstream_unavailable', 'upstream_incomplete')
                    if not transient or attempt:
                        raise
                    time.sleep(retry_delay(getattr(exc, 'retry_after', None)))

        results, errors = {}, []
        with ThreadPoolExecutor(max_workers=min(MAX_CONCURRENT_FRAMES, len(frames))) as pool:
            futures = {pool.submit(render_cached, params): index for index, params in frames}
            for future in as_completed(futures):
                index = futures[future]
                try:
                    (png, headers), cache_status = future.result()
                    results[index] = {'index': index, 'png': b64encode(png).decode('ascii'),
                                      'headers': {key.lower(): str(value) for key, value in headers.items()},
                                      'cache': cache_status}
                except Exception as exc:
                    code, status = getattr(exc, 'code', None), getattr(exc, 'status', None)
                    if isinstance(code, str) and re.fullmatch(r'[a-z0-9_]{1,64}', code) and isinstance(status, int):
                        if isinstance(exc, FrameError) and isinstance(exc.diagnostic, dict):
                            emit_upstream(logger, 'sequence', self.request_id, exc.diagnostic)
                        errors.append({'index': index, 'error': code, 'status': status})
                        continue
                    logger.error('sequence_frame_failed request_id=%s index=%s exception_type=%s',
                                 self.request_id, index, type(exc).__name__)
                    errors.append({'index': index, 'error': 'internal_error', 'status': 500})

        ordered = [results[index] for index, _ in frames if index in results]
        total = sum(len(item['png']) * 3 // 4 for item in ordered)
        if total > MAX_TOTAL_PNG_BYTES:
            return self.respond(413, b'{"error":"sequence_too_large"}', 'result_size', 'sequence_too_large')
        if not ordered:
            payload = json.dumps({'error': 'sequence_upstream_failed', 'frames': [], 'errors': errors},
                                 separators=(',', ':')).encode()
            return self.respond(502, payload, 'upstream', 'sequence_upstream_failed')
        payload = json.dumps({'frames': ordered, 'errors': errors}, separators=(',', ':'), allow_nan=False).encode()
        if len(payload) > 2_500_000:
            return self.respond(413, b'{"error":"sequence_too_large"}', 'result_size', 'sequence_too_large')
        return self.respond(200, payload, 'partial' if errors else 'ok', 'partial_upstream' if errors else None)

    def do_POST(self):
        self.dispatch('POST')

    def do_GET(self):
        self.dispatch('GET')

    def do_HEAD(self):
        self.dispatch('HEAD')

    def do_PUT(self):
        self.dispatch('PUT')

    def do_PATCH(self):
        self.dispatch('PATCH')

    def do_DELETE(self):
        self.dispatch('DELETE')

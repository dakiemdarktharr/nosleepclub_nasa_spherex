"""Read-only public asset delivery from the project's existing Mongo database.

Every path and byte is pinned by the deployed Git manifest. No client supplies
Mongo queries; this handler cannot read reviews, raw FITS or other collections.
"""
import base64
from collections import OrderedDict
from concurrent.futures import Future
from functools import lru_cache
from hashlib import sha256
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import re
import threading
import time
from uuid import uuid4
from urllib.parse import parse_qs, quote, urlencode, urlsplit

try:
    from api._access_control import database
    from api._telemetry import emit_request, request_logger
except ModuleNotFoundError as exc:
    if exc.name not in ('api', 'api._access_control'):
        raise
    from web.api._access_control import database
    from web.api._telemetry import emit_request, request_logger

HEX = re.compile(r'^[0-9a-f]{64}$')
LOGGER = request_logger('spherex.data')
CACHE_BYTES = 16 * 1024 * 1024
MAX_INFLIGHT = 16
MAX_WAITERS = 32
_cache = OrderedDict()
_inflight = {}
_cache_size = 0
_lock = threading.Lock()


@lru_cache(maxsize=1)
def manifest():
    return json.loads(Path(__file__).with_name('_data_manifest.json').read_bytes())


def parameters(query):
    if len(query) > 1024:
        raise ValueError('invalid_parameters')
    p = parse_qs(query, keep_blank_values=True, strict_parsing=True, max_num_fields=4)
    if set(p) - {'path', 'chunk', 'meta', 'v'} or any(len(v) != 1 for v in p.values()):
        raise ValueError('invalid_parameters')
    path = p.get('path', [''])[0]
    entry = manifest()['assets'].get(path)
    if entry is None:
        raise KeyError('unknown_asset')
    if 'v' in p and p['v'][0] != entry['stored_sha256']:
        raise ValueError('stale_asset_version')
    if 'meta' in p and (p['meta'] != ['1'] or 'chunk' in p):
        raise ValueError('invalid_parameters')
    chunk = None
    if 'chunk' in p:
        if not re.fullmatch(r'0|[1-9][0-9]{0,3}', p['chunk'][0]):
            raise ValueError('invalid_chunk')
        chunk = int(p['chunk'][0])
        if chunk >= len(entry['chunks']):
            raise ValueError('invalid_chunk')
    return path, entry, chunk, 'meta' in p


def read_chunk(part, db=None):
    row = (database() if db is None else db).public_asset_chunks.find_one({'_id': part['sha256']})
    if not row or row.get('size_bytes') != part['bytes']:
        raise RuntimeError('asset_unavailable')
    encoded = row.get('payload_b64')
    if not isinstance(encoded, str) or len(encoded) != 4 * ((part['bytes'] + 2) // 3):
        raise RuntimeError('asset_integrity_failure')
    try:
        payload = base64.b64decode(encoded, validate=True)
    except ValueError:
        raise RuntimeError('asset_integrity_failure')
    if len(payload) != part['bytes'] or sha256(payload).hexdigest() != part['sha256']:
        raise RuntimeError('asset_integrity_failure')
    return payload


def cached_chunk(part):
    """Only verified immutable bytes; coalesce same-hash reads in this instance."""
    global _cache_size
    key = (part['sha256'], part['bytes'])
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
        pending = _inflight.get(key)
        owner = pending is None
        if owner:
            if len(_inflight) >= MAX_INFLIGHT:
                raise RuntimeError('asset_reader_busy')
            pending = _inflight[key] = {'future': Future(), 'waiters': 0}
        else:
            if pending['waiters'] >= MAX_WAITERS:
                raise RuntimeError('asset_reader_busy')
            pending['waiters'] += 1
    if not owner:
        try:
            return pending['future'].result(timeout=15)
        finally:
            with _lock:
                pending['waiters'] -= 1
    try:
        payload = read_chunk(part)
        with _lock:
            if len(payload) <= CACHE_BYTES:
                while _cache and _cache_size + len(payload) > CACHE_BYTES:
                    _, removed = _cache.popitem(last=False)
                    _cache_size -= len(removed)
                _cache[key] = payload
                _cache_size += len(payload)
        pending['future'].set_result(payload)
        return payload
    except Exception as exc:
        pending['future'].set_exception(exc)
        raise
    finally:
        with _lock:
            _inflight.pop(key, None)


class handler(BaseHTTPRequestHandler):
    def reply(self, status, body, content_type='application/json; charset=utf-8', extra=None, cache=False):
        request_id = getattr(self, 'request_id', None) or uuid4().hex
        elapsed = (time.perf_counter() - getattr(self, 'started', time.perf_counter())) * 1000
        emit_request(LOGGER, {'event': 'data_request', 'request_id': request_id,
                             'method': self.command, 'status': status,
                             'category': getattr(self, 'category', 'ok' if status < 400 else 'request_rejected'),
                             'latency_ms': max(0, round(elapsed, 3))})
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        if status != 304:
            self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-App-Commit', os.environ.get('VERCEL_GIT_COMMIT_SHA', 'local'))
        self.send_header('X-Request-ID', request_id)
        self.send_header('Server-Timing', f'asset;dur={max(0, elapsed):.1f}')
        self.send_header('Cache-Control', 'public, max-age=31536000, immutable' if cache else 'no-store')
        if cache:
            self.send_header('Vercel-CDN-Cache-Control', 'public, s-maxage=86400')
        for key, value in (extra or {}).items():
            self.send_header(key, str(value))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        self.reply(405, b'{"error":"read_only"}', extra={'Allow': 'GET, HEAD'})

    do_PUT = do_DELETE = do_PATCH = do_POST

    def do_GET(self):
        self.started = time.perf_counter()
        self.request_id = uuid4().hex
        try:
            path, entry, chunk, metadata = parameters(urlsplit(self.path).query)
        except KeyError:
            return self.reply(404, b'{"error":"unknown_asset"}')
        except ValueError:
            return self.reply(400, b'{"error":"invalid_parameters"}')
        headers = {'X-Data-Source': 'mongodb', 'X-Data-SHA256': entry['sha256'],
                   'X-Data-Stored-SHA256': entry['stored_sha256']}
        versioned = parse_qs(urlsplit(self.path).query).get('v') == [entry['stored_sha256']]
        if metadata:
            body = json.dumps({'path': path, **entry}, separators=(',', ':')).encode()
            return self.reply(200, body, extra=headers, cache=versioned)
        if not versioned:
            query = {'path': path, 'v': entry['stored_sha256']}
            if chunk is not None:
                query['chunk'] = chunk
            return self.reply(307, b'', extra={'Location': '/api/data?' + urlencode(query)})
        if chunk is None and entry['stored_bytes'] > manifest()['direct_bytes']:
            return self.reply(307, b'', extra={'Location': '/download.html?' + urlencode({'path': path, 'v': entry['stored_sha256']})})
        try:
            parts = [entry['chunks'][chunk]] if chunk is not None else entry['chunks']
            body = b''.join(cached_chunk(part) for part in parts)
            expected = parts[0]['sha256'] if chunk is not None else entry['stored_sha256']
            if sha256(body).hexdigest() != expected:
                raise RuntimeError('asset_integrity_failure')
            headers['ETag'] = '"' + expected + '"'
            if chunk is not None:
                headers['X-Data-Chunk-SHA256'] = expected
                content_type = 'application/octet-stream'
            else:
                content_type = entry['content_type']
                headers['Content-Disposition'] = "inline; filename*=UTF-8''" + quote(path.rsplit('/', 1)[-1], safe='')
                if entry['encoding'] != 'identity':
                    headers['Content-Encoding'] = entry['encoding']
            if self.headers.get('If-None-Match') == headers['ETag']:
                return self.reply(304, b'', content_type, headers, cache=True)
            return self.reply(200, body, content_type, headers, cache=True)
        except Exception as exc:
            self.category = str(exc) if isinstance(exc, RuntimeError) and str(exc) in {
                'asset_unavailable', 'asset_integrity_failure', 'asset_reader_busy'
            } else 'asset_storage_unavailable'
            # Never expose driver errors, connection strings or collection data.
            return self.reply(503, b'{"error":"asset_unavailable"}', extra={'Retry-After': '10'})

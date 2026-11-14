"""Public, bounded point-in-time checks. No private records or notifications."""
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
import json
import os
import threading
import time

try:
    from api.data import manifest, read_chunk
    from api._access_control import database
    from api._health import recent
except ModuleNotFoundError as exc:
    if exc.name not in ('api', 'api.data'):
        raise
    from web.api.data import manifest, read_chunk
    from web.api._access_control import database
    from web.api._health import recent

_lock = threading.Lock()
_snapshot = None
_expires = 0


def snapshot():
    global _snapshot, _expires
    with _lock:
        if _snapshot is not None and time.monotonic() < _expires:
            return _snapshot
        started = time.perf_counter()
        state = 'available'
        history = {}
        try:
            entry = manifest()['assets']['data/manifest.json']
            for part in entry['chunks']:
                read_chunk(part)  # Deliberately bypass process cache for this small probe.
        except Exception:
            state = 'unavailable'
        try:
            from pymongo import timeout
            with timeout(1):
                history = recent(database())
        except Exception:
            pass
        _snapshot = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                     'commit': os.environ.get('VERCEL_GIT_COMMIT_SHA', 'local'),
                     'public_data': state, 'sample': 'data/manifest.json',
                     'probe_ms': round((time.perf_counter() - started) * 1000),
                     'irsa': 'not_checked', 'reviews': 'not_checked',
                     'recent_activity': history,
                     'scope': 'One pinned public metadata asset; not an uptime or all-assets guarantee.'}
        _expires = time.monotonic() + 60
        return _snapshot


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        value = snapshot()
        body = json.dumps(value, separators=(',', ':')).encode()
        remaining = max(0, min(60, int(datetime.fromisoformat(value['checked_at_utc']).timestamp() + 60 - time.time())))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', f'public, max-age={min(15, remaining)}')
        self.send_header('Vercel-CDN-Cache-Control', f'public, s-maxage={remaining}')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

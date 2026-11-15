"""Sparse, bounded health evidence. No user data; never fail an API request."""
from datetime import datetime, timezone
import os
import threading
import time

_lock = threading.Lock()
_last = {}
ENDPOINTS = {'data_request': 'data', 'frame_request': 'frame',
             'observations_request': 'observations', 'review_request': 'reviews'}


def record(event):
    if os.environ.get('VERCEL_ENV') != 'production':
        return
    endpoint = ENDPOINTS.get(event['event'])
    status = event['status']
    if not endpoint or 400 <= status < 500:
        return
    kind = 'error' if status >= 500 else 'success'
    key = (endpoint, kind)
    now = time.monotonic()
    with _lock:
        if now - _last.get(key, -1000) < (15 if kind == 'error' else 60):
            return
        _last[key] = now
    try:
        from pymongo import timeout
        try:
            from api._access_control import database
        except ModuleNotFoundError:
            from web.api._access_control import database
        # Adds at most 150 ms to an occasional origin request, no per-user rows.
        with timeout(.15):
            database().service_health.update_one({'_id': endpoint},
                {'$max': {f'last_{kind}_at': datetime.now(timezone.utc)}}, upsert=True)
    except Exception:
        pass  # Structured request logs remain the diagnostic source of record.


def recent(db):
    result = {}
    for row in db.service_health.find({'_id': {'$in': list(ENDPOINTS.values())}},
                                      {'last_success_at': 1, 'last_error_at': 1}).limit(4):
        result[row['_id']] = {key: value.isoformat() for key, value in row.items()
                              if key in {'last_success_at', 'last_error_at'} and isinstance(value, datetime)}
    return result

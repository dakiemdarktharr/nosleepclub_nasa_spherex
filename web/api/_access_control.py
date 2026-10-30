"""Bounded anonymous request budgets; no raw addresses or query data stored."""
from collections import OrderedDict
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import ipaddress
import os
import threading
import time

BUDGETS = {'observations': (12, 60), 'frame': (8, 24)}
BURST_LIMIT = 8
BURST_SECONDS = 1
MAX_BURST_KEYS = 4096
MAX_LOCAL_KEYS = 8192
_lock = threading.Lock()
_bursts = OrderedDict()
_counts = {}


class AccessDenied(Exception):
    def __init__(self, code, status, retry_after=None):
        self.code, self.status, self.retry_after = code, status, retry_after
        super().__init__(code)


def environment():
    value = os.environ.get('VERCEL_ENV')
    if value in ('production', 'preview', 'development'):
        return value
    if value or os.environ.get('VERCEL') == '1':
        raise AccessDenied('deployment_context_unavailable', 503)
    if os.environ.get('SPHEREX_LOCAL_API') == '1':
        return 'local'
    raise AccessDenied('deployment_context_unavailable', 503)


def address(headers, client_address, is_production):
    if is_production:
        # Vercel documents overwriting X-Forwarded-For. Reject chains and missing IP.
        raw = headers.get('X-Forwarded-For', '').strip()
    else:
        raw = client_address[0] if client_address else ''
    try:
        if not isinstance(raw, str) or len(raw) > 45 or '%' in raw:
            raise ValueError('invalid address')
        return ipaddress.ip_address(raw).compressed
    except ValueError:
        raise AccessDenied('rate_identity_unavailable', 503)


def hashed(value):
    return sha256(value.encode('ascii')).hexdigest()


@lru_cache(maxsize=1)
def database():
    from pymongo import MongoClient
    db = MongoClient(os.environ['MONGODB_URI'], serverSelectionTimeoutMS=4000,
                     connectTimeoutMS=4000, socketTimeoutMS=5000,
                     maxPoolSize=5, tz_aware=True).get_default_database()
    db.api_limits.create_index('expires_at', expireAfterSeconds=0)
    return db


def _burst(endpoint, ip_hash, now):
    window = int(now // BURST_SECONDS)
    key = (endpoint, ip_hash)
    with _lock:
        previous_window, count = _bursts.pop(key, (window, 0))
        count = count + 1 if previous_window == window else 1
        _bursts[key] = (window, count)
        while len(_bursts) > MAX_BURST_KEYS:
            _bursts.popitem(last=False)
    if count > BURST_LIMIT:
        raise AccessDenied('rate_limited', 429, max(1, int((window + 1) * BURST_SECONDS - now + 0.999)))


def _local(endpoint, namespace, minute, ip_hash, ip_limit, global_limit, retry):
    global_key = (namespace, endpoint, minute, 'global')
    ip_key = (namespace, endpoint, minute, ip_hash)
    with _lock:
        for key in list(_counts):
            if key[2] < minute - 1:
                del _counts[key]
        if global_key not in _counts and len(_counts) >= MAX_LOCAL_KEYS:
            raise AccessDenied('rate_storage_unavailable', 503)
        _counts[global_key] = _counts.get(global_key, 0) + 1
        if _counts[global_key] > global_limit:
            raise AccessDenied('rate_limited', 429, retry)
        if ip_key not in _counts and len(_counts) >= MAX_LOCAL_KEYS:
            raise AccessDenied('rate_storage_unavailable', 503)
        _counts[ip_key] = _counts.get(ip_key, 0) + 1
        if _counts[ip_key] > ip_limit:
            raise AccessDenied('rate_limited', 429, retry)


def _mongo(endpoint, namespace, minute, ip_hash, ip_limit, global_limit, retry):
    from pymongo import ReturnDocument
    db = database()
    expires = datetime.fromtimestamp((minute + 2) * 60, timezone.utc)
    def increment(scope):
        key = hashed(f'{namespace}|{endpoint}|{minute}|{scope}')
        row = db.api_limits.find_one_and_update({'_id': key},
            {'$inc': {'count': 1}, '$setOnInsert': {'expires_at': expires}},
            upsert=True, return_document=ReturnDocument.AFTER)
        return row['count']
    # Count globally first: once full, new IP documents cannot be created in this bucket.
    if increment('global') > global_limit:
        raise AccessDenied('rate_limited', 429, retry)
    if increment('ip|' + ip_hash) > ip_limit:
        raise AccessDenied('rate_limited', 429, retry)


def guard(endpoint, headers, client_address, now=None):
    if endpoint not in BUDGETS:
        raise AccessDenied('rate_storage_unavailable', 503)
    namespace = environment()
    is_production = namespace == 'production'
    ip = address(headers, client_address, is_production)
    timestamp = time.time() if now is None else now
    minute = int(timestamp // 60)
    retry = max(1, int((minute + 1) * 60 - timestamp + 0.999))
    uri_configured = bool(os.environ.get('MONGODB_URI'))
    if is_production and not uri_configured:
        raise AccessDenied('rate_storage_unavailable', 503)
    # Include minute in the digest, so stored identifiers do not link minutes.
    ip_hash = hashed(f'{namespace}|{endpoint}|{minute}|{ip}')
    _burst(endpoint, ip_hash, timestamp)
    ip_limit, global_limit = BUDGETS[endpoint]
    if not uri_configured:
        return _local(endpoint, namespace, minute, ip_hash, ip_limit, global_limit, retry)
    try:
        return _mongo(endpoint, namespace, minute, ip_hash, ip_limit, global_limit, retry)
    except AccessDenied:
        raise
    except Exception:
        raise AccessDenied('rate_storage_unavailable', 503)

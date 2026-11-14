"""Bounded in-process success cache and shared work for public, parsed queries.

No private records, addresses, request headers or errors are retained in entries.
Workers in different processes still rely on the shared quota and CDN cache.
"""
from collections import OrderedDict
from concurrent.futures import Future, TimeoutError
from hashlib import sha256
import json
import threading
import time

try:
    from api._access_control import AccessDenied
except ModuleNotFoundError as exc:
    if exc.name not in ('api', 'api._access_control'):
        raise
    from web.api._access_control import AccessDenied


def cache_key(namespace, contract, params):
    return sha256(json.dumps([namespace, contract, params], sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class ResponseCache:
    def __init__(self, ttl, max_bytes=16_000_000, max_entries=64, max_inflight=32,
                 max_waiters=32, wait_seconds=100, clock=time.monotonic):
        self.ttl, self.max_bytes, self.max_entries = ttl, max_bytes, max_entries
        self.max_inflight, self.max_waiters = max_inflight, max_waiters
        self.wait_seconds, self.clock = wait_seconds, clock
        self.lock = threading.Lock()
        self.entries, self.flights = OrderedDict(), {}
        self.size = 0

    def clear(self):
        # Used between isolated tests, never to evict active shared work.
        with self.lock:
            self.entries.clear()
            self.size = 0

    def run(self, key, produce):
        with self.lock:
            now = self.clock()
            for expired in [k for k, v in self.entries.items() if v[0] <= now]:
                self.size -= self.entries.pop(expired)[2]
            cached = self.entries.pop(key, None)
            if cached:
                self.entries[key] = cached
                return cached[1], 'hit'
            flight = self.flights.get(key)
            leader = flight is None
            if leader:
                if len(self.flights) >= self.max_inflight:
                    raise AccessDenied('service_busy', 503, 2)
                flight = {'future': Future(), 'waiters': 0}
                self.flights[key] = flight
            else:
                if flight['waiters'] >= self.max_waiters:
                    raise AccessDenied('service_busy', 503, 2)
                flight['waiters'] += 1
        if not leader:
            try:
                return flight['future'].result(timeout=self.wait_seconds), 'shared'
            except TimeoutError:
                raise AccessDenied('shared_request_timeout', 503, 2) from None
            finally:
                with self.lock:
                    flight['waiters'] -= 1
        try:
            result = produce()
            # Results are serialized bytes plus public provenance headers only.
            size = len(result[0]) + len(json.dumps(result[1], allow_nan=False).encode())
            with self.lock:
                if size <= self.max_bytes:
                    while self.entries and (self.size + size > self.max_bytes or len(self.entries) >= self.max_entries):
                        self.size -= self.entries.popitem(last=False)[1][2]
                    self.entries[key] = (self.clock() + self.ttl, result, size)
                    self.size += size
            flight['future'].set_result(result)
            return result, 'miss'
        except BaseException as exc:
            flight['future'].set_exception(exc)
            raise
        finally:
            with self.lock:
                self.flights.pop(key, None)

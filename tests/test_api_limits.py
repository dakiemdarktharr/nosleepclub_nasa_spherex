"""Shared quota, fail-closed and real handler integration tests without network."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.client import HTTPResponse
import json
import os
import threading
import types
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from web.api import _access_control as control
from tests import test_observations_api as observations_tests
from tests import test_frame_api as frame_tests


class AtomicCollection:
    def __init__(self):
        self.rows = {}
        self.lock = threading.Lock()
        self.indexes = []
    def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))
    def find_one_and_update(self, query, update, **kwargs):
        with self.lock:
            row = self.rows.setdefault(query['_id'], {'count': 0, **update['$setOnInsert']})
            row['count'] += 1
            return dict(row)


class ApiLimitTest(unittest.TestCase):
    def setUp(self):
        with control._lock:
            control._bursts.clear()
            control._counts.clear()
        self.addCleanup(self.clear_state)
        self.db = types.SimpleNamespace(api_limits=AtomicCollection())
        self.env = patch.dict(os.environ, {'VERCEL_ENV': 'production', 'MONGODB_URI': 'private-secret-uri'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.original_database = control.database.__wrapped__
        db = patch.object(control, 'database', return_value=self.db)
        db.start()
        self.addCleanup(db.stop)
        burst = patch.object(control, 'BURST_LIMIT', 10000)
        burst.start()
        self.addCleanup(burst.stop)

    @staticmethod
    def clear_state():
        with control._lock:
            control._bursts.clear()
            control._counts.clear()

    def attempt(self, endpoint, ip='203.0.113.1', now=6000):
        try:
            control.guard(endpoint, {'X-Forwarded-For': ip}, ('192.0.2.33', 1), now=now)
            return 200
        except control.AccessDenied as exc:
            return exc.status

    def test_concurrent_ip_and_global_budgets_are_atomic(self):
        with ThreadPoolExecutor(max_workers=20) as pool:
            statuses = list(pool.map(lambda _: self.attempt('observations'), range(30)))
        self.assertEqual(statuses.count(200), 12)
        self.assertEqual(statuses.count(429), 18)
        self.assertEqual(len(self.db.api_limits.rows), 2)
        with ThreadPoolExecutor(max_workers=20) as pool:
            statuses = list(pool.map(lambda n: self.attempt('frame', f'198.51.100.{n}'), range(1, 41)))
        self.assertEqual(statuses.count(200), 24)
        self.assertEqual(statuses.count(429), 16)
        self.assertEqual(len(self.db.api_limits.rows), 2 + 1 + 24)
        self.assertNotIn('198.51.100.', repr(self.db.api_limits.rows))
        self.assertNotIn('203.0.113.1', repr(self.db.api_limits.rows))
        for row in self.db.api_limits.rows.values():
            self.assertEqual(row['expires_at'], datetime.fromtimestamp(6120, timezone.utc))

    def test_headers_are_trusted_only_in_production_and_must_be_single_ip(self):
        self.assertEqual(control.address({'X-Forwarded-For': '203.0.113.1'}, ('192.0.2.33', 1), True), '203.0.113.1')
        self.assertEqual(control.address({'X-Forwarded-For': '203.0.113.1'}, ('192.0.2.33', 1), False), '192.0.2.33')
        for value in ('', '203.0.113.1, 198.51.100.1', 'garbage', 'fe80::1%eth0'):
            with self.subTest(value=value), self.assertRaises(control.AccessDenied) as denied:
                control.address({'X-Forwarded-For': value}, ('192.0.2.33', 1), True)
            self.assertEqual(denied.exception.status, 503)

    def test_fail_closed_production_and_in_memory_fallback(self):
        with patch.dict(os.environ, {'VERCEL_ENV': 'production'}, clear=True):
            self.assertEqual(self.attempt('frame'), 503)
        with patch.object(control, 'database', side_effect=RuntimeError('private-secret-uri')):
            self.assertEqual(self.attempt('frame', now=6120), 503)
        with patch.dict(os.environ, {'VERCEL_ENV': 'preview'}, clear=True):
            for _ in range(8):
                self.assertEqual(self.attempt('frame', now=6180), 200)
            self.assertEqual(self.attempt('frame', now=6180), 429)
            self.assertEqual(self.attempt('observations', now=6180), 200)
        self.assertNotIn('192.0.2.33', repr(control._counts))

    def test_burst_prefilter_avoids_extra_database_writes_and_is_bounded(self):
        with patch.object(control, 'BURST_LIMIT', 2), patch.object(control, 'MAX_BURST_KEYS', 3):
            self.assertEqual(self.attempt('frame'), 200)
            self.assertEqual(self.attempt('frame'), 200)
            self.assertEqual(self.attempt('frame'), 429)
            self.assertEqual(sum(row['count'] for row in self.db.api_limits.rows.values()), 4)
            for n in range(2, 6):
                self.attempt('frame', f'198.51.100.{n}')
            self.assertLessEqual(len(control._bursts), 3)

    def test_ttl_index_is_created(self):
        class MongoClient:
            def __init__(self, *args, **kwargs):
                pass
            def get_default_database(self):
                return db
        db = types.SimpleNamespace(api_limits=AtomicCollection())
        # Access the undecorated function to avoid affecting its shared client cache.
        with patch('pymongo.MongoClient', MongoClient):
            result = self.original_database()
        self.assertIs(result, db)
        self.assertEqual(db.api_limits.indexes[0], (('expires_at',), {'expireAfterSeconds': 0}))

    def test_handlers_reject_before_upstream_and_keep_endpoints_isolated(self):
        with patch.dict(os.environ, {'VERCEL_ENV': 'preview'}, clear=True):
            obs, frame = observations_tests.api, frame_tests.api
            with patch.object(obs, 'fetch', return_value=observations_tests.SAMPLE) as ofetch:
                self.assertEqual(observations_tests.request('/api/observations?ra=bad&dec=35')[0], 400)
                self.assertEqual(ofetch.call_count, 0)
                with self.assertLogs('observations_api', level='WARNING') as logs:
                    for _ in range(12):
                        self.assertEqual(observations_tests.request('/api/observations?ra=350&dec=35')[0], 200)
                    status, headers, body = observations_tests.request('/api/observations?ra=350&dec=35')
                self.assertEqual((status, body['error']), (429, 'rate_limited'))
                self.assertIn('Retry-After', headers)
                self.assertEqual(headers['Cache-Control'], 'no-store')
                self.assertIn('X-Request-ID', headers)
                self.assertEqual(ofetch.call_count, 12)
                self.assertNotIn('127.0.0.1', str(logs.output))
            path = '/api/frame?' + urlencode({'url': frame_tests.URL, 'ra': 350, 'dec': 35, 'fov_deg': .005})
            with patch.object(frame, 'fetch', return_value=frame_tests.synthetic()) as ffetch:
                for _ in range(8):
                    self.assertEqual(frame_tests.request(path)[0], 200)
                status, headers, body = frame_tests.request(path)
                self.assertEqual(status, 429)
                self.assertIn('Retry-After', headers)
                self.assertEqual(headers['Cache-Control'], 'no-store')
                self.assertIn('X-Request-ID', headers)
                self.assertEqual(ffetch.call_count, 8)

    def test_production_missing_identity_returns_503_without_upstream(self):
        obs = observations_tests.api
        with patch.object(obs, 'fetch') as fetch:
            status, headers, body = observations_tests.request('/api/observations?ra=350&dec=35')
        self.assertEqual((status, body['error']), (503, 'rate_identity_unavailable'))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        fetch.assert_not_called()

    def test_production_storage_error_is_sanitized_and_stops_upstream(self):
        obs = observations_tests.api
        request = (b'GET /api/observations?ra=350&dec=35 HTTP/1.1\r\n'
                   b'Host: demo.example\r\nX-Forwarded-For: 203.0.113.77\r\n\r\n')
        sock = observations_tests.MemorySocket(request)
        with patch.object(control, 'database', side_effect=RuntimeError('private-secret-uri')):
            with patch.object(obs, 'fetch') as fetch, self.assertLogs('observations_api', level='WARNING') as logs:
                obs.handler(sock, ('127.0.0.1', 1), None)
        response = HTTPResponse(observations_tests.MemorySocket(sock.output.getvalue()))
        response.begin()
        self.assertEqual(response.status, 503)
        self.assertEqual(json.loads(response.read()), {'error': 'rate_storage_unavailable'})
        self.assertNotIn('203.0.113.77', str(logs.output))
        self.assertNotIn('private-secret-uri', str(logs.output))
        fetch.assert_not_called()

    def test_local_capacity_fails_closed_and_minute_resets(self):
        with patch.dict(os.environ, {'VERCEL_ENV': 'preview'}, clear=True):
            with patch.object(control, 'MAX_LOCAL_KEYS', 1):
                self.assertEqual(self.attempt('frame', now=6000), 503)
            with control._lock:
                control._counts.clear()
            for _ in range(8):
                self.assertEqual(self.attempt('frame', now=6000), 200)
            self.assertEqual(self.attempt('frame', now=6000), 429)
            self.assertEqual(self.attempt('frame', now=6060), 200)

    def test_unknown_deployment_fails_closed_and_local_requires_opt_in(self):
        for env in ({}, {'VERCEL':'1'}, {'VERCEL':'1','SPHEREX_LOCAL_API':'1'}, {'VERCEL_ENV':'unknown'}):
            with self.subTest(env=env), patch.dict(os.environ,env,clear=True):
                with self.assertRaises(control.AccessDenied) as denied:
                    control.guard('frame',{},('127.0.0.1',1),now=7000)
                self.assertEqual(denied.exception.code,'deployment_context_unavailable')
        with patch.dict(os.environ,{'SPHEREX_LOCAL_API':'1'},clear=True):
            control.guard('frame',{},('127.0.0.1',1),now=7000)
        with patch.dict(os.environ,{'SPHEREX_LOCAL_API':'1','VERCEL_ENV':'production'},clear=True):
            with self.assertRaises(control.AccessDenied):
                control.guard('frame',{},('127.0.0.1',1),now=7000)


if __name__ == '__main__':
    unittest.main()

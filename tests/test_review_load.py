import json
import threading
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

import requests

from scripts import verify_review_load as load


MANIFEST = {'analysis_sha256': 'a' * 64,
            'scenes': [{'id': 'strict', 'motion': {'spectral_configuration': 'strict'},
                        'before': {'sha256': 'c' * 64}, 'after': {'sha256': 'd' * 64},
                        'target_detection': 'candidate_motion_unconfirmed'}]}


class Clock:
    def __init__(self):
        self.t = 0
    def __call__(self):
        return self.t
    def sleep(self, duration):
        self.t += duration


class Response:
    def __init__(self, data, commit=load.COMMIT, status=200):
        self.status_code = status
        self.headers = {'X-App-Commit': commit, 'X-Request-ID': 'b' * 32,
                        'Set-Cookie': '__Host-spherex-review=secret; Secure; HttpOnly; SameSite=Strict'}
        self.data = data
    def json(self):
        return self.data


class Server:
    def __init__(self, clock):
        self.clock = clock
        self.sessions = []
        self.calls = []
        self.fault = None
        self.lock = threading.Lock()
    def factory(self):
        session = Session(self, len(self.sessions))
        self.sessions.append(session)
        return session


class Session:
    def __init__(self, server, number):
        self.server, self.number = server, number
        self.scope = format(number + 1, '064x')
        self.rows = []
        self.count = 0
        self.trust_env = True
    def close(self):
        pass
    def request(self, method, url, **kwargs):
        assert url == load.BASE + '/api/reviews'
        assert kwargs['timeout'] == (5, 20) and not kwargs['allow_redirects'] and kwargs['verify']
        assert not self.trust_env
        with self.server.lock:
            self.count += 1
            self.server.calls.append((self.server.clock(), self.number, method))
            action = self.server.fault(self, method, kwargs) if self.server.fault else None
            if action == 'timeout':
                raise requests.Timeout('secret-cookie-and-note')
            if action == 'drift':
                return Response({}, commit='0' * 40)
            if action == 'status':
                return Response({}, status=503)
            scope = self.scope
            if method == 'POST':
                row = {**kwargs['json'], 'review_id': format(self.number + 100, '064x'),
                       'input_sha256': ['c' * 64, 'd' * 64], 'target_detection': 'candidate_motion_unconfirmed',
                       'expires_at': (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()}
                self.rows = [row]
                if action == 'commit_timeout':
                    raise requests.Timeout('secret')
                return Response({'saved': True, 'storage': 'mongodb', 'contract_version': '1.1',
                                 'session_scope': scope, 'review': row})
            if method == 'DELETE':
                assert kwargs['json']['review_id'] == self.rows[0]['review_id']
                self.rows = []
                if action == 'delete_timeout':
                    raise requests.Timeout('secret')
                return Response({'deleted': True})
            return Response({'storage': 'mongodb', 'contract_version': '1.1',
                             'session_scope': scope, 'reviews': list(self.rows)})


class ReviewLoadTests(unittest.TestCase):
    def setup_runner(self):
        clock = Clock()
        server = Server(clock)
        runner = load.Runner(MANIFEST, server.factory, clock, clock.sleep)
        return runner, server, clock

    def test_complete_isolation_wave_limits_and_receipt_privacy(self):
        runner, server, _ = self.setup_runner()
        result = runner.run()
        self.assertTrue(result['passed'])
        self.assertEqual((result['planned_attempts'], result['owners_cleanup_verified']), (60, 12))
        batches = {}
        for t, _, _ in server.calls:
            batches[t] = batches.get(t, 0) + 1
        self.assertEqual(len(batches), 20)
        self.assertTrue(all(n == 3 for n in batches.values()))
        self.assertTrue(all(b - a >= 6 for a, b in zip(sorted(batches), sorted(batches)[1:])))
        self.assertTrue(all(not s.rows for s in server.sessions))
        receipt = json.dumps(result)
        for owner in runner.owners:
            self.assertNotIn(owner['note'], receipt)
            self.assertNotIn(owner['scope'], receipt)
            self.assertNotIn(owner['id'], receipt)
        self.assertNotIn('secret', receipt)

    def test_actual_inflight_is_bounded_to_three(self):
        runner, server, _ = self.setup_runner()
        barrier, guard = threading.Barrier(3), threading.Lock()
        inflight = [0, 0]
        original = Session.request
        def measured(session, method, url, **kwargs):
            with guard:
                inflight[0] += 1
                inflight[1] = max(inflight)
            if session.count == 0:
                barrier.wait(timeout=3)
            try:
                return original(session, method, url, **kwargs)
            finally:
                with guard:
                    inflight[0] -= 1
        with patch.object(Session, 'request', measured):
            self.assertTrue(runner.run()['passed'])
        self.assertEqual(inflight[1], 3)

    def test_unrecognized_cleanup_row_is_never_deleted_and_stops(self):
        runner, server, _ = self.setup_runner()
        def fault(session, method, kw):
            if session.number == 0 and method == 'POST':
                session.rows = [{'note': 'existing user note', 'review_id': 'f' * 64}]
                return 'timeout'
            return None
        server.fault = fault
        result = runner.run()
        self.assertFalse(result['passed'])
        self.assertTrue(result['fatal'])
        self.assertEqual(server.sessions[0].rows[0]['note'], 'existing user note')
        self.assertFalse(any(n == 0 and m == 'DELETE' for _, n, m in server.calls))
        self.assertFalse(any(n >= 3 for _, n, _ in server.calls))
        self.assertIn('cleanup_unrecognized_row', [r['error'] for r in result['records']])

    def test_post_timeout_with_unknown_commit_is_discovered_and_deleted(self):
        runner, server, _ = self.setup_runner()
        server.fault = lambda session, method, kw: 'commit_timeout' if session.number == 0 and method == 'POST' else None
        result = runner.run()
        self.assertFalse(result['passed'])
        self.assertEqual(result['owners_cleanup_verified'], 12)
        self.assertFalse(server.sessions[0].rows)
        self.assertEqual([r['stage'] for r in result['records'] if r['owner'] == 0][-3:],
                         ['cleanup_get', 'cleanup_delete', 'cleanup_verify'])
        self.assertEqual(sum(r['error'] == 'transport_error' for r in result['records']), 1)

    def test_cleanup_delete_timeout_is_followed_by_empty_verification(self):
        runner, server, _ = self.setup_runner()
        def fault(session, method, kw):
            if session.number == 0 and method == 'POST':
                return 'commit_timeout'
            if session.number == 0 and method == 'DELETE':
                return 'delete_timeout'
            return None
        server.fault = fault
        result = runner.run()
        self.assertFalse(result['passed'])
        self.assertEqual(result['owners_touched'], 3)
        self.assertEqual(result['owners_cleanup_verified'], 3)
        self.assertEqual([r['stage'] for r in result['records'] if r['owner'] == 0][-3:],
                         ['cleanup_get', 'cleanup_delete', 'cleanup_verify'])

    def test_nonempty_and_duplicate_scope_are_never_written(self):
        for duplicate in (False, True):
            runner, server, _ = self.setup_runner()
            if duplicate:
                server.sessions[1].scope = server.sessions[0].scope
            else:
                server.sessions[0].rows = [{'note': 'existing user note'}]
            result = runner.run()
            self.assertFalse(result['passed'])
            self.assertTrue(result['fatal'])
            self.assertFalse(any(method != 'GET' for _, _, method in server.calls))
            if not duplicate:
                self.assertEqual(server.sessions[0].rows[0]['note'], 'existing user note')

    def test_two_errors_or_commit_drift_stop_next_wave(self):
        for failure in ('status', 'drift'):
            runner, server, _ = self.setup_runner()
            server.fault = lambda session, method, kw: failure if method == 'GET' and session.number < 2 else None
            result = runner.run()
            self.assertFalse(result['passed'])
            self.assertEqual(len(server.calls), 3)
            self.assertEqual(len(result['records']), 3)
            self.assertEqual(sum(bool(r['error']) for r in result['records']), 2)

    def test_metrics_include_failures_and_cold_calls(self):
        runner, server, clock = self.setup_runner()
        def fault(session, method, kw):
            if session.number == 0 and method == 'GET' and session.count == 1:
                clock.t += 9
                return 'status'
            return None
        server.fault = fault
        result = runner.run()
        record = next(r for r in result['records'] if r['owner'] == 0)
        self.assertEqual(record['latency_seconds'], 9)
        get_values = [r['latency_seconds'] for r in result['records'] if r['phase'] == 'planned' and r['method'] == 'GET']
        self.assertEqual(result['p95_get_seconds'], load.percentile(get_values))
        self.assertFalse(result['passed'])

    def test_design_mismatch_refused_before_network(self):
        with patch.object(load, 'design_value', return_value={'wrong': True}), \
             patch.object(load, 'DESIGN') as design:
            design.read_bytes.return_value = b'{}'
            with self.assertRaisesRegex(RuntimeError, 'design_mismatch'):
                load.check_committed()


if __name__ == '__main__':
    unittest.main()

"""Exercise review lifecycle through the real HTTP handler with an in-memory DB."""
from datetime import datetime, timedelta, timezone
from http.client import HTTPResponse
from io import BytesIO
import importlib.util
import json
import os
from pathlib import Path
import types
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('review_api', Path(__file__).resolve().parents[1] / 'web/api/reviews.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def matches(row, query):
    for key, value in query.items():
        if isinstance(value, dict) and '$gt' in value:
            if key not in row or not row[key] > value['$gt']:
                return False
        elif row.get(key) != value:
            return False
    return True


class Cursor(list):
    def limit(self, n):
        return Cursor(self[:n])


class Reviews:
    def __init__(self):
        self.rows = []

    def find(self, query, projection):
        rows = []
        for row in self.rows:
            if matches(row, query):
                if projection.get('key') == 1:
                    rows.append({'key': row['key']})
                else:
                    rows.append({k: v for k, v in row.items() if projection.get(k) != 0})
        return Cursor(rows)

    def find_one(self, query, projection, **kwargs):
        return next((row for row in self.rows if matches(row, query)), None)

    def count_documents(self, query, limit, **kwargs):
        return min(limit, sum(matches(row, query) for row in self.rows))

    def update_one(self, query, update, upsert, **kwargs):
        row = self.find_one(query, {})
        if row is None:
            row = dict(query)
            self.rows.append(row)
        row.update(update['$set'])

    def delete_one(self, query):
        row = self.find_one(query, {})
        if row is not None:
            self.rows.remove(row)


class Limits:
    def __init__(self):
        self.rows = {}

    def find_one_and_update(self, query, update, **kwargs):
        row = self.rows.setdefault(query['_id'], {'count': 0})
        row['count'] += 1
        return row


class Guard:
    def update_one(self, query, update, **kwargs):
        return types.SimpleNamespace(matched_count=1)


class Session:
    in_transaction = False
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def start_transaction(self, **kwargs):
        self.in_transaction = True
    def commit_transaction(self):
        self.in_transaction = False
    def abort_transaction(self):
        self.in_transaction = False


class Client:
    def start_session(self):
        return Session()


class MemorySocket:
    def __init__(self, request):
        self.input = BytesIO(request)
        self.output = BytesIO()

    def makefile(self, mode, *args, **kwargs):
        return self.input

    def sendall(self, data):
        self.output.write(data)


class ReviewHandlerTest(unittest.TestCase):
    def setUp(self):
        self.db = types.SimpleNamespace(reviews=Reviews(), limits=Limits(), review_guard=Guard(), client=Client())
        self.patches = [patch.object(api, 'database', return_value=self.db),
                        patch.dict(os.environ, {'MONGODB_URI': 'private-uri'})]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])

    def request(self, method, body=None, cookie=None, extra=None):
        headers = {'Host': 'demo.example', 'Origin': 'https://demo.example', 'X-Forwarded-For': '192.0.2.1'}
        if cookie:
            headers['Cookie'] = cookie
        if body is not None:
            body = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        headers.update(extra or {})
        if body is not None:
            headers['Content-Length'] = str(len(body))
        request = (f'{method} /api/reviews HTTP/1.1\r\n' +
                   ''.join(f'{k}: {v}\r\n' for k, v in headers.items()) + '\r\n').encode() + (body or b'')
        sock = MemorySocket(request)
        api.handler(sock, ('127.0.0.1', 1), None)
        response_sock = MemorySocket(sock.output.getvalue())
        response = HTTPResponse(response_sock, method=method)
        response.begin()
        payload = response.read()
        result = response.status, dict(response.getheaders()), json.loads(payload) if payload else None
        return result

    def session(self):
        status, headers, _ = self.request('GET')
        self.assertEqual(status, 200)
        return headers['Set-Cookie'].split(';')[0]

    def item(self):
        manifest = api.manifest()
        return {'scene_id': manifest['scenes'][0]['id'], 'selection': 'target', 'status': 'uncertain',
                'note': 'private-note', 'analysis_sha256': manifest['analysis_sha256']}

    def test_old_analysis_deletion_and_isolation_by_id_and_legacy(self):
        owner, stranger = self.session(), self.session()
        item = self.item()
        status, _, posted = self.request('POST', item, owner)
        self.assertEqual(status, 200)
        rid = posted['review']['review_id']
        self.assertEqual(self.request('GET', cookie=owner)[2]['reviews'][0]['review_id'], rid)
        self.request('DELETE', {'review_id': rid}, stranger)
        self.assertEqual(len(self.db.reviews.rows), 1)
        newer = dict(api.manifest(), analysis_sha256='f' * 64)
        with patch.object(api, 'manifest', return_value=newer):
            self.assertEqual(self.request('POST', item, owner)[0], 400)
            self.assertEqual(self.request('DELETE', {'review_id': rid}, owner)[0], 200)
        self.assertEqual(self.db.reviews.rows, [])
        self.request('POST', item, owner)
        with patch.object(api, 'manifest', return_value=newer):
            self.assertEqual(self.request('DELETE', item, owner)[0], 200)
        self.assertEqual(self.db.reviews.rows, [])

    def test_expiry_filter_and_limit_counts_only_live_reviews(self):
        cookie = self.session()
        item = self.item()
        self.request('POST', item, cookie)
        row = self.db.reviews.rows[0]
        row['expires_at'] = datetime.now(timezone.utc) - timedelta(seconds=1)
        result = self.request('GET', cookie=cookie)[2]
        self.assertEqual(result['reviews'], [])
        self.assertEqual(result['contract_version'], '1.1')
        self.assertEqual(self.request('POST', item, cookie)[0], 200)
        self.assertIn('expires_at', self.request('GET', cookie=cookie)[2]['reviews'][0])
        base = dict(self.db.reviews.rows[0])
        self.db.reviews.rows.extend({**base, 'key': f'extra-{i}'} for i in range(99))
        other = {**item, 'selection': 'target', 'scene_id': api.manifest()['scenes'][1]['id']}
        self.assertEqual(self.request('POST', other, cookie)[0], 409)
        self.assertEqual(self.request('POST', item, cookie)[0], 200)

    def test_validation_rate_headers_and_sanitized_logs(self):
        with self.assertLogs('review_api', level='WARNING') as captured:
            cookie = self.session()
            self.assertEqual(self.request('POST', self.item(), cookie, {'Origin': 'https://evil.example'})[0], 403)
            self.assertEqual(self.request('POST', {**self.item(), 'note': 'x' * 2001}, cookie)[0], 400)
            self.assertEqual(self.request('PUT', {}, cookie)[0], 405)
            self.db.limits.rows[next(iter(self.db.limits.rows))]['count'] = 90
            status, headers, body = self.request('GET', cookie=cookie)
            self.assertEqual((status, body['error']), (429, 'rate_limited'))
            self.assertEqual(headers['RateLimit-Remaining'], '0')
            self.assertIn('Retry-After', headers)
        logs = '\n'.join(captured.output)
        for secret in ('private-note', 'private-uri', '192.0.2.1', cookie):
            self.assertNotIn(secret, logs)
        event = json.loads(captured.output[-1].split(':', 2)[-1])
        self.assertEqual(event['category'], 'rate_limit')
        self.assertEqual(len(event['request_id']), 32)
        self.assertIn('latency_ms', event)

    def test_payload_provenance_and_type_validation(self):
        item = self.item()
        item.update(owner='someone_else', input_sha256=['forged'], target_detection=True)
        validated = api.validate_review(item)
        self.assertNotIn('owner', validated)
        self.assertNotEqual(validated['input_sha256'], ['forged'])
        for field, value in [('scene_id', {'$ne': None}), ('analysis_sha256', 'old'),
                             ('selection', 'unknown'), ('note', 'x' * 2001), ('status', {'$gt': ''})]:
            item = self.item()
            item[field] = value
            with self.assertRaises(ValueError):
                api.validate_review(item)

    def test_storage_failure_does_not_expose_exception(self):
        cookie = self.session()
        with patch.object(api, 'database', side_effect=RuntimeError('private-uri private-note')):
            with self.assertLogs('review_api', level='WARNING') as captured:
                status, headers, body = self.request('GET', cookie=cookie)
        self.assertEqual(status, 503)
        self.assertEqual(body, {'error': 'storage_unavailable'})
        self.assertIn('X-Request-ID', headers)
        self.assertNotIn('private-uri', str(captured.output))
        self.assertNotIn('private-note', str(captured.output))
        self.assertIn('dependency_or_internal', str(captured.output))

    def test_http_write_validation(self):
        cookie = self.session()
        self.assertEqual(self.request('POST', self.item())[0], 401)
        self.assertEqual(self.request('POST', self.item(), cookie, {'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.request('POST', {**self.item(), 'note': 'x' * 9000}, cookie)[0], 413)
        self.assertEqual(self.request('DELETE', {'review_id': {'$ne': None}}, cookie)[0], 400)
        status, headers, body = self.request('HEAD', cookie=cookie)
        self.assertEqual(status, 405)
        self.assertEqual(headers['Allow'], 'GET, POST, DELETE')
        self.assertIsNone(body)

    def test_unpaired_surrogate_is_rejected_before_storage(self):
        cookie = self.session()
        with patch.object(api, 'database') as database:
            status, _, body = self.request('POST', {**self.item(), 'note': '\ud800'}, cookie)
        self.assertEqual((status, body['error']), (400, 'invalid_review'))
        database.assert_not_called()

    def test_physical_global_limit_allows_edits_but_not_new_rows(self):
        first, second, third = self.session(), self.session(), self.session()
        item = self.item()
        with patch.object(api, 'GLOBAL_REVIEW_LIMIT', 2):
            self.assertEqual(self.request('POST', item, first)[0], 200)
            self.assertEqual(self.request('POST', item, second)[0], 200)
            self.assertEqual(self.request('POST', item, third)[2]['error'], 'storage_limit')
            self.assertEqual(self.request('POST', {**item, 'note': 'edited'}, first)[0], 200)
            self.db.reviews.rows[1]['expires_at'] = datetime.now(timezone.utc) - timedelta(seconds=1)
            self.assertEqual(self.request('POST', item, third)[2]['error'], 'storage_limit')
            self.assertEqual(self.request('POST', item, second)[0], 200)

    def test_resurrecting_expired_review_obeys_live_owner_limit(self):
        cookie = self.session()
        item = self.item()
        self.assertEqual(self.request('POST', item, cookie)[0], 200)
        old = self.db.reviews.rows[0]
        old['expires_at'] = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.db.reviews.rows.extend({**old, 'key': f'extra-{i}',
                                     'expires_at': datetime.now(timezone.utc) + timedelta(days=1)} for i in range(100))
        self.assertEqual(self.request('POST', item, cookie)[2]['error'], 'review_limit')

    def test_global_post_limit_preserves_reads_and_deletes(self):
        cookie = self.session()
        item = self.item()
        with patch.object(api, 'POST_GLOBAL_LIMIT', 2):
            self.assertEqual(self.request('POST', item, cookie)[0], 200)
            self.assertEqual(self.request('POST', item, cookie)[0], 200)
            status, headers, body = self.request('POST', item, cookie)
            self.assertEqual((status, body['error']), (429, 'rate_limited'))
            self.assertIn('Retry-After', headers)
            self.assertEqual(self.request('GET', cookie=cookie)[0], 200)
            self.assertEqual(self.request('DELETE', item, cookie)[0], 200)

    def test_transient_conflict_retries_transaction_from_guard(self):
        from pymongo.errors import OperationFailure
        class ConflictGuard(Guard):
            calls = 0
            def update_one(self, query, update, **kwargs):
                if 'session' in kwargs:
                    self.calls += 1
                    if self.calls == 1:
                        raise OperationFailure('conflict', details={'errorLabels': ['TransientTransactionError']})
                return super().update_one(query, update, **kwargs)
        self.db.review_guard = ConflictGuard()
        cookie = self.session()
        self.assertEqual(self.request('POST', self.item(), cookie)[0], 200)
        self.assertEqual(self.db.review_guard.calls, 2)
        self.assertEqual(len(self.db.reviews.rows), 1)

    def test_unknown_commit_is_not_retried_as_a_new_transaction(self):
        from pymongo.errors import OperationFailure
        class UnknownSession(Session):
            starts = 0
            commits = 0
            def start_transaction(self, **kwargs):
                self.starts += 1
                super().start_transaction(**kwargs)
            def commit_transaction(self):
                self.commits += 1
                labels = ['UnknownTransactionCommitResult'] if self.commits == 1 else ['TransientTransactionError']
                raise OperationFailure('private failure', details={'errorLabels': labels})
        session = UnknownSession()
        self.db.client = types.SimpleNamespace(start_session=lambda: session)
        cookie = self.session()
        with self.assertLogs('review_api', level='WARNING') as logs:
            status, _, body = self.request('POST', self.item(), cookie)
        self.assertEqual((status, body['error']), (503, 'save_outcome_unknown'))
        self.assertEqual((session.starts, session.commits), (1, 2))
        self.assertNotIn('private failure', str(logs.output))

    def test_unknown_commit_is_retried_on_same_transaction(self):
        from pymongo.errors import OperationFailure
        class UnknownThenCommitted(Session):
            starts = 0
            commits = 0
            def start_transaction(self, **kwargs):
                self.starts += 1
                super().start_transaction(**kwargs)
            def commit_transaction(self):
                self.commits += 1
                if self.commits == 1:
                    raise OperationFailure('ambiguous', details={'errorLabels': ['UnknownTransactionCommitResult']})
                super().commit_transaction()
        session = UnknownThenCommitted()
        self.db.client = types.SimpleNamespace(start_session=lambda: session)
        cookie = self.session()
        self.assertEqual(self.request('POST', self.item(), cookie)[0], 200)
        self.assertEqual((session.starts, session.commits), (1, 2))

    def test_missing_guard_fails_closed_before_upsert(self):
        class MissingGuard(Guard):
            def update_one(self, query, update, **kwargs):
                return types.SimpleNamespace(matched_count=0 if 'session' in kwargs else 1)
        self.db.review_guard = MissingGuard()
        cookie = self.session()
        status, _, body = self.request('POST', self.item(), cookie)
        self.assertEqual((status, body['error']), (503, 'storage_unavailable'))
        self.assertEqual(self.db.reviews.rows, [])

    def test_conflict_retries_are_bounded(self):
        from pymongo.errors import OperationFailure
        class ConflictGuard(Guard):
            calls = 0
            def update_one(self, query, update, **kwargs):
                if 'session' in kwargs:
                    self.calls += 1
                    raise OperationFailure('conflict', details={'errorLabels': ['TransientTransactionError']})
                return super().update_one(query, update, **kwargs)
        self.db.review_guard = ConflictGuard()
        cookie = self.session()
        self.assertEqual(self.request('POST', self.item(), cookie)[0], 503)
        self.assertEqual(self.db.review_guard.calls, api.MAX_TRANSACTION_ATTEMPTS)
        self.assertEqual(self.db.reviews.rows, [])

    def test_transaction_writes_shared_guard_before_counts_and_upsert(self):
        events = []
        class TracedGuard(Guard):
            def update_one(self, query, update, **kwargs):
                events.append('guard' if 'session' in kwargs else 'initialize')
                return super().update_one(query, update, **kwargs)
        class TracedReviews(Reviews):
            def find_one(self, query, projection, **kwargs):
                if 'session' in kwargs:
                    events.append('find')
                return super().find_one(query, projection, **kwargs)
            def count_documents(self, query, limit, **kwargs):
                self.assert_session(kwargs)
                events.append('owner_count' if 'owner' in query else 'global_count')
                return super().count_documents(query, limit, **kwargs)
            def update_one(self, query, update, upsert, **kwargs):
                self.assert_session(kwargs)
                events.append('upsert')
                return super().update_one(query, update, upsert, **kwargs)
            @staticmethod
            def assert_session(kwargs):
                if 'session' not in kwargs:
                    raise AssertionError('transaction operation lacks session')
        self.db.review_guard = TracedGuard()
        self.db.reviews = TracedReviews()
        cookie = self.session()
        self.assertEqual(self.request('POST', self.item(), cookie)[0], 200)
        self.assertEqual(events, ['initialize', 'guard', 'find', 'owner_count', 'global_count', 'upsert'])

    def test_commit_header_stays_available_and_is_validated(self):
        commit = 'a' * 40
        with patch.dict(os.environ, {'VERCEL_GIT_COMMIT_SHA': commit}):
            status, headers, _ = self.request('GET')
        self.assertEqual(status, 200)
        self.assertEqual(headers['X-App-Commit'], commit)
        with patch.dict(os.environ, {'VERCEL_GIT_COMMIT_SHA': 'bad-commit'}):
            self.assertNotIn('X-App-Commit', self.request('GET')[1])


if __name__ == '__main__':
    unittest.main()

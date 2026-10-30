"""Opt-in concurrency checks against a dedicated loopback MongoDB replica set.

Set REVIEW_TEST_MONGODB_URI=mongodb://127.0.0.1:27017/?directConnection=true
only for a disposable replica set named codex-review-test. Never use production.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib.util
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import unittest
from unittest.mock import patch
from uuid import uuid4

from pymongo import MongoClient, timeout
from pymongo.errors import PyMongoError

spec = importlib.util.spec_from_file_location('review_transactions_api', Path(__file__).resolve().parents[1] / 'web/api/reviews.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
TEST_URI = os.environ.get('REVIEW_TEST_MONGODB_URI')


@unittest.skipUnless(TEST_URI, 'Set REVIEW_TEST_MONGODB_URI for an isolated loopback replica set')
class ReplicaSetConcurrency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        uri = urlsplit(TEST_URI)
        options = parse_qs(uri.query)
        if (uri.scheme != 'mongodb' or uri.hostname != '127.0.0.1' or uri.username or uri.password or
                uri.path not in ('', '/') or uri.fragment or ',' in uri.netloc or
                options != {'directConnection': ['true']}):
            raise RuntimeError('Refusing non-loopback or non-isolated test URI')
        cls.client = MongoClient(TEST_URI, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000,
                                 socketTimeoutMS=5000, maxPoolSize=32, tz_aware=True)
        hello = cls.client.admin.command('hello')
        if hello.get('setName') != 'codex-review-test' or not hello.get('isWritablePrimary'):
            cls.client.close()
            raise RuntimeError('Expected writable disposable replica set codex-review-test')
        cls.dbname = 'codex_review_test_' + uuid4().hex
        cls.db = cls.client[cls.dbname]
        cls.db.reviews.create_index([('owner', 1), ('key', 1)], unique=True)
        # No TTL index here: keep synthetic expired rows physically present so
        # the test deterministically covers the pre-TTL-deletion state.

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'dbname', '').startswith('codex_review_test_'):
            cls.client.drop_database(cls.dbname)
        cls.client.close()

    def setUp(self):
        # The database name is randomly generated above for this test run only.
        self.db.reviews.delete_many({})
        self.db.review_guard.delete_many({})
        self.now = datetime.now(timezone.utc)
        self.item = {'scene_id': 'scene', 'selection': 'target', 'status': 'uncertain', 'note': 'synthetic',
                     'analysis_sha256': 'a' * 64, 'input_sha256': [], 'target_detection': 'unconfirmed'}

    def seed(self, owner, key, *, expired=False):
        self.db.reviews.insert_one({'owner': owner, 'key': key,
            'expires_at': self.now + timedelta(days=-1 if expired else 1)})

    def attempt(self, owner, key):
        try:
            with timeout(10):
                api.save_review(self.db, owner, key, self.item, self.now)
            return 'saved'
        except api.ReviewQuota as exc:
            return exc.code
        except PyMongoError:
            # A bounded conflict/timeout is fail-closed; do not mislabel it as success.
            return 'storage_unavailable'

    def test_simultaneous_owner_inserts_cannot_cross_live_cap(self):
        for i in range(4):
            self.seed('owner-a', f'old-{i}')
        with patch.object(api, 'OWNER_REVIEW_LIMIT', 5), patch.object(api, 'GLOBAL_REVIEW_LIMIT', 100):
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda i: self.attempt('owner-a', f'new-{i}'), range(8)))
        self.assertEqual(results.count('saved'), 1)
        self.assertEqual(self.db.reviews.count_documents({'owner': 'owner-a', 'expires_at': {'$gt': self.now}}), 5)
        self.assertTrue(all(x in ('saved', 'review_limit', 'storage_unavailable') for x in results))

    def test_simultaneous_distinct_owners_cannot_cross_physical_cap(self):
        for i in range(7):
            self.seed(f'old-owner-{i}', f'old-{i}', expired=(i == 0))
        with patch.object(api, 'OWNER_REVIEW_LIMIT', 5), patch.object(api, 'GLOBAL_REVIEW_LIMIT', 8):
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda i: self.attempt(f'new-owner-{i}', f'new-{i}'), range(8)))
            self.assertEqual(results.count('saved'), 1)
            self.assertEqual(self.db.reviews.count_documents({}), 8)
            # Editing an existing live key succeeds even at the physical cap.
            self.assertEqual(self.attempt('old-owner-1', 'old-1'), 'saved')
        self.assertTrue(all(x in ('saved', 'storage_limit', 'storage_unavailable') for x in results))

    def test_expired_existing_row_resurrection_obeys_owner_live_cap(self):
        self.seed('owner-a', 'expired', expired=True)
        for i in range(5):
            self.seed('owner-a', f'live-{i}')
        with patch.object(api, 'OWNER_REVIEW_LIMIT', 5), patch.object(api, 'GLOBAL_REVIEW_LIMIT', 6):
            self.assertEqual(self.attempt('owner-a', 'expired'), 'review_limit')
            self.assertEqual(self.attempt('owner-a', 'live-0'), 'saved')
        self.assertLessEqual(self.db.reviews.count_documents({'owner': 'owner-a', 'expires_at': {'$gt': self.now}}), 5)

    def test_concurrent_same_key_is_idempotent(self):
        with patch.object(api, 'OWNER_REVIEW_LIMIT', 1), patch.object(api, 'GLOBAL_REVIEW_LIMIT', 1):
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: self.attempt('owner-a', 'same-key'), range(8)))
        self.assertGreaterEqual(results.count('saved'), 1)
        self.assertEqual(self.db.reviews.count_documents({'owner': 'owner-a', 'key': 'same-key'}), 1)
        self.assertTrue(all(x in ('saved', 'storage_unavailable') for x in results))


if __name__ == '__main__':
    unittest.main()

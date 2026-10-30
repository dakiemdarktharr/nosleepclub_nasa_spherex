"""Opt-in encrypted backup drills on disposable loopback replica set only."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
import unittest
from uuid import uuid4

from bson import Binary, Int64, ObjectId
from cryptography.fernet import Fernet

from scripts import review_backup as backup

URI = os.environ.get('REVIEW_TEST_MONGODB_URI')


def now_ms():
    now = datetime.now(timezone.utc)
    return now.replace(microsecond=now.microsecond // 1000 * 1000)


def review(index, expires):
    return {'_id': ObjectId(), 'owner': format(index + 1, '064x'),
            'key': 'a' * 64 + f':scene{index}:target', 'note': 'synthetic-only',
            'status': 'uncertain', 'expires_at': expires,
            'extra': {'blob': Binary(bytes([index, 0]), subtype=128), 'count': Int64(2**40 + index), 'date': now_ms()}}


@unittest.skipUnless(URI, 'Set REVIEW_TEST_MONGODB_URI to a disposable loopback replica set')
class FixtureDrill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        backup.validate_uri(URI)
        cls.client = backup._fixture_client(URI)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def setUp(self):
        self.owned_names = []
        self.key = Fernet.generate_key()

    def dbname(self, source):
        prefix = 'review_backup_src_' if source else 'review_backup_dst_'
        name = prefix + uuid4().hex
        self.assertFalse(backup.database_exists(self.client, name))
        return name

    def tearDown(self):
        # Only test-created names checked absent before creation are eligible.
        for name in self.owned_names:
            self.assertRegex(name, r'^review_backup_(?:src|dst)_[a-f0-9]{32}$')
            self.client.drop_database(name)

    def test_real_source_to_independent_target_preserves_bson_and_indexes(self):
        source, target = self.dbname(True), self.dbname(False)
        db = self.client[source]
        collection = db.create_collection('reviews')
        self.owned_names.append(source)
        collection.create_index([('owner', 1), ('key', 1)], unique=True, name='owner_1_key_1')
        collection.create_index('expires_at', expireAfterSeconds=0, name='expires_at_1')
        expected = [review(0, now_ms() + timedelta(days=1)), review(1, now_ms() + timedelta(days=2))]
        collection.insert_many(expected)
        token = backup.snapshot_fixture(URI, source, self.key)
        self.assertFalse(b'synthetic-only' in token)
        receipt = backup.restore_fixture(URI, target, token, self.key)
        self.owned_names.append(target)
        self.assertEqual(receipt, {'snapshot_version': 1, 'restored_count': 2, 'excluded_expired_count': 0})
        actual = list(self.client[target].reviews.find({}).sort('_id', 1))
        expected.sort(key=lambda entry: entry['_id'])
        self.assertTrue(actual == expected, 'Restored BSON does not match source')
        self.assertEqual(actual[0]['expires_at'].utcoffset(), timedelta(0))
        self.assertEqual(type(actual[0]['extra']['count']), Int64)
        self.assertEqual(type(actual[0]['extra']['blob']), Binary)
        for old, new in zip(expected, actual):
            self.assertTrue(sha256((old['owner']+'\0'+old['key']).encode()).digest() ==
                            sha256((new['owner']+'\0'+new['key']).encode()).digest())
        indexes = {index['name']: index for index in self.client[target].reviews.list_indexes()}
        self.assertTrue(indexes['owner_1_key_1']['unique'])
        self.assertEqual(list(indexes['owner_1_key_1']['key'].items()), [('owner', 1), ('key', 1)])
        self.assertEqual(list(indexes['expires_at_1']['key'].items()), [('expires_at', 1)])
        self.assertEqual(indexes['expires_at_1']['expireAfterSeconds'], 0)
        with self.assertRaises(backup.BackupError) as error:
            backup.restore_fixture(URI, target, token, self.key)
        self.assertEqual(str(error.exception), 'target_exists')
        self.assertEqual(self.client[target].reviews.count_documents({}), 2)

    def test_expired_rows_and_auth_failures_never_restore(self):
        target, wrong_target, tampered_target = self.dbname(False), self.dbname(False), self.dbname(False)
        docs = [review(0, now_ms() - timedelta(days=1)), review(1, now_ms() + timedelta(days=1))]
        token = backup.seal_snapshot(docs, list(backup.REQUIRED_INDEXES), self.key)
        with self.assertRaises(backup.BackupError):
            backup.restore_fixture(URI, wrong_target, token, Fernet.generate_key())
        changed = bytearray(token); changed[len(changed)//2] = ord('A') if changed[len(changed)//2] != ord('A') else ord('B')
        with self.assertRaises(backup.BackupError):
            backup.restore_fixture(URI, tampered_target, bytes(changed), self.key)
        self.assertFalse(backup.database_exists(self.client, wrong_target))
        self.assertFalse(backup.database_exists(self.client, tampered_target))
        receipt = backup.restore_fixture(URI, target, token, self.key)
        self.owned_names.append(target)
        self.assertEqual(receipt['restored_count'], 1)
        self.assertEqual(receipt['excluded_expired_count'], 1)
        actual = list(self.client[target].reviews.find({}))
        self.assertTrue(actual == [docs[1]], 'Unexpected restored rows')
        self.assertEqual(self.client[target].reviews.count_documents({'_id': docs[0]['_id']}), 0)


if __name__ == '__main__':
    unittest.main()

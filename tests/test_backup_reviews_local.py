"""Manual backup crypto/schema checks and an opt-in isolated MongoDB restore drill."""
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from bson import Binary, Int64, ObjectId
from cryptography.fernet import Fernet

from scripts import backup_reviews_local as backup


def row(identity):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return {'_id': identity, 'owner': 'a' * 64, 'key': 'b' * 64 + ':scene:target',
            'note': 'synthetic-private-note', 'expires_at': now + timedelta(days=1),
            'extra': {'blob': Binary(b'\0\1', subtype=128), 'count': Int64(2**40), 'date': now}}


class LocalBackupTests(unittest.TestCase):
    def setUp(self):
        self.key = Fernet.generate_key()
        self.indexes = list(backup.fixture.REQUIRED_INDEXES)

    def test_round_trip_supports_both_production_identity_types(self):
        for identity in ('d' * 64, ObjectId()):
            document = row(identity)
            token = backup.seal([document], self.indexes, self.key)
            self.assertNotIn(b'synthetic-private-note', token)
            result = backup.unseal(token, self.key)
            self.assertEqual(result['documents'], [document])
            self.assertIsInstance(result['documents'][0]['extra']['count'], Int64)
            self.assertEqual(result['indexes'], self.indexes)

    def test_tampered_wrong_key_or_invalid_destination_never_connect(self):
        token = backup.seal([row('d' * 64)], self.indexes, self.key)
        local = 'mongodb://127.0.0.1:27027/?directConnection=true'
        with patch.object(backup.fixture, '_fixture_client') as client:
            for uri, content, key in [(local, token, Fernet.generate_key()),
                                      (local, token[:-10], self.key),
                                      ('mongodb+srv://secret.example/', token, self.key)]:
                with self.assertRaises(backup.BackupError):
                    backup.restore_drill(uri, content, key)
            client.assert_not_called()

    def test_existing_target_cannot_be_overwritten(self):
        token = backup.seal([row('d' * 64)], self.indexes, self.key)
        client = MagicMock()
        with patch.object(backup.fixture, '_fixture_client', return_value=client), patch.object(backup.fixture, 'database_exists', return_value=True):
            with self.assertRaisesRegex(backup.BackupError, '^target_exists$'):
                backup.restore_drill('mongodb://127.0.0.1:27027/?directConnection=true', token, self.key)
        client.__getitem__.assert_not_called()

    def test_unknown_database_refused_before_reading_reviews(self):
        client = MagicMock()
        client.get_default_database.return_value.name = 'other_database'
        with patch.object(backup, 'MongoClient', return_value=client):
            with self.assertRaisesRegex(backup.BackupError, '^unexpected_source_database$'):
                backup.snapshot_reviews('mongodb+srv://user:secret@example/', self.key)
        client.get_default_database.return_value.reviews.find.assert_not_called()

    def test_source_snapshot_reads_only_reviews_in_a_snapshot_transaction(self):
        document = row('d' * 64)
        client = MagicMock()
        db = client.get_default_database.return_value
        db.name = backup.SOURCE
        db.reviews.find.return_value.limit.return_value.batch_size.return_value = iter([document])
        with patch.object(backup, 'MongoClient', return_value=client), patch.object(backup.fixture, '_read_indexes', return_value=self.indexes):
            token = backup.snapshot_reviews('mongodb+srv://user:secret@example/nosleepclub_nasa_spherex', self.key)
        self.assertEqual(backup.unseal(token, self.key)['documents'], [document])
        self.assertEqual(db.reviews.find.call_args.args, ({},))
        self.assertIn('session', db.reviews.find.call_args.kwargs)
        db.reviews.insert_many.assert_not_called()
        db.reviews.create_index.assert_not_called()
        client.close.assert_called_once()

    def test_source_cannot_disable_certificate_validation(self):
        with patch.object(backup, 'MongoClient') as client, self.assertRaisesRegex(backup.BackupError, '^insecure_tls_options$'):
            backup.snapshot_reviews('mongodb+srv://example/db?tlsInsecure=true', self.key)
        client.assert_not_called()

    def test_duplicate_owner_key_invalid_expiry_and_limits_rejected(self):
        document = row('d' * 64)
        invalid = [[document, {**document, '_id': 'e' * 64}],
                   [{**document, 'expires_at': document['expires_at'].replace(tzinfo=None)}],
                   [{**document, '_id': 'arbitrary'}],
                   [{**document, 'note': 'x' * 40000}]]
        for documents in invalid:
            with self.assertRaises(backup.BackupError):
                backup.seal(documents, self.indexes, self.key)
        with patch.object(backup, 'MAX_DOCUMENTS', 0), self.assertRaises(backup.BackupError):
            backup.seal([document], self.indexes, self.key)

    @unittest.skipUnless(os.name == 'nt', 'Windows current-user DPAPI only')
    def test_actual_dpapi_key_is_reused_without_plaintext_on_disk(self):
        with tempfile.TemporaryDirectory(prefix='spherex-dpapi-test-') as directory:
            folder = Path(directory)
            key = backup.load_key(folder, create=True)
            self.assertEqual(key, backup.load_key(folder))
            protected = (folder / 'review-key.dpapi').read_bytes()
            self.assertNotIn(key, protected)
            with self.assertRaises(backup.BackupError):
                backup.dpapi(protected[:-8], False)


@unittest.skipUnless(os.environ.get('REVIEW_TEST_MONGODB_URI'), 'Disposable loopback MongoDB is not configured')
class LocalMongoDrillTests(unittest.TestCase):
    def test_real_isolated_restore_verifies_bson_indexes_and_expiry(self):
        uri = os.environ['REVIEW_TEST_MONGODB_URI']
        client = backup.fixture._fixture_client(uri)
        target = 'review_backup_dst_' + uuid4().hex
        self.assertFalse(backup.fixture.database_exists(client, target))
        key = Fernet.generate_key()
        live = row('d' * 64)
        expired = {**row(ObjectId()), 'key': 'b' * 64 + ':old:target',
                   'expires_at': datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=1)}
        token = backup.seal([live, expired], list(backup.fixture.REQUIRED_INDEXES), key)
        created = False
        try:
            receipt = backup.restore_drill(uri, token, key, target)
            created = True
            self.assertEqual(receipt['restored_count'], 1)
            self.assertEqual(receipt['excluded_expired_count'], 1)
            self.assertTrue(receipt['bson_verified'] and receipt['indexes_verified'])
            self.assertEqual(list(client[target].reviews.find({})), [live])
            with self.assertRaisesRegex(backup.BackupError, '^target_exists$'):
                backup.restore_drill(uri, token, key, target)
        finally:
            if created:
                client.drop_database(target)  # This test's UUID, verified absent before creation only.
            client.close()


if __name__ == '__main__':
    unittest.main()

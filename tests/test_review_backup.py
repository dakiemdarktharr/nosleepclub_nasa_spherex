"""Offline encryption/schema tests: synthetic BSON and mocked fixture boundary only."""
from datetime import datetime, timedelta, timezone
from contextlib import nullcontext
from hashlib import sha256
from unittest.mock import patch
import copy
import struct
import unittest
from uuid import uuid4

from bson import BSON, Binary, Int64, ObjectId
from bson.decimal128 import Decimal128
from cryptography.fernet import Fernet

from scripts import review_backup as backup


def now_ms():
    value = datetime.now(timezone.utc)
    return value.replace(microsecond=value.microsecond // 1000 * 1000)


def row(note='private synthetic note', expires=None):
    return {'_id': ObjectId(), 'owner': 'a' * 64, 'key': 'b' * 64 + ':scene:target',
            'note': note, 'expires_at': expires or now_ms() + timedelta(days=1),
            'nested': {'binary': Binary(b'\x00\x01', subtype=128), 'int64': Int64(2**40),
                       'decimal': Decimal128('1.234'), 'date': now_ms()}}


def indexes():
    return copy.deepcopy(list(backup.REQUIRED_INDEXES))


class EncryptedBackup(unittest.TestCase):
    def setUp(self):
        self.key = Fernet.generate_key()
        self.doc = row()

    def test_authenticated_bson_round_trip_preserves_identity_and_types(self):
        token = backup.seal_snapshot([self.doc], indexes(), self.key)
        self.assertFalse(b'private synthetic note' in token)
        self.assertFalse(self.doc['owner'].encode() in token)
        result = backup.open_snapshot(token, self.key)
        restored = result['documents'][0]
        self.assertEqual(result['version'], 1)
        self.assertTrue(restored == self.doc, 'BSON round-trip mismatch')
        self.assertEqual(type(restored['nested']['int64']), Int64)
        self.assertEqual(type(restored['nested']['binary']), Binary)
        self.assertEqual(type(restored['nested']['decimal']), Decimal128)
        self.assertEqual(restored['nested']['date'].utcoffset(), timedelta(0))
        self.assertTrue(sha256((restored['owner']+'\0'+restored['key']).encode()).digest() ==
                        sha256((self.doc['owner']+'\0'+self.doc['key']).encode()).digest())
        self.assertEqual(result['indexes'], indexes())

    def test_wrong_key_tampering_and_truncation_fail_before_client(self):
        token = backup.seal_snapshot([self.doc], indexes(), self.key)
        changed = bytearray(token); changed[len(changed)//2] = ord('A') if changed[len(changed)//2] != ord('A') else ord('B')
        target = 'review_backup_dst_' + uuid4().hex
        uri = 'mongodb://127.0.0.1:27027/?directConnection=true'
        with patch.object(backup, '_fixture_client') as client:
            for content, key in [(token, Fernet.generate_key()), (bytes(changed), self.key), (token[:-12], self.key)]:
                with self.subTest(length=len(content)), self.assertRaises(backup.BackupError) as error:
                    backup.restore_fixture(uri, target, content, key)
                self.assertEqual(str(error.exception), 'authentication_failed')
            client.assert_not_called()

    def test_bad_version_duplicate_rows_and_indexes_are_rejected_before_client(self):
        doc2 = copy.deepcopy(self.doc)
        doc3 = {**self.doc, '_id': ObjectId()}
        malformed = [
            {'version': 2, 'created_at': now_ms(), 'indexes': indexes(), 'documents': [self.doc]},
            {'version': 1, 'created_at': now_ms(), 'indexes': indexes(), 'documents': [self.doc, doc2]},
            {'version': 1, 'created_at': now_ms(), 'indexes': indexes(), 'documents': [self.doc, doc3]},
            {'version': 1, 'created_at': now_ms(), 'indexes': [indexes()[0], indexes()[0]], 'documents': [self.doc]},
            {'version': 1, 'created_at': now_ms(), 'indexes': [{**indexes()[0], 'unique': False}, indexes()[1]], 'documents': [self.doc]},
            {'version': 1, 'created_at': now_ms(), 'indexes': indexes(), 'documents': [{**self.doc, 'expires_at': 'bad'}]},
        ]
        with patch.object(backup, '_fixture_client') as client:
            for content in malformed:
                token = Fernet(self.key).encrypt(BSON.encode(content))
                with self.subTest(kind=content['version']), self.assertRaises(backup.BackupError):
                    backup.restore_fixture('mongodb://127.0.0.1:27027/?directConnection=true',
                                           'review_backup_dst_' + uuid4().hex, token, self.key)
            client.assert_not_called()

    def test_bounds_names_and_remote_uris_refused(self):
        for uri in ['mongodb://localhost:27027/?directConnection=true', 'mongodb://127.0.0.2:27027/?directConnection=true',
                    'mongodb://127.0.0.1:27027/', 'mongodb://127.0.0.1:27027/?directConnection=false',
                    'mongodb://name:secret@127.0.0.1:27027/?directConnection=true',
                    'mongodb://127.0.0.1:65536/?directConnection=true', 'mongodb+srv://example.com']:
            with self.subTest(uri=uri), self.assertRaises(backup.BackupError):
                backup.validate_uri(uri)
        for name in ['reviews', 'review_backup_src_' + 'a'*31, 'review_backup_src_' + 'A'*32,
                     'review_backup_src_' + 'a'*32, 'review_backup_dst_' + uuid4().hex]:
            with self.subTest(name=name), self.assertRaises(backup.BackupError):
                backup.validate_name(name, source=True)
        with patch.object(backup, 'MAX_DOCUMENTS', 0), self.assertRaises(backup.BackupError):
            backup.seal_snapshot([self.doc], indexes(), self.key)
        with patch.object(backup, 'MAX_DOCUMENT_BYTES', 500), self.assertRaises(backup.BackupError):
            backup.seal_snapshot([{**self.doc, 'note': 'x'*1000}], indexes(), self.key)
        with patch.object(backup, 'MAX_PLAINTEXT_BYTES', 100), self.assertRaises(backup.BackupError):
            backup.seal_snapshot([self.doc], indexes(), self.key)
        with patch.object(backup, 'MAX_CIPHERTEXT_BYTES', 100), self.assertRaises(backup.BackupError):
            backup.open_snapshot(b'x'*101, self.key)

    def test_unknown_index_and_ambiguous_bson_rejected(self):
        bad = indexes(); bad[0]['key'][0][1] = True
        with self.assertRaises(backup.BackupError):
            backup.seal_snapshot([self.doc], bad, self.key)
        with self.assertRaises(backup.BackupError):
            backup.seal_snapshot([{**self.doc, 'nested': {'unsafe': '\ud800'}}], indexes(), self.key)
        with self.assertRaises(backup.BackupError):
            backup.seal_snapshot([{**self.doc, 'expires_at': datetime.now()}], indexes(), self.key)
        with self.assertRaises(backup.BackupError):
            backup.open_snapshot(Fernet(self.key).encrypt(b'not BSON'), self.key)
        valid = BSON.encode({'version': 1, 'created_at': now_ms(), 'indexes': indexes(), 'documents': [self.doc]})
        duplicate_field = b'\x10version\x00' + struct.pack('<i', 1)
        duplicate = struct.pack('<i', len(valid) + len(duplicate_field)) + valid[4:-1] + duplicate_field + b'\x00'
        with patch.object(backup, '_fixture_client') as client:
            with self.assertRaises(backup.BackupError) as error:
                backup.restore_fixture('mongodb://127.0.0.1:27027/?directConnection=true',
                                       'review_backup_dst_' + uuid4().hex, Fernet(self.key).encrypt(duplicate), self.key)
            self.assertEqual(str(error.exception), 'invalid_snapshot')
            client.assert_not_called()

    def test_restore_filters_expired_rows_and_refuses_existing_target(self):
        class Collection:
            def __init__(self):
                self.rows = []; self.indexes = []
            def count_documents(self, query, limit):
                return len(self.rows)
            def create_index(self, keys, **kwargs):
                self.indexes.append(kwargs)
            def insert_many(self, rows, **kwargs):
                self.rows.extend(rows)
        class DB:
            def __init__(self):
                self.collection = Collection(); self.created = False
            def create_collection(self, name):
                self.created = True; return self.collection
            def list_collection_names(self):
                return ['reviews']
        class Session:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def start_transaction(self): return nullcontext()
        class Client:
            def __init__(self, exists=False):
                self.db = DB(); self.exists = exists
            def list_databases(self, *, filter, nameOnly):
                return nullcontext(iter([{'name': filter['name']}] if self.exists else []))
            def __getitem__(self, key): return self.db
            def start_session(self): return Session()
            def close(self): pass
        uri = 'mongodb://127.0.0.1:27027/?directConnection=true'
        target = 'review_backup_dst_' + uuid4().hex
        expired = row(expires=now_ms()-timedelta(days=1))
        future = {**row(expires=now_ms()+timedelta(days=1)), 'key': 'c'*64+':scene:target'}
        token = backup.seal_snapshot([expired, future], indexes(), self.key)
        client = Client()
        with patch.object(backup, '_fixture_client', return_value=client):
            receipt = backup.restore_fixture(uri, target, token, self.key)
        self.assertEqual(receipt['restored_count'], 1)
        self.assertEqual(receipt['excluded_expired_count'], 1)
        self.assertTrue(client.db.collection.rows == [future], 'Unexpected restored rows')
        self.assertEqual(len(client.db.collection.indexes), 2)
        existing = Client(exists=True)
        with patch.object(backup, '_fixture_client', return_value=existing):
            with self.assertRaises(backup.BackupError) as error:
                backup.restore_fixture(uri, target, token, self.key)
        self.assertEqual(str(error.exception), 'target_exists')
        self.assertFalse(existing.db.created)


if __name__ == '__main__':
    unittest.main()

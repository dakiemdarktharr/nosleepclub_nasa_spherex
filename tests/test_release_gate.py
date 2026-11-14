import base64
import gzip
from hashlib import sha256
import os
import unittest
from unittest.mock import patch
import zlib

from web import release_gate


class PublicCollection:
    def __init__(self, rows):
        self.rows = rows

    def find_one(self, query, projection):
        assert set(query) == {'_id'}
        assert projection == {'size_bytes': 1, 'payload_b64': 1}
        return self.rows.get(query['_id'])


def fixture(raw, encoding):
    stored = gzip.compress(raw, mtime=0) if encoding == 'gzip' else raw
    rows, chunks = {}, []
    for offset in range(0, len(stored), 113):
        block = stored[offset:offset + 113]
        digest = sha256(block).hexdigest()
        chunks.append({'bytes': len(block), 'sha256': digest})
        rows[digest] = {'size_bytes': len(block), 'payload_b64': base64.b64encode(block).decode()}
    return PublicCollection(rows), {'encoding': encoding, 'chunks': chunks,
        'bytes': len(raw), 'sha256': sha256(raw).hexdigest(),
        'stored_bytes': len(stored), 'stored_sha256': sha256(stored).hexdigest()}


class ReleaseGateTest(unittest.TestCase):
    def test_all_chunks_and_source_bytes_are_verified_with_bounded_decode(self):
        for encoding in ('identity', 'gzip'):
            collection, entry = fixture(b'science-data-with-repeated-content\n' * 50000, encoding)
            manifest = {'asset_count': 1, 'assets': {'data/test': entry}}
            self.assertEqual(release_gate.verify_manifest(collection, manifest),
                             {'assets': 1, 'stored_bytes': entry['stored_bytes'], 'passed': True})

    def test_missing_corrupt_or_incorrect_manifest_hash_prevents_release(self):
        for failure in ('missing', 'corrupt', 'stored', 'source', 'size', 'truncated'):
            collection, entry = fixture(b'public dataset\n' * 100, 'gzip')
            row = collection.rows[entry['chunks'][0]['sha256']]
            if failure == 'missing':
                collection.rows.clear()
            elif failure == 'corrupt':
                row['payload_b64'] = '!' * len(row['payload_b64'])
            elif failure == 'stored':
                entry['stored_sha256'] = '0' * 64
            elif failure == 'source':
                entry['sha256'] = '0' * 64
            elif failure == 'size':
                entry['bytes'] = 1
            else:
                blob = base64.b64decode(row['payload_b64'])[:-1]
                digest = sha256(blob).hexdigest()
                entry['chunks'] = [{'bytes': len(blob), 'sha256': digest}]
                collection.rows[digest] = {'size_bytes': len(blob), 'payload_b64': base64.b64encode(blob).decode()}
            with self.assertRaises((ValueError, zlib.error), msg=failure):
                release_gate.verify_asset(collection, entry)

    def test_preview_never_requires_production_secrets(self):
        with patch.dict(os.environ, {'VERCEL_ENV': 'preview'}, clear=True):
            self.assertIsNone(release_gate.production_gate())

    def test_production_without_connection_fails_closed_without_secret_output(self):
        with patch.dict(os.environ, {'VERCEL_ENV': 'production'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'Production data gate failed') as result:
                release_gate.production_gate()
            self.assertNotIn('MONGODB_URI', str(result.exception))


if __name__ == '__main__':
    unittest.main()

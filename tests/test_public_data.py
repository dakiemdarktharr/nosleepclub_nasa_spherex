from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
import base64
import gzip
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_data_manifest as package
from web import build_public
from web.api import data, data_import

ROOT = Path(__file__).resolve().parents[1]


class Collection:
    def __init__(self, rows=()):
        self.rows = {r['_id']: r for r in rows}

    def find_one(self, query):
        return self.rows.get(query['_id'])

    def update_one(self, query, update, upsert=False):
        if query['_id'] not in self.rows and upsert:
            self.rows[query['_id']] = {'_id': query['_id'], **update['$setOnInsert']}


class Database:
    def __init__(self):
        self.public_asset_chunks = Collection()
        self.public_asset_import_permits = Collection()


class PublicDataTest(unittest.TestCase):
    def setUp(self):
        self.raw = b'{"qualification":"synthetic control, no detection"}\n' * 10
        self.payload, self.encoding = package.encode(self.raw, '.json')
        self.digest = sha256(self.payload).hexdigest()
        self.part = {'sha256': self.digest, 'bytes': len(self.payload)}
        self.entry = {'sha256': sha256(self.raw).hexdigest(), 'stored_sha256': self.digest,
                      'bytes': len(self.raw), 'stored_bytes': len(self.payload),
                      'encoding': self.encoding, 'content_type': 'application/json', 'chunks': [self.part]}
        self.db = Database()
        self.manifest = {'assets': {'data/control.json': self.entry}, 'chunk_bytes': package.CHUNK_BYTES,
                         'direct_bytes': package.DIRECT_BYTES}

    def test_compression_keeps_exact_source_and_stable_header(self):
        self.assertEqual(gzip.decompress(self.payload), self.raw)
        self.assertEqual(self.payload[9], 255)
        self.assertEqual(package.encode(self.raw, '.json')[0], self.payload)
        self.assertEqual(package.encode(self.raw, '.gz'), (self.raw, 'identity'))

    def test_only_manifest_paths_and_bounded_single_parameters(self):
        with patch.object(data, 'manifest', return_value=self.manifest):
            for query in ('path=../reviews', 'path=data/control.json&path=data/control.json',
                          'path=data/control.json&chunk=-1', 'path=data/control.json&chunk=1',
                          'path=data/control.json&v=old', 'path=data/control.json&meta=1&chunk=0',
                          'path=data/control.json&collection=reviews'):
                with self.assertRaises((ValueError, KeyError), msg=query):
                    data.parameters(query)
            self.assertEqual(data.parameters('path=data/control.json&chunk=0')[2], 0)
            self.assertTrue(data.parameters('path=data/control.json&meta=1')[3])

    def test_insert_only_replay_and_corrupt_storage_refusal(self):
        with patch.object(data_import, 'manifest', return_value=self.manifest):
            data_import.put_chunk(self.db, self.digest, self.payload)
            data_import.put_chunk(self.db, self.digest, self.payload)
            self.assertEqual(len(self.db.public_asset_chunks.rows), 1)
            self.assertEqual(data.read_chunk(self.part, self.db), self.payload)
            with self.assertRaises(ValueError):
                data_import.put_chunk(self.db, self.digest, b'wrong')
            self.db.public_asset_chunks.rows[self.digest]['payload_b64'] = base64.b64encode(b'x' * len(self.payload)).decode()
            with self.assertRaises(RuntimeError):
                data.read_chunk(self.part, self.db)
            with self.assertRaises(ValueError):
                data_import.put_chunk(self.db, self.digest, self.payload)

    def test_capability_absent_wrong_expired_and_revoked_fail_closed(self):
        now = datetime(2026, 10, 31, tzinfo=timezone.utc)
        token = 'a' * 43
        headers = {'Authorization': 'Bearer ' + token}
        with patch.object(data_import, 'permit_id', return_value='manifest'):
            self.assertFalse(data_import.allowed(headers, self.db, now))
            self.db.public_asset_import_permits.rows['manifest'] = {'_id': 'manifest',
                'token_sha256': sha256(token.encode()).hexdigest(), 'issued_at': now.isoformat(),
                'expires_at': (now + timedelta(minutes=1)).isoformat()}
            self.assertTrue(data_import.allowed(headers, self.db, now))
            self.assertFalse(data_import.allowed({'Authorization': 'Bearer ' + 'b' * 43}, self.db, now))
            self.assertFalse(data_import.allowed(headers, self.db, now + timedelta(minutes=2)))
            self.db.public_asset_import_permits.rows.clear()
            self.assertFalse(data_import.allowed(headers, self.db, now))

    def response(self, path, method='GET', headers=None, body=b''):
        h = object.__new__(data.handler)
        if 'v=' not in path and 'meta=' not in path and 'path=data/control.json' in path:
            path += '&v=' + self.digest
        h.path = path; h.command = method; h.headers = headers or {}; h.wfile = BytesIO(); h.rfile = BytesIO(body)
        result = {'headers': {}}
        h.send_response = lambda status: result.update(status=status)
        h.send_header = lambda key, value: result['headers'].update({key: value})
        h.end_headers = lambda: None
        with patch.object(data, 'manifest', return_value=self.manifest), patch.object(data, 'database', return_value=self.db):
            getattr(h, 'do_' + method)()
        result['body'] = h.wfile.getvalue()
        return result

    def test_http_exact_gzip_chunk_cache_and_no_private_write(self):
        self.db.public_asset_chunks.rows[self.digest] = {'_id': self.digest, 'size_bytes': len(self.payload),
            'payload_b64': base64.b64encode(self.payload).decode()}
        r = self.response('/api/data?path=data/control.json')
        self.assertEqual(r['status'], 200)
        self.assertEqual(r['headers']['Content-Encoding'], 'gzip')
        self.assertEqual(gzip.decompress(r['body']), self.raw)
        self.assertEqual(r['headers']['X-Data-Source'], 'mongodb')
        self.assertEqual(r['headers']['Content-Disposition'], "inline; filename*=UTF-8''control.json")
        r = self.response('/api/data?path=data/control.json&chunk=0')
        self.assertNotIn('Content-Encoding', r['headers'])
        self.assertEqual(r['body'], self.payload)
        cached = self.response('/api/data?path=data/control.json', headers={'If-None-Match': '"' + self.digest + '"'})
        self.assertEqual(cached['status'], 304)
        self.assertNotIn('Content-Length', cached['headers'])
        self.assertEqual(self.response('/api/data?path=reviews')['status'], 404)
        self.assertEqual(self.response('/api/data?path=data/control.json', method='POST')['status'], 405)
        self.db.public_asset_chunks.rows.clear()
        failed = self.response('/api/data?path=data/control.json')
        self.assertEqual(failed['status'], 503)
        self.assertEqual(failed['headers']['Cache-Control'], 'no-store')
        self.assertNotIn('Vercel-CDN-Cache-Control', failed['headers'])

    def test_large_archive_redirect_does_not_read_database(self):
        self.entry['stored_bytes'] = package.DIRECT_BYTES + 1
        r = self.response('/api/data?path=data/control.json')
        self.assertEqual(r['status'], 307)
        self.assertTrue(r['headers']['Location'].startswith('/download.html?path='))

    def test_unversioned_metadata_is_never_cached(self):
        r = self.response('/api/data?path=data/control.json&meta=1')
        self.assertEqual(r['status'], 200)
        self.assertEqual(r['headers']['Cache-Control'], 'no-store')

    def test_static_build_excludes_datasets_and_api(self):
        with tempfile.TemporaryDirectory() as temp:
            build_public.build(ROOT / 'web', Path(temp))
            self.assertFalse((Path(temp) / 'data').exists())
            self.assertFalse((Path(temp) / 'api').exists())
            for name in ('index.html', 'download.html', 'data-download.js', 'draft-store.js'):
                self.assertTrue((Path(temp) / name).is_file())

    def test_production_cutover_routes_and_static_output_are_explicit(self):
        config = json.loads((ROOT / 'web/vercel.json').read_bytes())
        self.assertEqual(config['buildCommand'], 'python build_public.py')
        self.assertEqual(config['outputDirectory'], 'public')
        self.assertNotIn('rewrites', config)
        self.assertEqual(config['redirects'], package.redirects(json.loads(package.MANIFEST.read_bytes())))
        self.assertIn('name="data-origin" content="mongodb"', (ROOT / 'web/index.html').read_text(encoding='utf-8'))

    def test_committed_manifest_retains_all_public_product_hashes(self):
        value = json.loads(package.MANIFEST.read_bytes())
        self.assertEqual(value['asset_count'], 213)
        for name, entry in value['assets'].items():
            # No private/raw products and all transport parts are below 4.5 MB.
            self.assertTrue(name.startswith('data/'))
            blob = subprocess.check_output(['git', 'show', 'HEAD:web/' + name], cwd=ROOT)
            self.assertEqual(sha256(blob).hexdigest(), entry['sha256'], name)
            self.assertEqual(sum(p['bytes'] for p in entry['chunks']), entry['stored_bytes'])
            self.assertTrue(all(0 < p['bytes'] <= package.CHUNK_BYTES for p in entry['chunks']))


if __name__ == '__main__':
    unittest.main()

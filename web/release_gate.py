"""Read-only production gate: every pinned public asset must exist and verify.

The gate reads only public_asset_chunks. It neither changes MongoDB nor reads
reviews. Hashing is streamed with one stored chunk and a bounded decode buffer.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import zlib

CHUNK_LIMIT = 524288
DECODE_LIMIT = 65536
DIGEST = re.compile(r'[0-9a-f]{64}')


def verify_asset(collection, entry):
    stored_hash, source_hash = sha256(), sha256()
    stored_bytes = source_bytes = 0
    encoding = entry['encoding']
    if encoding not in ('identity', 'gzip'):
        raise ValueError('unsupported_encoding')
    decoder = zlib.decompressobj(31) if encoding == 'gzip' else None

    def decoded(block):
        nonlocal source_bytes
        source_bytes += len(block)
        if source_bytes > entry['bytes']:
            raise ValueError('source_size_mismatch')
        source_hash.update(block)

    for part in entry['chunks']:
        size, digest = part['bytes'], part['sha256']
        if type(size) is not int or not 0 < size <= CHUNK_LIMIT or not DIGEST.fullmatch(digest):
            raise ValueError('invalid_manifest_chunk')
        row = collection.find_one({'_id': digest}, {'size_bytes': 1, 'payload_b64': 1})
        if not row or row.get('size_bytes') != size:
            raise ValueError('missing_chunk')
        encoded = row.get('payload_b64')
        if not isinstance(encoded, str) or len(encoded) != 4 * ((size + 2) // 3):
            raise ValueError('invalid_chunk_encoding')
        block = base64.b64decode(encoded, validate=True)
        if len(block) != size or sha256(block).hexdigest() != digest:
            raise ValueError('chunk_hash_mismatch')
        stored_bytes += size
        stored_hash.update(block)
        if decoder is None:
            decoded(block)
        else:
            pending = block
            while pending:
                decoded(decoder.decompress(pending, DECODE_LIMIT))
                pending = decoder.unconsumed_tail
            if decoder.unused_data:
                raise ValueError('unexpected_gzip_data')
    if decoder is not None:
        if not decoder.eof:
            raise ValueError('incomplete_gzip')
    if stored_bytes != entry['stored_bytes'] or stored_hash.hexdigest() != entry['stored_sha256']:
        raise ValueError('stored_hash_mismatch')
    if source_bytes != entry['bytes'] or source_hash.hexdigest() != entry['sha256']:
        raise ValueError('source_hash_mismatch')
    return stored_bytes


def verify_manifest(collection, manifest, workers=4):
    entries = list(manifest['assets'].values())
    if not entries or len(entries) != manifest['asset_count']:
        raise ValueError('invalid_manifest_count')
    with ThreadPoolExecutor(max_workers=workers) as pool:
        sizes = list(pool.map(lambda entry: verify_asset(collection, entry), entries))
    return {'assets': len(sizes), 'stored_bytes': sum(sizes), 'passed': True}


def production_gate(root=None):
    if os.environ.get('VERCEL_ENV') != 'production' and os.environ.get('SPHEREX_VERIFY_RELEASE_DATA') != '1':
        return None
    root = Path(__file__).resolve().parent if root is None else Path(root)
    # Do not print driver errors: they may contain connection details.
    try:
        from pymongo import MongoClient
        uri = os.environ['MONGODB_URI']
        value = json.loads((root / 'api/_data_manifest.json').read_bytes())
        with MongoClient(uri, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000,
                         socketTimeoutMS=30000, maxPoolSize=4) as client:
            result = verify_manifest(client.get_default_database().public_asset_chunks, value)
    except Exception:
        raise RuntimeError('Production data gate failed: public assets could not be verified; keep the current release.') from None
    print('Production data gate: ' + json.dumps(result, sort_keys=True), flush=True)
    return result


if __name__ == '__main__':
    production_gate()

"""Package only committed public demo products for content-addressed Mongo storage.

No credentials, network access, private reviews, raw FITS or reserved fields.
Compression is transport only; the original Git blob hash is retained.
"""
from __future__ import annotations
import argparse
import base64
import gzip
from hashlib import sha256
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CHUNK_BYTES = 512 * 1024
DIRECT_BYTES = 4 * 1024 * 1024
MANIFEST = ROOT / 'web/api/_data_manifest.json'
CACHE = ROOT / 'data/raw/asset-migration'
TYPES = {'.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml',
         '.png': 'image/png', '.jpg': 'image/jpeg', '.csv': 'text/csv; charset=utf-8',
         '.txt': 'text/plain; charset=utf-8', '.gz': 'application/gzip',
         '.npz': 'application/octet-stream', '.fits': 'application/fits'}


def encode(raw, suffix):
    if suffix in ('.json', '.svg', '.csv', '.txt'):
        compressed = gzip.compress(raw, compresslevel=9, mtime=0)
        compressed = compressed[:9] + b'\xff' + compressed[10:]
        if len(compressed) + 32 < len(raw):
            return compressed, 'gzip'
    return raw, 'identity'


def build(ref='HEAD', cache=None):
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', ref, '--', 'web/data'],
                                    cwd=ROOT, text=True).splitlines()
    entries = {}
    unique = {}
    for name in paths:
        path = Path(name)
        if path.suffix not in TYPES:
            raise ValueError('Unsupported public asset: ' + name)
        raw = subprocess.check_output(['git', 'show', f'{ref}:{name}'], cwd=ROOT)
        stored, encoding = encode(raw, path.suffix)
        chunks = []
        for offset in range(0, len(stored), CHUNK_BYTES):
            payload = stored[offset:offset + CHUNK_BYTES]
            digest = sha256(payload).hexdigest()
            chunks.append({'sha256': digest, 'bytes': len(payload)})
            unique[digest] = len(payload)
            if cache is not None:
                target = cache / digest
                if target.exists():
                    if target.read_bytes() != payload:
                        raise ValueError('Conflicting cached chunk')
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(payload)
        entries[name.removeprefix('web/')] = {'sha256': sha256(raw).hexdigest(), 'bytes': len(raw),
            'stored_sha256': sha256(stored).hexdigest(), 'stored_bytes': len(stored),
            'encoding': encoding, 'content_type': TYPES[path.suffix], 'chunks': chunks}
    return {'schema_version': 1, 'chunk_bytes': CHUNK_BYTES, 'direct_bytes': DIRECT_BYTES,
            'asset_count': len(entries), 'source_bytes': sum(e['bytes'] for e in entries.values()),
            'stored_bytes': sum(e['stored_bytes'] for e in entries.values()),
            'unique_chunks': len(unique), 'unique_chunk_bytes': sum(unique.values()), 'assets': entries}


def serialize(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', action='store_true')
    group.add_argument('--check', action='store_true')
    group.add_argument('--batch', type=int, help='Emit a single public chunk document as JSON, never a URI')
    group.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    if args.write or args.check:
        value = build(cache=CACHE if args.write else None)
        encoded = serialize(value)
        if args.write:
            MANIFEST.write_bytes(encoded)
        elif not MANIFEST.exists() or MANIFEST.read_bytes() != encoded:
            raise SystemExit('Public data manifest missing or stale')
        print(json.dumps({k: v for k, v in value.items() if k != 'assets'}))
        return
    value = json.loads(MANIFEST.read_bytes())
    if args.summary:
        print(json.dumps({k: v for k, v in value.items() if k != 'assets'}))
        return
    digests = sorted({p['sha256'] for e in value['assets'].values() for p in e['chunks']})
    digest = digests[args.batch]
    payload = (CACHE / digest).read_bytes()
    if sha256(payload).hexdigest() != digest:
        raise SystemExit('Cached chunk integrity failure')
    print(json.dumps({'_id': digest, 'size_bytes': len(payload),
                      'payload_b64': base64.b64encode(payload).decode('ascii')}, separators=(',', ':')))


if __name__ == '__main__':
    main()

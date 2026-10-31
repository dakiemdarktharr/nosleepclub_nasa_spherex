"""Import public chunks without downloading or exposing Mongo credentials.

Prepare creates a local one-time bearer capability and a hash-only Atlas permit.
The operator inserts that permit via the Atlas connector, uploads the pinned
public chunks, then removes the permit and destroys the local capability.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
import secrets
import time
from uuid import uuid4

from scripts.build_data_manifest import CACHE, MANIFEST

BASE = 'https://nosleepclub-nasa-spherex.vercel.app'
TOKEN_PATH = CACHE / 'import-capability.token'
PERMIT_PATH = CACHE / 'import-permit.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()
    if args.prepare == args.upload:
        parser.error('Choose --prepare or --upload')
    if args.prepare:
        token = secrets.token_urlsafe(32)
        if TOKEN_PATH.exists() or PERMIT_PATH.exists():
            raise SystemExit('Existing migration capability; inspect/revoke before preparing another')
        CACHE.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(token, encoding='ascii')
        issued = datetime.now(timezone.utc)
        permit = {'_id': sha256(MANIFEST.read_bytes()).hexdigest(), 'issued_at': issued.isoformat(),
                  'token_sha256': sha256(token.encode('ascii')).hexdigest(),
                  'expires_at': (issued + timedelta(minutes=45)).isoformat()}
        PERMIT_PATH.write_text(json.dumps(permit) + '\n', encoding='ascii')
        print('Prepared local capability and hash-only permit. No Mongo URI read or exported.')
        return
    import requests
    import truststore
    truststore.inject_into_ssl()
    token = TOKEN_PATH.read_text(encoding='ascii')
    value = json.loads(MANIFEST.read_bytes())
    chunks = {c['sha256']: c['bytes'] for entry in value['assets'].values() for c in entry['chunks']}
    report = {'schema_version': 1, 'base_url': BASE, 'manifest_sha256': sha256(MANIFEST.read_bytes()).hexdigest(),
              'started_at': datetime.now(timezone.utc).isoformat(), 'requests': [], 'completed': False}
    receipt = CACHE / ('import-receipt-' + uuid4().hex + '.json')
    session = requests.Session()
    try:
        for i, (digest, size) in enumerate(sorted(chunks.items())):
            payload = (CACHE / digest).read_bytes()
            if len(payload) != size or sha256(payload).hexdigest() != digest:
                raise RuntimeError('Local public chunk integrity failure')
            for attempt in range(2):
                started = time.monotonic()
                response = session.post(BASE + '/api/data_import', data=payload, allow_redirects=False, timeout=(10, 35),
                    headers={'Authorization': 'Bearer ' + token, 'X-Data-Chunk-SHA256': digest,
                             'Content-Type': 'application/octet-stream'})
                report['requests'].append({'index': i, 'sha256': digest, 'bytes': size, 'attempt': attempt + 1,
                    'status': response.status_code, 'elapsed_seconds': round(time.monotonic() - started, 3),
                    'request_id': response.headers.get('X-Vercel-Id')})
                if response.status_code == 200:
                    if response.json() != {'uploaded': True, 'bytes': size, 'sha256': digest}:
                        raise RuntimeError('Import acknowledgement does not match pinned chunk')
                    break
                if response.status_code not in (502, 503, 504) or attempt == 1:
                    raise RuntimeError('Import rejected: HTTP ' + str(response.status_code))
            if (i + 1) % 25 == 0:
                print(f'Imported {i + 1}/{len(chunks)} pinned chunks', flush=True)
        report['completed'] = True
        report['chunk_count'] = len(chunks)
        report['stored_bytes'] = sum(chunks.values())
    finally:
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        with receipt.open('x', encoding='ascii') as stream:
            stream.write(json.dumps(report, indent=2) + '\n')
        print('Receipt: ' + str(receipt), flush=True)
    print('Import completed. Revoke Atlas permit before release acceptance.', flush=True)


if __name__ == '__main__':
    main()

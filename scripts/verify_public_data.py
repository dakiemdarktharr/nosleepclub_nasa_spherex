"""Reconcile every published product with its exact Git bytes through Mongo HTTP.

Reader-only before cutover; canonical routes after cutover. No private records,
cookies or credentials. Every failure/retry remains in an immutable receipt.
"""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import time
from urllib.parse import urlencode

import requests
import truststore

from scripts.build_data_manifest import MANIFEST, ROOT
from scripts.migrate_public_data import BASE


def verify(output, canonical=False):
    truststore.inject_into_ssl()
    if Path(output).exists():
        raise ValueError('Refusing to overwrite reconciliation receipt')
    current = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    value = json.loads(MANIFEST.read_bytes())
    report = {'schema_version': 1, 'started_at': datetime.now(timezone.utc).isoformat(),
              'local_commit': current, 'manifest_sha256': sha256(MANIFEST.read_bytes()).hexdigest(),
              'canonical_routes': canonical, 'requests': [], 'assets': [], 'passed': False,
              'qualification': 'Exact public-byte transport reconciliation; no science/load/uptime claim.'}
    session = requests.Session()

    def get(path):
        for attempt in range(2):
            start = time.monotonic()
            response = session.get(BASE + path, timeout=(10, 35), allow_redirects=False, stream=True)
            payload = response.raw.read(decode_content=False)
            response.close()
            report['requests'].append({'path': path, 'status': response.status_code, 'attempt': attempt + 1,
                'bytes': len(payload), 'elapsed_seconds': round(time.monotonic() - start, 3),
                'cache': response.headers.get('X-Vercel-Cache'), 'request_id': response.headers.get('X-Vercel-Id')})
            if response.status_code not in (502, 503, 504) or attempt == 1:
                return response, payload
        raise AssertionError('Unreachable')

    try:
        for i, (path, entry) in enumerate(sorted(value['assets'].items())):
            blob = subprocess.check_output(['git', 'show', 'HEAD:web/' + path], cwd=ROOT)
            if len(blob) != entry['bytes'] or sha256(blob).hexdigest() != entry['sha256']:
                raise RuntimeError('Manifest differs from committed original: ' + path)
            base = '/api/data?' + urlencode({'path': path, 'v': entry['stored_sha256']})
            if canonical:
                redirect, _ = get('/' + path)
                if redirect.status_code != 307 or redirect.headers.get('Location') != base:
                    raise RuntimeError('Canonical route did not resolve to pinned Mongo version: ' + path)
            if entry['stored_bytes'] <= value['direct_bytes']:
                response, stored = get(base)
                if response.status_code != 200 or response.headers.get('X-Data-Source') != 'mongodb':
                    raise RuntimeError('Mongo reader failed for ' + path)
                raw = gzip.decompress(stored) if entry['encoding'] == 'gzip' else stored
            else:
                parts = []
                for index, chunk in enumerate(entry['chunks']):
                    response, part = get(base + '&chunk=' + str(index))
                    if response.status_code != 200 or len(part) != chunk['bytes'] or sha256(part).hexdigest() != chunk['sha256']:
                        raise RuntimeError('Mongo chunk mismatch: ' + path + '/' + str(index))
                    if response.headers.get('X-Data-Source') != 'mongodb':
                        raise RuntimeError('Mongo provenance header absent')
                    parts.append(part)
                stored = b''.join(parts)
                raw = gzip.decompress(stored) if entry['encoding'] == 'gzip' else stored
            if len(stored) != entry['stored_bytes'] or sha256(stored).hexdigest() != entry['stored_sha256'] or raw != blob:
                raise RuntimeError('Exact byte reconciliation failed: ' + path)
            report['assets'].append({'path': path, 'bytes': len(raw), 'sha256': entry['sha256'],
                                     'stored_bytes': len(stored), 'stored_sha256': entry['stored_sha256']})
            if (i + 1) % 25 == 0:
                print(f'Reconciled {i + 1}/{len(value["assets"])} public assets', flush=True)
        report['passed'] = True
        report['source_bytes'] = sum(a['bytes'] for a in report['assets'])
        report['stored_bytes'] = sum(a['stored_bytes'] for a in report['assets'])
    finally:
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        with Path(output).open('x', encoding='ascii') as stream:
            stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'assets': len(report['assets']), 'requests': len(report['requests'])}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--canonical', action='store_true')
    args = parser.parse_args()
    verify(args.output, args.canonical)


if __name__ == '__main__':
    main()

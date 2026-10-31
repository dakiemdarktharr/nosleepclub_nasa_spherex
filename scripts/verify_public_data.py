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
from urllib3.exceptions import HTTPError as TransportError

from scripts.build_data_manifest import MANIFEST, ROOT
from scripts.migrate_public_data import BASE


def get(session, path, records):
    for attempt in range(2):
        start = time.monotonic()
        response = None
        try:
            response = session.get(BASE + path, timeout=(10, 35), allow_redirects=False, stream=True)
            payload = response.raw.read(4 * 1024 * 1024 + 1, decode_content=False)
            records.append({'path': path, 'status': response.status_code, 'attempt': attempt + 1,
                'bytes': len(payload), 'elapsed_seconds': round(time.monotonic() - start, 3),
                'cache': response.headers.get('X-Vercel-Cache'), 'request_id': response.headers.get('X-Vercel-Id')})
            if len(payload) > 4 * 1024 * 1024:
                raise RuntimeError('Public response exceeded bounded transport size')
            if response.status_code not in (502, 503, 504) or attempt == 1:
                return response, payload
        except (requests.RequestException, TransportError) as error:
            records.append({'path': path, 'status': response.status_code if response is not None else None,
                'attempt': attempt + 1, 'transport_error': type(error).__name__,
                'elapsed_seconds': round(time.monotonic() - start, 3)})
            if attempt == 1:
                raise RuntimeError('Public transport failed; see retained receipt') from None
        finally:
            if response is not None:
                response.close()
    raise AssertionError('Unreachable')


def check_headers(response, entry, chunk=False):
    expected_type = 'application/octet-stream' if chunk else entry['content_type'].split(';')[0]
    expected_encoding = None if chunk or entry['encoding'] == 'identity' else entry['encoding']
    if response.headers.get('Content-Type', '').split(';')[0] != expected_type or response.headers.get('Content-Encoding') != expected_encoding:
        raise RuntimeError('Public content type/encoding differs from browser contract')


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

    def request(path):
        return get(session, path, report['requests'])

    try:
        for i, (path, entry) in enumerate(sorted(value['assets'].items())):
            blob = subprocess.check_output(['git', 'show', 'HEAD:web/' + path], cwd=ROOT)
            if len(blob) != entry['bytes'] or sha256(blob).hexdigest() != entry['sha256']:
                raise RuntimeError('Manifest differs from committed original: ' + path)
            base = '/api/data?' + urlencode({'path': path, 'v': entry['stored_sha256']})
            if canonical:
                redirect, _ = request('/' + path)
                if redirect.status_code != 307 or redirect.headers.get('Location') != base:
                    raise RuntimeError('Canonical route did not resolve to pinned Mongo version: ' + path)
            if entry['stored_bytes'] <= value['direct_bytes']:
                response, stored = request(base)
                if response.status_code != 200 or response.headers.get('X-Data-Source') != 'mongodb':
                    raise RuntimeError('Mongo reader failed for ' + path)
                check_headers(response, entry)
            else:
                parts = []
                for index, chunk in enumerate(entry['chunks']):
                    response, part = request(base + '&chunk=' + str(index))
                    if response.status_code != 200 or len(part) != chunk['bytes'] or sha256(part).hexdigest() != chunk['sha256']:
                        raise RuntimeError('Mongo chunk mismatch: ' + path + '/' + str(index))
                    if response.headers.get('X-Data-Source') != 'mongodb':
                        raise RuntimeError('Mongo provenance header absent')
                    check_headers(response, entry, chunk=True)
                    parts.append(part)
                stored = b''.join(parts)
            if len(stored) != entry['stored_bytes'] or sha256(stored).hexdigest() != entry['stored_sha256']:
                raise RuntimeError('Stored byte reconciliation failed: ' + path)
            raw = gzip.decompress(stored) if entry['encoding'] == 'gzip' else stored
            if raw != blob:
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

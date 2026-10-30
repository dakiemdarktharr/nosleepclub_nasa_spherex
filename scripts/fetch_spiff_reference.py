"""Fetch a small, versioned SPIFF reference bundle; never run downloaded code.

These tables/templates are development references, not astrometric truth or a
sealed validation set. Large individual-source spectra/images are not fetched.
"""
from datetime import datetime, timezone
from hashlib import md5, sha256
import io
import json
from pathlib import Path
import time
import zipfile

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/external/spiff'
RECEIPT = ROOT / 'web/data/external/spiff-reference.json'
RECORD = 'https://zenodo.org/api/records/19051216'
VERSION = 'QR2-2026-04-24'
FILES = {
    '00_README.txt': (2338, 'b5ca7d52456b54ccc93755bdbbdf4754'),
    'spiff_zenodo_manifest.csv': (4237, '2b7ac7eff4c11953c29bfbec14495acb'),
    'spiff_tables.zip': (784867, 'd5ed51c8075a355876cacccd18c4e21f'),
    'spiff_templates_hybrid_csv.zip': (81282, '5e00408a1f284059f993e9da112954fe'),
}


def bounded_get(url, maximum):
    started = time.monotonic()
    with requests.get(url, stream=True, timeout=(10, 20), allow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError('Unexpected response or redirect')
        length = response.headers.get('Content-Length')
        if length and int(length) > maximum:
            raise ValueError('Response exceeds size bound')
        chunks = []
        count = 0
        for chunk in response.iter_content(65536):
            count += len(chunk)
            if count > maximum or time.monotonic() - started > 60:
                raise ValueError('Response exceeds size/time bound')
            chunks.append(chunk)
        return b''.join(chunks)


def checked_file(name, content):
    size, checksum = FILES[name]
    if len(content) != size or md5(content, usedforsecurity=False).hexdigest() != checksum:
        raise ValueError('Published size/checksum mismatch: ' + name)
    return {'name': name, 'bytes': len(content), 'provider_md5': checksum,
            'sha256': sha256(content).hexdigest()}


def cache(path, content):
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError('Refusing to overwrite different cache: ' + path.name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as target:
            target.write(content)


def main():
    # Verify publisher metadata as well as the pinned file checksums.
    metadata_bytes = bounded_get(RECORD, 2_000_000)
    metadata = json.loads(metadata_bytes)
    if (metadata['id'] != 19051216 or metadata['metadata']['version'] != VERSION
            or metadata['metadata']['license']['id'] != 'cc-by-4.0'):
        raise ValueError('Unexpected dataset version/license')
    published = {row['key']: row for row in metadata['files']}
    results = []
    for name, (size, checksum) in FILES.items():
        url = RECORD + '/files/' + name + '/content'
        row = published[name]
        if (row['size'] != size or row['checksum'] != 'md5:' + checksum
                or row['links']['self'] != url):
            raise ValueError('Publisher metadata changed: ' + name)
        path = RAW / name
        content = path.read_bytes() if path.exists() else bounded_get(url, size)
        record = checked_file(name, content)
        record.update(url=url, path=path.relative_to(ROOT).as_posix())
        if name.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                # Inventory only: no extraction, CSV evaluation or executable import.
                members = archive.infolist()
                if len(members) > 200 or sum(v.file_size for v in members) > 20_000_000:
                    raise ValueError('Unexpected archive expansion')
                record['archive_members'] = [{'name': v.filename, 'bytes': v.file_size}
                                             for v in members]
        cache(path, content)
        results.append(record)
        print(name, record['bytes'], record['sha256'], flush=True)
    cache(RAW / 'record-metadata.json', metadata_bytes)
    receipt = {
        'dataset': 'SPHEREx Photometry and Image Fitting Framework (SPIFF) library',
        'authors': 'Jonathan Gagne et al.', 'doi': '10.5281/zenodo.19051216',
        'version': VERSION, 'source': 'https://zenodo.org/records/19051216',
        'paper': 'https://arxiv.org/abs/2604.22012',
        'license': {'id': 'CC-BY-4.0', 'url': 'https://creativecommons.org/licenses/by/4.0/'},
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'metadata_sha256': sha256(metadata_bytes).hexdigest(),
        'builder_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'files': results,
        'purpose': 'development SED references and catalog inventory; not astrometric truth',
        'limits': [
            'No new SPHEREx images or individual-source spectra downloaded by this script',
            'No accuracy, completeness or independent validation result from this inventory',
            'SPHEREx-derived templates share instrument/pixel provenance; prevent overlap with validation sources/exposures',
            'L0-Y1 templates do not bracket the much colder WISE 0855 spectrum',
        ],
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    # A repeated run keeps the original retrieval receipt when content is unchanged.
    if RECEIPT.exists():
        old = json.loads(RECEIPT.read_text(encoding='utf-8'))
        if old['files'] != results or old['metadata_sha256'] != receipt['metadata_sha256']:
            raise ValueError('Reference inventory changed; retain old receipt and review a new version')
        print('Existing receipt unchanged')
    else:
        cache(RECEIPT, (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


if __name__ == '__main__':
    main()

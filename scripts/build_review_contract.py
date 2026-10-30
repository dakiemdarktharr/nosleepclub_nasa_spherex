"""Generate or verify the minimal server-side review manifest from the public manifest."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def render_contract(source_bytes):
    source = json.loads(source_bytes.decode('utf-8'))
    contract = {
        'schema_version': '1.0',
        'source_manifest_sha256': sha256(source_bytes).hexdigest(),
        'analysis_sha256': source['analysis_sha256'],
        'scenes': [
            {'id': scene['id'],
             'candidates': [{'id': candidate['id']} for candidate in scene['candidates']],
             'before': {'sha256': scene['before']['sha256']},
             'after': {'sha256': scene['after']['sha256']},
             'target_detection': scene['target_detection']}
            for scene in source['scenes']
        ],
    }
    return (json.dumps(contract, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true', help='Write the derived contract')
    mode.add_argument('--check', action='store_true', help='Fail if the derived contract is missing or stale')
    args = parser.parse_args(argv)
    target = ROOT / 'web/api/_review_manifest.json'
    expected = render_contract((ROOT / 'web/data/manifest.json').read_bytes())
    if args.write:
        target.write_bytes(expected)
        print(f'Wrote {target} ({len(expected)} bytes)')
        return 0
    if not target.is_file() or target.read_bytes() != expected:
        print('Review contract missing or stale; run python scripts/build_review_contract.py --write', file=sys.stderr)
        return 1
    print('Review contract matches canonical manifest')
    return 0


if __name__ == '__main__':
    sys.exit(main())

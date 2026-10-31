"""Public profile archive retains both complete immutable journals and source seals."""
from collections import Counter
import gzip
from hashlib import sha256
import json
from pathlib import Path
import unittest

from scripts.science_jobs import encode
from scripts.run_wise_linked_study import encoded


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT/'web/data/profile-landscape'


def checksum(value): return sha256(encode({k:v for k,v in value.items() if k != 'checksum'})).hexdigest()


class ProfileProductsTests(unittest.TestCase):
    def test_public_artifacts_and_sources_have_exact_hashes(self):
        report = json.loads((PUBLIC/'overview.json').read_text(encoding='utf-8'))
        design_bytes = (PUBLIC/'design.json').read_bytes(); design = json.loads(design_bytes)
        self.assertEqual(sha256(design_bytes).hexdigest(), report['design_sha256'])
        for mapping in (design['sources'], design['opened_products'], report['audit_source_sha256'], report['publisher_source_sha256']):
            for name, expected in mapping.items():
                self.assertEqual(sha256((ROOT/name).read_bytes()).hexdigest(), expected, name)
        for name, meta in report['figures'].items():
            self.assertEqual(sha256((PUBLIC/name).read_bytes()).hexdigest(), meta['sha256'], name)
            self.assertEqual(len(meta['record_checksums']), 4)
        environment = json.loads((PUBLIC/'figure-environment.json').read_text(encoding='utf-8'))
        self.assertEqual(sha256((ROOT/environment['requirements_path']).read_bytes()).hexdigest(), environment['requirements_sha256'])
        self.assertEqual(environment['publisher_sha256'], report['publisher_source_sha256']['scripts/publish_profile_landscape.py'])
        self.assertEqual(set(environment['figures']), set(report['figures']))
        for name, meta in environment['figures'].items():
            self.assertEqual(meta['sha256'], report['figures'][name]['sha256'])

    def test_all_112_profile_and_audit_records_are_bound_in_archive(self):
        report = json.loads((PUBLIC/'overview.json').read_text(encoding='utf-8'))
        compressed = (PUBLIC/'records.json.gz').read_bytes(); raw = gzip.decompress(compressed)
        self.assertEqual(len(compressed), report['download']['bytes'])
        self.assertEqual(sha256(compressed).hexdigest(), report['download']['sha256'])
        self.assertEqual(len(raw), report['download']['uncompressed_bytes'])
        self.assertEqual(sha256(raw).hexdigest(), report['download']['uncompressed_sha256'])
        archive = json.loads(raw); json.dumps(archive, allow_nan=False)
        for header_name, records_name in (('journal_header', 'records'), ('audit_journal_header', 'audit_records')):
            header = archive[header_name]; records = archive[records_name]
            self.assertEqual(checksum(header), header['checksum'])
            self.assertEqual(len(records), 112)
            self.assertEqual([r['key'] for r in records], header['expected_keys'])
            for record in records:
                self.assertEqual(checksum(record), record['checksum'])
                self.assertEqual(record['identity_sha256'], header['identity_sha256'])
        records = archive['records']; audit_records = archive['audit_records']
        profile = {tuple(r['key']):r for r in records}
        for audited in audit_records:
            self.assertEqual(audited['payload']['profile_checksum'], profile[tuple(audited['key'])]['checksum'])
        self.assertEqual(dict(Counter(r['payload']['status'] for r in records)), {'profile_completed': 96, 'preparation_failed': 16})
        self.assertEqual(dict(Counter(r['payload']['status'] for r in audit_records)), {'verified': 96, 'verified_unavailable': 16})
        self.assertEqual(len({r['key'][0] for r in records}), 14)
        self.assertTrue(all(n == 8 for n in Counter(r['key'][0] for r in records).values()))
        for header_name, records_name, expected in (('journal_header', 'records', report['cell_digest']),
                ('audit_journal_header', 'audit_records', json.loads((PUBLIC/'independent-audit.json').read_text(encoding='utf-8'))['audit_cell_digest'])):
            body = {'header_sha256': sha256(encode(archive[header_name])).hexdigest(),
                'records': [{'key': r['key'], 'checksum': r['checksum']} for r in archive[records_name]]}
            self.assertEqual(sha256(encoded(body)).hexdigest(), expected)

    def test_no_science_promotion_or_opening_of_deferred_cells(self):
        report = json.loads((PUBLIC/'overview.json').read_text(encoding='utf-8'))
        receipt = json.loads((PUBLIC/'independent-audit.json').read_text(encoding='utf-8'))
        body = {k:v for k,v in receipt.items() if k != 'receipt_sha256'}
        self.assertEqual(sha256(encoded(body)).hexdigest(), receipt['receipt_sha256'])
        self.assertEqual(receipt['status'], 'passed'); self.assertEqual(receipt['failures'], [])
        self.assertIs(report['promotion'], False); self.assertIs(report['original_calibration_gate_passed'], False)
        self.assertIs(report['assessment_opened'], False); self.assertEqual(report['prospective_fields_opened'], 0)
        self.assertEqual(len(report['focus']), 4)
        self.assertEqual({f['obs_id'] for f in report['focus']}, {'2025W46_2A_0214_2', '2025W46_2A_0214_3'})
        self.assertTrue(all(len(f['arms']) == 4 for f in report['focus']))


if __name__ == '__main__': unittest.main()

"""Check versioned science products without needing ignored raw FITS caches."""
import gzip
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


class ReferencePresenceProductTests(unittest.TestCase):
    def test_frozen_sources_and_opened_products_unchanged(self):
        for folder in ('reference-stars', 'source-presence'):
            design = load('web/data/' + folder + '/design.json')
            for key in ('sources', 'opened_products'):
                for path, expected in design[key].items():
                    with self.subTest(folder=folder, path=path):
                        self.assertEqual(sha256((ROOT / path).read_bytes()).hexdigest(), expected)

    def test_archive_hashes_stream_without_loading_hundreds_of_megabytes(self):
        for folder in ('reference-stars', 'source-presence'):
            overview = load('web/data/' + folder + '/overview.json');download = overview['download']
            path = ROOT / 'web' / download['path']
            self.assertEqual(path.stat().st_size, download['bytes'])
            compressed = sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024*1024), b''):
                    compressed.update(chunk)
            self.assertEqual(compressed.hexdigest(), download['sha256'])
            unpacked = sha256();count = 0
            with gzip.open(path, 'rb') as stream:
                for chunk in iter(lambda: stream.read(1024*1024), b''):
                    count += len(chunk);unpacked.update(chunk)
            self.assertEqual((count, unpacked.hexdigest()), (download['uncompressed_bytes'], download['uncompressed_sha256']))

    def test_reference_failures_and_all_vs_numerical_denominators_retained(self):
        report = load('web/data/reference-stars/overview.json')
        self.assertEqual(report['counts']['statuses'], {'fit_completed': 718, 'fit_failed': 0, 'preparation_failed': 122})
        self.assertEqual(sum(report['failure_reasons'].values()), 122)
        self.assertEqual(len(report['sources']), 21)
        self.assertEqual(len(report['frames']), 20)
        self.assertEqual(sum(s['common_completed'] == 0 for s in report['sources']), 2)
        self.assertEqual(report['summary']['common_completed'], 359)
        self.assertEqual(report['summary']['common_numerical'], 357)
        for variant in ('nearest', 'bilinear'):
            arm = next(a for a in report['summary']['arms'] if a['variant'] == variant)
            self.assertEqual(arm['planned'], 420)
            self.assertEqual(arm['common_completed']['n'], 359)
            self.assertEqual(arm['common_numerical']['n'], 357)
            self.assertEqual(sum(next(a for a in r['arms'] if a['variant'] == variant)['completed'] for r in report['sources']), 359)
        self.assertFalse(report['promotion'])

    def test_seal_and_conditional_validation_full_denominators(self):
        report = load('web/data/source-presence/overview.json');seal = load('web/data/source-presence/threshold.json')
        design_path = ROOT / 'web/data/source-presence/design.json'
        self.assertEqual(sha256(design_path.read_bytes()).hexdigest(), seal['design_sha256'])
        self.assertEqual(report['threshold']['value'], seal['threshold'])
        self.assertEqual(report['threshold']['calibration_digest'], seal['calibration_digest'])
        self.assertFalse(seal['validation_generated'])
        self.assertEqual(report['calibration']['completed'], 1998)
        self.assertEqual(report['validation']['completed'], 5994)
        self.assertEqual(report['audit_counts']['saved_realizations_replayed'], 7992)
        self.assertTrue(report['conditional_gates_passed'])
        expected = {'plane_null': 0, 'quadratic_null': 0, 'plane_300uJy': 46,
                    'plane_600uJy': 928, 'quadratic_300uJy': 55, 'quadratic_600uJy': 870}
        self.assertEqual({r['scenario']: r['accepted'] for r in report['cases']}, expected)
        for row in report['cases']:
            self.assertEqual((row['planned'], row['completed'], row['failed']), (999, 999, 0))
        self.assertFalse(report['promotion'])

    def test_publications_bind_current_audit_sources(self):
        for folder, module in [('reference-stars', 'publish_reference_stars'), ('source-presence', 'publish_presence_study')]:
            overview = load('web/data/' + folder + '/overview.json')
            self.assertEqual(overview['audit_source_sha256'], sha256((ROOT / 'scripts' / (module + '.py')).read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()

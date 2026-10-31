"""Public products bind complete audits without opening raw FITS or MongoDB."""
import gzip
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT/'web'


def read(relative):
    return json.loads((WEB/relative).read_text(encoding='utf-8'))


class ShapeReferenceProductsTests(unittest.TestCase):
    def test_complete_calibration_and_deferred_point_denominators(self):
        learn = read('data/shape-correction/overview.json')
        point = read('data/shape-point-check/overview.json')
        self.assertEqual((learn['planned'], sum(learn['counts'].values())), (168, 168))
        self.assertEqual(sum(s['information_available'] for s in learn['sources']), learn['counts']['information_available'])
        self.assertEqual(len(learn['sources']), 14)
        self.assertEqual((point['planned'], point['recorded'], point['deferred']), (420, 168, 252))
        self.assertEqual(sum(point['counts'].values()), 168)
        self.assertEqual(sum(s['counts'].get('not_evaluated', 0) for s in point['source_rows']), 252)
        self.assertEqual(len(point['source_rows']), 21)
        self.assertIsNone(point['assessment_digest'])
        self.assertEqual(point['primary']['point_status_counts']['missing'], 56)
        self.assertEqual(len(point['primary']['source_rows']), 7)
        self.assertFalse(point['primary']['developmental_gates_passed'])
        self.assertFalse(point['promotion'])

    def test_refused_gate_mode_cases_and_coefficient_binding(self):
        point = read('data/shape-point-check/overview.json');gate = read('data/shape-point-check/calibration-gate.json')
        seal = read('data/shape-correction/coefficient-seal.json');learn = read('data/shape-correction/overview.json')
        self.assertFalse(gate['assessment_allowed'])
        self.assertEqual(len(gate['comparisons'])+len(gate['failures']), learn['audit']['saved_cells'])
        self.assertEqual(point['calibration_gate']['failure_count'], 2)
        self.assertEqual(point['calibration_gate']['comparison_count'], 143)
        self.assertEqual(gate['shape_calibration_cell_digest'], seal['cell_digest'])
        self.assertEqual(point['coefficient_seal_sha256'], sha256((WEB/'data/shape-correction/coefficient-seal.json').read_bytes()).hexdigest())
        self.assertEqual(point['calibration_gate_sha256'], sha256((WEB/'data/shape-point-check/calibration-gate.json').read_bytes()).hexdigest())
        self.assertTrue(all(c['baseline_near_best_count'] == 1 and c['corrected_near_best_count'] == 2 for c in point['calibration_gate']['failure_cases']))
        self.assertTrue(all(c['corrected_mode_maximum_separation_arcsec'] > 1 for c in point['calibration_gate']['failure_cases']))

    def test_covariance_sources_failures_and_all_native_audit(self):
        report = read('data/reference-covariance/overview.json')
        self.assertEqual(report['counts'], {'influence_available': 357, 'baseline_unavailable': 61, 'baseline_numerical_refusal': 2})
        self.assertEqual(report['planned'], 420)
        self.assertEqual(len(report['source_counts']), 21)
        self.assertEqual(sum(sum(s['statuses'].values()) for s in report['source_counts'].values()), 420)
        self.assertEqual(len(report['heldout_sources']), 7)
        self.assertEqual(sum(s['dof'] for s in report['heldout_sources']), report['heldout_joint']['dof'])
        self.assertTrue(any(s['available'] == 0 and s['chi2'] is None for s in report['heldout_sources']))
        self.assertEqual(report['independent_audit']['native_audited'], 357)
        self.assertEqual(report['unique_original_pixels'], 49294)
        self.assertFalse(report['learned_shape_used']);self.assertFalse(report['promotion'])

    def test_source_design_publisher_and_independent_audit_hashes(self):
        for directory in ('shape-correction', 'shape-point-check', 'reference-covariance'):
            with self.subTest(directory=directory):
                overview = read(f'data/{directory}/overview.json')
                self.assertEqual(overview['design_sha256'], sha256((WEB/f'data/{directory}/design.json').read_bytes()).hexdigest())
                design = read(f'data/{directory}/design.json')
                for path, digest in design['sources'].items():
                    self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(), digest, path)
                self.assertFalse(overview['promotion'])
        for directory, publisher in (('shape-correction', 'publish_shape_calibration.py'), ('shape-point-check', 'publish_shape_points.py'), ('reference-covariance', 'publish_reference_covariance.py')):
            overview = read(f'data/{directory}/overview.json')
            expected = overview.get('publisher_sha256', overview.get('audit_source_sha256'))
            self.assertEqual(expected, sha256((ROOT/'scripts'/publisher).read_bytes()).hexdigest())
        for directory in ('shape-point-check', 'reference-covariance'):
            audit = read(f'data/{directory}/independent-audit.json')
            for path, digest in audit['audit_source_sha256'].items():
                self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(), digest, path)

    def test_full_download_compressed_and_streamed_uncompressed_hashes(self):
        for directory in ('shape-correction', 'shape-point-check', 'reference-covariance'):
            with self.subTest(directory=directory):
                download = read(f'data/{directory}/overview.json')['download'];path = WEB/download['path']
                self.assertTrue(path.resolve().is_relative_to(WEB.resolve()))
                compressed = sha256();size = 0
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024*1024), b''):
                        compressed.update(chunk);size += len(chunk)
                self.assertEqual(size, download['bytes']);self.assertEqual(compressed.hexdigest(), download['sha256'])
                uncompressed = sha256();size = 0
                with gzip.open(path, 'rb') as stream:
                    for chunk in iter(lambda: stream.read(1024*1024), b''):
                        uncompressed.update(chunk);size += len(chunk)
                self.assertEqual(size, download['uncompressed_bytes'])
                self.assertEqual(uncompressed.hexdigest(), download['uncompressed_sha256'])


if __name__ == '__main__':
    unittest.main()

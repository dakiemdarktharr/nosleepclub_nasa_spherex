"""Audit numeric provenance of diagnostics and real challenge-target previews."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import unittest
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class DiagnosticProducts(unittest.TestCase):
    def test_opened_field_diagnostics_keep_counts_and_recompute_errors(self):
        data=json.loads((ROOT/'web/data/diagnostics/bias-overview.json').read_text(encoding='utf-8'))
        self.assertFalse(data['scientific_promotion']);self.assertFalse(data['changes_point_model']);self.assertFalse(data['changes_calibrator'])
        self.assertEqual(data['source_sha256'],sha256((ROOT/'scripts/diagnose_bias.py').read_bytes()).hexdigest())
        self.assertEqual(data['builder_sha256'],sha256((ROOT/'scripts/build_bias_overview.py').read_bytes()).hexdigest())
        self.assertEqual(len(data['cases']),6)
        for item in data['inputs']:
            path=ROOT/item['path']
            if path.exists():self.assertEqual(sha256(path.read_bytes()).hexdigest(),item['sha256'])
        for case in data['cases']:
            self.assertLess(case['replay_max_vector_difference_arcsec'],1e-5)
            self.assertLess(case['signal_only_control']['error_arcsec'],1e-3)
            p=ROOT/case['source']['path'];self.assertEqual(sha256(p.read_bytes()).hexdigest(),case['source']['sha256'])
            values=[r for r in case['gaussian_controls']['records'] if r['numeric_valid']]
            self.assertEqual(len(case['gaussian_controls']['records']),64)
            errors=[np.linalg.norm(r['error_east_north_arcsec']) for r in values]
            self.assertAlmostEqual(np.sqrt(np.mean(np.square(errors))),case['gaussian_controls']['rms_numeric_arcsec'])
            self.assertEqual(sum(r['mahalanobis2_raw']<=2.27886856637673 for r in values),case['gaussian_controls']['raw68_numeric'])
            for row in values:
                e=np.asarray(row['error_east_north_arcsec']);c=np.asarray(row['covariance_arcsec2'])
                self.assertAlmostEqual(float(e@np.linalg.solve(c,e)),row['mahalanobis2_raw'])
            trials=case['exposure_influence']['trials']
            self.assertEqual(len(trials),20)
            changes=[r['vector_change_arcsec'] for r in trials if r['vector_change_arcsec'] is not None]
            self.assertAlmostEqual(max(changes),case['exposure_influence']['maximum_vector_change_arcsec'])

    def test_five_target_discovery_snapshots_have_real_image_provenance(self):
        path=ROOT/'web/data/explorer-check/coverage.json';data=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(data['source_sha256'],sha256((ROOT/'scripts/check_observation_targets.py').read_bytes()).hexdigest())
        self.assertEqual(data['targets_sha256'],sha256((ROOT/'web/data/challenge-targets.json').read_bytes()).hexdigest())
        self.assertEqual({r['target']['id'] for r in data['targets']},{'wise0855','barnard','epsilon','rwaur','rdra'})
        for row in data['targets']:
            self.assertNotIn('error',row);self.assertFalse(row['truncated']);self.assertGreaterEqual(len(row['observations']),2)
            self.assertEqual(len(row['images']),2)
            for image in row['images']:
                self.assertNotIn('error',image);self.assertGreater(image['display']['valid_pixels'],0)
                p=ROOT/'web'/image['image'];content=p.read_bytes()
                self.assertEqual(sha256(content).hexdigest(),image['png_sha256'])
                im=Image.open(BytesIO(content));self.assertEqual(im.mode,'RGB');self.assertLessEqual(max(im.size),192)
                self.assertTrue(image['cutout_url'].startswith('https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/level2/'))
                raw=ROOT/'data/raw/explorer-check'/(row['target']['id']+'-'+image['side']+'.fits')
                if raw.exists():self.assertEqual(sha256(raw.read_bytes()).hexdigest(),image['raw_sha256'])

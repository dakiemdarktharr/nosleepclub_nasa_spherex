"""Audit the external benchmark's heldout split, inputs and denominators."""
from hashlib import sha256
import json
from pathlib import Path
import unittest

import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'web/data/benchmark'


class ExternalBenchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=json.loads((OUT/'protocol.json').read_text())
        cls.summary=json.loads((OUT/'summary.json').read_text())

    def test_sources_inputs_and_pre_fit_split_are_frozen(self):
        protocol=self.protocol
        self.assertEqual(self.summary['protocol_sha256'],sha256((OUT/'protocol.json').read_bytes()).hexdigest())
        for name,digest in protocol['source_hashes'].items():
            self.assertEqual(sha256((ROOT/'scripts'/name).read_bytes()).hexdigest(),digest)
        self.assertEqual(len(protocol['fields']),3)
        centers=[];used=set()
        for field in protocol['fields']:
            centers.append(SkyCoord(field['field']['ra']*u.deg,field['field']['dec']*u.deg))
            refs=field['references'];ids=[r['catalog']['source_id'] for r in refs]
            self.assertEqual(len(ids),len(set(ids)))
            self.assertEqual(ids,sorted(ids,key=lambda s:sha256(s.encode()).hexdigest()))
            self.assertEqual([r['split'] for r in refs],['heldout' if i%3==0 else 'training' for i in range(len(refs))])
            inputs=field['input_manifest']
            for record in inputs['records']:
                self.assertNotIn(record['obs_id'],used);used.add(record['obs_id'])
                self.assertEqual(record['collection'],'spherex_qr2')
                self.assertEqual(len(record['sha256']),64)
                path=ROOT/record['path']
                if path.exists():self.assertEqual(sha256(path.read_bytes()).hexdigest(),record['sha256'])
        for i,a in enumerate(centers):
            for b in centers[i+1:]:self.assertGreater(a.separation(b).deg,10)

    def test_every_heldout_and_injection_attempt_remains_reported(self):
        for field in self.protocol['fields']:
            payload=json.loads((OUT/(field['field']['id']+'.json')).read_text())
            heldout={r['catalog']['source_id'] for r in field['references'] if r['split']=='heldout'}
            training={r['catalog']['source_id'] for r in payload['training']}
            self.assertFalse(heldout&training)
            for group in payload['configurations']:
                if 'unavailable_reason' in group:
                    self.assertNotIn('real_summary',group)
                    continue
                for reg in group['registrations']:self.assertFalse(set(reg['source_ids'])&heldout)
                self.assertEqual({r['source_id'] for r in group['real_controls']},heldout)
                self.assertEqual(len(group['injections']),16)
                keys={(tuple(r['anchor']),r['snr_per_frame'],tuple(r['truth_delta_px'])) for r in group['injections']}
                self.assertEqual(len(keys),16)
                for name,key in [('real_controls','real_summary'),('injections','injection_summary')]:
                    records=group[name];summary=group[key];valid=[r for r in records if r.get('valid')]
                    self.assertEqual(summary['attempted'],len(records))
                    self.assertEqual(summary['valid'],len(valid))
                    self.assertEqual(summary['failed'],len(records)-len(valid))
                    self.assertEqual(summary['within_68_ellipse'],sum(r['within_68_ellipse'] for r in valid))
                    if valid:
                        rms=np.sqrt(np.mean([np.dot(r['error_east_north_arcsec'],r['error_east_north_arcsec']) for r in valid]))
                        self.assertAlmostEqual(summary['rmse_arcsec'],rms,places=10)

    def test_real_motion_and_injections_keep_truth_separate(self):
        self.assertFalse(self.summary['current_measurement_changed'])
        for field in self.protocol['fields']:
            payload=json.loads((OUT/(field['field']['id']+'.json')).read_text())
            for group in payload['configurations']:
                records=group['real_controls']+group['injections']
                if 'positive_control' in group:records.append(group['positive_control'])
                for r in records:
                    if 'error_east_north_arcsec' not in r:continue
                    actual=np.array(r['measured_east_north_arcsec'])-r['expected_east_north_arcsec']
                    np.testing.assert_allclose(actual,r['error_east_north_arcsec'],atol=1e-10)
                    self.assertAlmostEqual(np.linalg.norm(actual),r['error_arcsec'],places=10)
                    cov=np.array(r['covariance_arcsec2'])
                    self.assertTrue(np.all(np.linalg.eigvalsh(cov)>0))
                    if r['valid']:
                        self.assertFalse(r['before']['at_boundary'] or r['after']['at_boundary'])


if __name__=='__main__':unittest.main()

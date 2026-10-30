"""Provenance and all-attempt audits of the new-field quality study."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'web/data/quality'


class QualityEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=json.loads((OUT/'protocol.json').read_text())
        cls.summary=json.loads((OUT/'evaluation-summary.json').read_text())

    def test_lock_and_new_fields_are_independent_of_development(self):
        self.assertEqual(self.summary['protocol_sha256'],sha256((OUT/'protocol.json').read_bytes()).hexdigest())
        for name,digest in self.protocol['source_hashes'].items():
            self.assertEqual(sha256((ROOT/'scripts'/name).read_bytes()).hexdigest(),digest)
        old=json.loads((ROOT/'web/data/benchmark/protocol.json').read_text())['fields']
        old_centers=[SkyCoord(f['field']['ra']*u.deg,f['field']['dec']*u.deg) for f in old]
        old_ids={r['obs_id'] for f in old for r in f['input_manifest']['records']}
        self.assertEqual(len(self.protocol['fields']),3)
        for f in self.protocol['fields']:
            center=SkyCoord(f['field']['ra']*u.deg,f['field']['dec']*u.deg)
            for point in old_centers:self.assertGreater(center.separation(point).deg,10.)
            for r in f['input_manifest']['records']:self.assertNotIn(r['obs_id'],old_ids)
            ids=[r['catalog']['source_id'] for r in f['references']]
            self.assertEqual(ids,sorted(ids,key=lambda s:sha256(s.encode()).hexdigest()))
            self.assertEqual([r['split'] for r in f['references']],['heldout' if i%3==0 else 'training' for i in range(len(ids))])

    def test_gate_never_removes_attempts_or_uses_truth_for_acceptance(self):
        for field in self.protocol['fields']:
            payload=json.loads((OUT/('evaluation-'+field['field']['id']+'.json')).read_text())
            heldout={r['catalog']['source_id'] for r in field['references'] if r['split']=='heldout'}
            for key in ['baseline_registrations','ir_robust_registrations']:
                for reg in payload.get(key,[]):self.assertFalse(set(reg['source_ids'])&heldout)
            self.assertEqual(payload['planned_injections'],32)
            if payload['injections']:
                self.assertEqual(len(payload['injections']),32)
                keys={(r['patch_index'],r['snr_per_frame'],r['truth_psf'],tuple(r['truth_delta_px'])) for r in payload['injections']}
                self.assertEqual(len(keys),32)
            else:self.assertTrue(payload['unavailable'])
            for record in payload['injections']+payload['real_controls']:
                self.assertEqual(set(record['models']),{'baseline','ir_robust'})
                for kind,r in record['models'].items():
                    if r['accepted']:
                        self.assertTrue(r['numeric_valid']);self.assertEqual(r['quality_reasons'],[])
                        self.assertTrue(r['before']['quality']['accepted'] and r['after']['quality']['accepted'])
                    if 'before' in r and kind=='ir_robust':
                        for epoch in ['before','after']:
                            quality=r[epoch]['quality'];comparison=quality['model_comparison']
                            self.assertEqual('model_disagreement' in quality['reasons'],comparison['shift_px']>comparison['limit_px'])

    def test_paired_numbers_and_ui_overview_have_verifiable_inputs(self):
        from scripts import build_quality_overview
        overview=json.loads((OUT/'overview.json').read_text())
        self.assertEqual(overview['source_sha256'],sha256(Path(build_quality_overview.__file__).read_bytes()).hexdigest())
        for name,digest in overview['input_sha256'].items():self.assertEqual(sha256((OUT/name).read_bytes()).hexdigest(),digest)
        for field in self.protocol['fields']:
            data=json.loads((OUT/('evaluation-'+field['field']['id']+'.json')).read_text())
            for name,selection in [('real_controls','real_summary'),('injections','injection_summary')]:
                if selection not in data:continue
                records=data[name];summary=data[selection]
                for kind in ['baseline','ir_robust']:
                    for gate in ['numeric_valid','accepted']:
                        s=summary['models'][kind][gate];valid=[r['models'][kind] for r in records if r['models'][kind][gate]]
                        self.assertEqual(s['attempted'],len(records));self.assertEqual(s['valid'],len(valid))
                        if valid:self.assertAlmostEqual(s['rmse_arcsec'],np.sqrt(np.mean([r['error_arcsec']**2 for r in valid])),places=9)
                common=[r for r in records if all(r['models'][k]['numeric_valid'] for k in ['baseline','ir_robust'])]
                self.assertEqual(summary['paired_numeric']['common'],len(common))
        self.assertFalse(overview['default_measurement_changed'])


if __name__=='__main__':unittest.main()

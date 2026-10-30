"""Audit split, locked provenance and all published 0.8 attempts/uncertainties."""
import json
from pathlib import Path
import unittest
import numpy as np
from scripts import covariance_study as study
from scripts import covariance_model as model

OUT=study.OUT
def read(name):return json.loads((OUT/(name+'.json')).read_text(encoding='utf-8'))


class CovarianceProducts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design=read('design');cls.seal=read('validation-protocol');cls.cal=read('calibrator');cls.overview=read('overview')
        cls.fields={role:[read(role+'-'+i['field']['id']) for i in items] for role,items in cls.design['fields'].items()}

    def test_source_hashes_and_sealed_inputs_match(self):
        self.assertEqual(self.design['source_hashes'],study.sources())
        self.assertEqual(self.design['rules'],study.RULES)
        self.assertEqual(self.design['model_rules'],model.RULES)
        self.assertEqual(self.seal['design_sha256'],study.bench.digest(OUT/'design.json'))
        self.assertEqual(self.seal['calibrator_sha256'],study.bench.digest(OUT/'calibrator.json'))
        self.assertEqual(self.seal['calibration_summary_sha256'],study.bench.digest(OUT/'calibration-summary.json'))
        for name,h in self.overview['input_sha256'].items():self.assertEqual(study.bench.digest(OUT/name),h)
        self.assertEqual(self.overview['source_sha256'],study.bench.digest(Path(study.ROOT/'scripts/build_covariance_overview.py')))

    def test_fields_exposures_and_gaia_splits_do_not_leak(self):
        exposures=self.design['selected_exposure_ids'];roles=list(exposures)
        for i,a in enumerate(roles):
            for b in roles[i+1:]:self.assertFalse(set(exposures[a])&set(exposures[b]))
        for items in self.design['fields'].values():
            for item in items:
                train={r['catalog']['source_id'] for r in item['references'] if r['split']=='training'}
                held={r['catalog']['source_id'] for r in item['references'] if r['split']=='heldout'}
                self.assertFalse(train&held)
        self.assertNotEqual(study.RULES['calibration_truth_psfs'],study.RULES['validation_truth_psfs'])

    def test_calibrator_is_reproducible_from_calibration_only(self):
        rows=[r for v in self.fields['calibration'] for r in v['injections']]
        actual=model.calibrate(rows)
        for k,v in actual.items():self.assertEqual(self.cal[k],v)
        for ident,h in self.cal['source_results'].items():self.assertEqual(study.bench.digest(OUT/('calibration-'+ident+'.json')),h)

    def test_all_planned_attempts_retained_and_summaries_recompute(self):
        for role,fields in self.fields.items():
            for field in fields:
                expected=0 if role=='development' else len(study.RULES[role+'_positions_px'])*8
                self.assertEqual(len(field['injections']),expected)
                self.assertEqual(field['injection_summary'],study.summarize(field['injections']))
                self.assertEqual(field['real_summary'],study.summarize(field['real_controls']))
                if role=='validation':self.assertEqual(field['point_gate'],study.point_gate(field))
        rows=[r for v in self.fields['validation'] for r in v['injections']]
        self.assertEqual(self.overview['coverage_gate'],study.coverage_gate(rows))

    def test_calibration_does_not_change_centroid_or_gate_and_is_psd(self):
        for field in self.fields['validation']:
            for r in field['injections']+field['real_controls']:
                v=r['models']['candidate']
                if 'covariance_arcsec2' not in v:continue
                raw=np.asarray(v['covariance_arcsec2']);cal=np.asarray(v['calibrated_covariance_arcsec2'])
                np.testing.assert_allclose(cal,model.apply_covariance(raw,self.cal),atol=1e-12)
                self.assertGreaterEqual(np.linalg.eigvalsh(cal-raw).min(),-1e-10)
                error=np.array(v['measured_east_north_arcsec'])-v['expected_east_north_arcsec']
                np.testing.assert_allclose(error,v['error_east_north_arcsec'],atol=1e-12)
                self.assertAlmostEqual(np.linalg.norm(error),v['error_arcsec'])
                self.assertAlmostEqual(float(error@np.linalg.solve(cal,error)),v['mahalanobis2_calibrated'])

    def test_default_measurement_remains_separate(self):
        manifest=json.loads((study.ROOT/'web/data/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['analysis_sha256'],'24e6906adb049f7fc39a73552e9a0764d55108c30d5051ddb25f96078824e7a1')
        self.assertFalse(self.overview['current_measurement_changed'])

    def test_coupled_exceptions_do_not_hide_valid_baseline_fits(self):
        audit=read('failure-audit')
        self.assertFalse(audit['original_results_modified'])
        self.assertEqual(audit['recovered_baseline'],0)
        self.assertEqual(audit['source_sha256'],study.bench.digest(study.ROOT/'scripts/audit_covariance_failures.py'))
        total=sum('fit_exception' in r['models']['previous']['quality_reasons'] for f in self.fields['validation'] for r in f['injections']+f['real_controls'])
        self.assertEqual(len(audit['corrections']),total)
        for name,h in audit['input_sha256'].items():self.assertEqual(study.bench.digest(OUT/name),h)


if __name__=='__main__':unittest.main()

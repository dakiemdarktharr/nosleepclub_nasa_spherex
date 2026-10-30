"""Published 0.9 products: fair selection, calibration isolation and support audit."""
import copy
from pathlib import Path
import unittest
import numpy as np
from scripts import ablation_study as s
from scripts import conditional_covariance as cc
from scripts.build_ablation_overview import comparison


class AblationProducts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design=s.read(s.OUT/'design.json');cls.selection=s.read(s.OUT/'selection.json');cls.cal=s.read(s.OUT/'calibrator.json')
        cls.seal=s.read(s.OUT/'validation-protocol.json');cls.overview=s.read(s.OUT/'overview.json')
        cls.results={phase:[s.read(s.OUT/(phase+'-'+i['field']['id']+'.json')) for i in items] for phase,items in cls.design['fields'].items()}

    def test_hash_chain_and_frozen_rules(self):
        self.assertEqual(self.design['source_hashes'],s.sources());self.assertEqual(self.design['rules'],s.RULES)
        self.assertEqual(self.design['point_model_rules'],s.model.RULES);self.assertEqual(self.design['covariance_rules'],cc.RULES)
        for name,key in [('design.json','design_sha256'),('calibrator.json','calibrator_sha256'),('selection.json','selection_sha256')]:
            self.assertEqual(self.seal[key],s.bench.digest(s.OUT/name))
        for name,digest in self.overview['input_sha256'].items():self.assertEqual(s.bench.digest(s.OUT/name),digest)
        self.assertEqual(self.overview['source_sha256'],s.bench.digest(s.ROOT/'scripts/build_ablation_overview.py'))
        self.assertEqual(self.overview['guard_sha256'],s.bench.digest(s.ROOT/'scripts/run_ablation.py'))

    def test_roles_and_reference_ids_are_disjoint(self):
        roles=list(self.design['selected_exposure_ids'])
        for i,a in enumerate(roles):
            for b in roles[i+1:]:self.assertFalse(set(self.design['selected_exposure_ids'][a])&set(self.design['selected_exposure_ids'][b]))
        for items in self.design['fields'].values():
            for item in items:
                ids={role:{r['catalog']['source_id'] for r in item['references'] if r['split']==role} for role in ['training','heldout']}
                self.assertFalse(ids['training']&ids['heldout'])

    def test_model_selection_and_feature_threshold_recompute_from_development_only(self):
        actual=s.choose(self.results['development'])
        for key,value in actual.items():self.assertEqual(self.selection[key],value)
        self.assertEqual(self.selection['feature_thresholds'],s.feature_thresholds(self.results['development']))
        for ident,digest in self.selection['source_results'].items():self.assertEqual(s.bench.digest(s.OUT/('development-'+ident+'.json')),digest)
        for result in self.results['development']:
            leave=s.choose([r for r in self.results['development'] if r is not result])['selected_model']
            self.assertEqual(next(r['selected_model'] for r in self.selection['leave_one_field_out'] if r['excluded_field']==result['field']['id']),leave)

    def test_covariance_recomputes_from_calibration_only_and_matches_selected_model(self):
        rows=[r for f in self.results['calibration'] for r in f['injections']]
        actual=cc.fit(rows,self.selection['selected_model'],self.selection['feature_thresholds'])
        for key,value in actual.items():self.assertEqual(self.cal[key],value)
        for ident,digest in self.cal['source_results'].items():self.assertEqual(s.bench.digest(s.OUT/('calibration-'+ident+'.json')),digest)

    def test_every_attempt_is_retained_and_models_have_independent_outcomes(self):
        for phase,results in self.results.items():
            for result in results:
                self.assertEqual(len(result['injections']),len(s.RULES[phase+'_positions_px'])*8)
                self.assertEqual(result['injection_summary'],s.summarize(result['injections'],result['kinds']))
                self.assertEqual(result['real_summary'],s.summarize(result['real_controls'],result['kinds']))
                for r in result['injections']+result['real_controls']:self.assertEqual(set(r['models']),set(result['kinds']))

    def test_validation_routing_psd_and_coverage_match_published_data(self):
        selected=self.selection['selected_model'];allrows=[]
        for result in self.results['validation']:
            for r in result['injections']+result['real_controls']:
                expected=copy.deepcopy(r);s.apply_record(expected,self.cal)
                self.assertEqual(r,expected)
                v=r['models'][selected]
                for name in ['global_calibration','conditional_calibration']:
                    out=v.get(name,{})
                    if not out.get('supported'):continue
                    raw=np.asarray(v['covariance_arcsec2']);cov=np.asarray(out['covariance_arcsec2']);e=np.asarray(v['error_east_north_arcsec'])
                    self.assertGreaterEqual(np.linalg.eigvalsh(cov-raw).min(),-1e-9)
                    self.assertAlmostEqual(out['mahalanobis2'],float(e@np.linalg.solve(cov,e)))
                    self.assertAlmostEqual(out['area_inflation'],np.sqrt(np.linalg.det(cov)/np.linalg.det(raw)))
            allrows.extend(result['injections'])
        self.assertEqual(self.overview['coverage_gate'],s.coverage_gate(allrows,selected))
        self.assertEqual(self.overview['validation']['injections'],comparison(allrows,selected))
        p=self.overview['diagnostic_patch'];same=[r for r in allrows if r['field_id']==p['field']['id'] and r['patch_index']==p['patch_index'] and r['models'][selected]['accepted'] and r['models'][selected].get('conditional_calibration',{}).get('supported')]
        self.assertEqual(p['attempted_accepted_supported'],len(same))
        self.assertEqual(p['covered68'],sum(r['models'][selected]['conditional_calibration']['mahalanobis2']<=cc.RULES['ellipse68_threshold'] for r in same))
        self.assertEqual(p['map_center_px'],[p['anchor_px'][0]+64.5,127.5-p['anchor_px'][1]])

    def test_default_wise_measurement_remains_separate(self):
        manifest=s.read(s.ROOT/'web/data/manifest.json')
        self.assertFalse(self.overview['current_measurement_changed'])
        self.assertEqual(manifest['analysis_sha256'],'24e6906adb049f7fc39a73552e9a0764d55108c30d5051ddb25f96078824e7a1')


if __name__=='__main__':unittest.main()

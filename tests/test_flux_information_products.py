import hashlib
import json
from pathlib import Path
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SUMMARY=ROOT/'web/data/flux-information/development-summary.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def tr(f,m):return np.trace(np.linalg.solve(f,m))/2


class FluxInformationProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=json.loads(SUMMARY.read_text(encoding='utf-8'))
        rules=cls.p['rules']
        cls.boot=np.random.default_rng(rules['bootstrap_seed']).integers(0,64,size=(rules['bootstrap_draws'],64))

    def test_provenance_and_immutable_raw_if_available(self):
        p=self.p['provenance'];self.assertEqual(sha(ROOT/p['design_path']),p['design_sha256'])
        self.assertEqual(sha(ROOT/'scripts/build_flux_information_report.py'),p['builder_sha256'])
        for name,key in [('data/raw/benchmark/flux-information-development.json','raw_report_sha256'),
                         ('data/raw/benchmark/bias-gaussian64-development.json','bias_control_sha256'),
                         ('data/raw/benchmark/continuous-epsf-development.json','continuous_control_sha256')]:
            path=ROOT/name
            if path.exists():self.assertEqual(sha(path),p[key])
        self.assertEqual(len(self.p['field_provenance']),3)

    def test_post_run_per_exposure_matrices_reconstruct_every_total(self):
        self.assertEqual(len(self.p['cases']),6)
        for c in self.p['cases']:
            for geo,audit in zip(c['geometry'],c['post_run_geometry_audit']):
                self.assertEqual(len(audit['per_exposure']),len(geo['observations']))
                sums={k:np.zeros((2,2)) for k in ['F','known','G','V']}
                for i,(row,obs) in enumerate(zip(audit['per_exposure'],geo['observations'])):
                    self.assertEqual(row['obs_id'],obs['obs_id']);a=row['amplitude'];I=row['target_information']
                    self.assertAlmostEqual(a,geo['amplitudes'][i],places=12)
                    self.assertAlmostEqual(a*np.sqrt(I),obs['true_flux_snr_projected'],places=10)
                    s=np.asarray(row['projected_derivative_gram']);t=np.asarray(row['known_flux_derivative_gram'])
                    sums['F']+=a*a*s;sums['known']+=a*a*t;sums['G']+=(a*a+2/I)*s;sums['V']+=(a*a+1/I)*s
                for a,b in [('F','fisher_effective'),('known','fisher_known'),('G','expected_jtj_matched'),('V','expected_score_covariance_matched')]:
                    np.testing.assert_allclose(sums[a],geo[b],rtol=1e-10,atol=1e-10)
                    np.testing.assert_allclose(sums[a],audit['recomputed_matrices'][a],rtol=1e-10,atol=1e-10)
                self.assertEqual(geo['dof'],sum(r['native_pixels']-r['nuisance_rank']-1 for r in geo['observations']))

    def test_every_trial_and_group_bootstrap_recomputes(self):
        for c in self.p['cases']:
            self.assertEqual([r['draw'] for r in c['records']],list(range(64)))
            for condition in self.p['rules']['truth_conditions']:
                for epoch,geo in enumerate(c['geometry']):
                    f=np.asarray(geo['fisher_effective']);rows=[r['conditions'][condition][epoch] for r in c['records']]
                    good=[r for r in rows if 'failure' not in r];s=c['summaries'][condition][epoch]
                    self.assertEqual((s['attempts'],s['successful'],s['failures']),(64,len(good),64-len(good)))
                    for r in good:
                        score=np.asarray(r['profile_score']);self.assertAlmostEqual(r['score_q'],float(score@np.linalg.solve(f,score)),places=8)
                        h=np.asarray(r['hessians']);change=np.linalg.norm(h[0]-h[1])/max(np.linalg.norm(h[1]),1e-15)
                        self.assertAlmostEqual(r['hessian_relative_step_change'],change,places=10)
                        self.assertEqual(r['hessian_stable'],bool(change<=.05))
                    if len(good)!=64:continue
                    self.assertEqual(s['hessian_stable'],sum(r['hessian_stable'] for r in good))
                    for name,values in [('jtj',[r['jtj'] for r in good]),('hessian_002',[r['hessians'][0] for r in good]),('hessian_004',[r['hessians'][1] for r in good])]:
                        mats=np.asarray(values);z=np.array([tr(f,m) for m in mats]);out=s[name]
                        np.testing.assert_allclose(out['mean_matrix'],mats.mean(axis=0),rtol=1e-11,atol=1e-11)
                        self.assertAlmostEqual(out['normalized_trace'],z.mean(),places=10)
                        np.testing.assert_allclose(out['draw_bootstrap_95'],np.quantile(z[self.boot].mean(axis=1),[.025,.975]),atol=1e-10)
                    scores=np.asarray([r['profile_score'] for r in good]);cov=np.cov(scores,rowvar=False)
                    np.testing.assert_allclose(s['score_covariance'],cov,atol=1e-10)
                    np.testing.assert_allclose(s['mean_score_draw_bootstrap_95'],np.quantile(scores[self.boot].mean(axis=1),[.025,.975],axis=0),atol=1e-10)
                    extra=c['additional_diagnostics'][condition][epoch]
                    self.assertAlmostEqual(extra['score_covariance_normalized_trace'],float(tr(f,cov)),places=10)
                    sampled=scores[self.boot];centered=sampled-sampled.mean(axis=1,keepdims=True)
                    covs=np.einsum('bni,bnj->bij',centered,centered)/63
                    z=np.array([tr(f,v) for v in covs])
                    np.testing.assert_allclose(extra['score_covariance_draw_bootstrap_95_posthoc'],np.quantile(z,[.025,.975]),atol=1e-10)
                    self.assertAlmostEqual(s['mean_reduced_chi2'],np.mean([r['profile_chi2'] for r in good])/geo['dof'],places=10)

    def test_all_public_trials_match_immutable_raw_if_available(self):
        path=ROOT/'data/raw/benchmark/flux-information-development.json'
        if not path.exists():self.skipTest('Raw cache not present')
        raw=json.loads(path.read_text(encoding='utf-8'))
        for c in self.p['cases']:
            original=next(x for x in raw['cases'] if x['field']==c['field'] and x['snr_per_frame']==c['snr_per_frame'])
            for key in ['geometry','records','summaries','signal_variance_replay']:
                self.assertEqual(c[key],original[key])


if __name__=='__main__':unittest.main()

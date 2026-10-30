import hashlib
import json
from pathlib import Path
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SUMMARY=ROOT/'web/data/sandwich/development-summary.json'
OVERVIEW=ROOT/'web/data/sandwich/overview.json'
METHODS=['gauss_newton','profile_hessian','exposure_sandwich']


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class SandwichProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(SUMMARY.read_text(encoding='utf-8'))
        cls.overview=json.loads(OVERVIEW.read_text(encoding='utf-8'))

    def test_overview_matches_audited_report_and_has_no_draw_rows(self):
        overview=self.overview;full=self.data;provenance=overview['provenance']
        self.assertEqual(provenance['public_report_path'],SUMMARY.relative_to(ROOT).as_posix())
        self.assertEqual(provenance['public_report_sha256'],digest(SUMMARY))
        self.assertEqual(provenance['public_report_bytes'],SUMMARY.stat().st_size)
        for key in ['rules','limitations','field_provenance']:
            self.assertEqual(overview[key],full[key])
        self.assertEqual(len(overview['cases']),len(full['cases']))
        for case,original in zip(overview['cases'],full['cases']):
            for key in ['field','source','snr_per_frame','anchor_sky_px','truth_delta_sky_px','noise_seed','summary']:
                self.assertEqual(case[key],original[key])
            for side in ['frozen_baseline','candidate']:
                subset=case['original_background'][side];raw=original['original_background'][side]
                for key,value in subset.items():self.assertEqual(value,raw.get(key))
            self.assertEqual(case['original_background']['candidate_epoch_positions_px'],
                             [e['position_px'] for e in original['original_background']['candidate']['epochs']])
            self.assertEqual(len(case['lower_objective_mode_anomalies']),original['summary']['lower_fixed_objective_epochs'])
            def check(value):
                if isinstance(value,dict):
                    self.assertFalse({'records','epochs','per_frame','exposures'} & set(value))
                    for v in value.values():check(v)
                elif isinstance(value,list):
                    self.assertNotEqual(len(value),128)
                    for v in value:check(v)
            check(case)
        for key,value in overview['aggregate_counts'].items():
            self.assertEqual(value,sum(case['summary'][key] for case in full['cases']))

    def test_hashes_and_optional_raw(self):
        p=self.data['provenance']
        self.assertEqual(digest(ROOT/p['design_path']),p['design_sha256'])
        self.assertEqual(digest(ROOT/'scripts/build_sandwich_report.py'),p['builder_sha256'])
        for path,key in [('data/raw/benchmark/sandwich-development.json','raw_report_sha256'),
                         ('data/raw/benchmark/bias-gaussian64-development.json','baseline_sha256'),
                         ('data/raw/benchmark/continuous-epsf-development.json','continuous_sha256')]:
            file=ROOT/path
            if file.exists():self.assertEqual(digest(file),p[key])

    def test_every_score_meat_hessian_covariance_and_q(self):
        for case in self.data['cases']:
            self.assertEqual([r['draw'] for r in case['records']],list(range(128)))
            for row in case['records']:
                if 'failure' in row:continue
                error=np.asarray(row['error_east_north_arcsec'])
                for epoch in row['epochs']:
                    s=epoch['sandwich']
                    if 'exposures' not in s:continue
                    u=np.array([x[1] for x in s['exposures']]);j=np.array([x[2] for x in s['exposures']])
                    np.testing.assert_allclose(u.T@u,s['meat'],rtol=1e-10,atol=1e-10)
                    np.testing.assert_allclose(u.sum(axis=0),s['score_sum'],atol=1e-10)
                    self.assertAlmostEqual(np.linalg.norm(u-j),s['scalar_vs_residual_jacobian_difference'],places=10)
                    h=np.asarray(s['hessians']);change=np.linalg.norm(h[0]-h[1])/max(np.linalg.norm(h[1]),1e-15)
                    self.assertAlmostEqual(change,s['hessian_relative_step_change'],places=10)
                    if s['supported']:
                        inverse=np.linalg.inv(h[0]);expected=s['correction_factor']*inverse@(u.T@u)@inverse.T
                        np.testing.assert_allclose(expected,s['covariance_px2'],atol=1e-10)
                for method in METHODS:
                    entry=row['methods'][method]
                    if not entry['supported']:continue
                    for kind in ['centroid_only','plus_registration']:
                        part=entry[kind];cov=np.asarray(part['covariance_arcsec2'])
                        self.assertAlmostEqual(part['q'],float(error@np.linalg.solve(cov,error)),places=8)

    def test_all_selections_denominators_coverage_and_area(self):
        cuts=self.data['rules']['ellipse_thresholds']
        selectors={'all_attempts':lambda r:True,'numeric':lambda r:r.get('numeric_valid',False),
                   'accepted':lambda r:r.get('accepted',False),
                   'common_supported':lambda r:r.get('numeric_valid',False) and all(r['methods'][m]['supported'] for m in METHODS),
                   'common_accepted':lambda r:r.get('accepted',False) and all(r['methods'][m]['supported'] for m in METHODS)}
        for case in self.data['cases']:
            for group,predicate in selectors.items():
                rows=[r for r in case['records'] if predicate(r)];valid=[r for r in rows if r.get('numeric_valid')]
                summary=case['summary']['selections'][group];self.assertEqual((summary['attempts'],summary['numeric']),(len(rows),len(valid)))
                for method in METHODS:
                    available=[r['methods'][method] for r in valid if r['methods'][method]['supported']]
                    ms=summary['methods'][method];self.assertEqual(ms['supported'],len(available));self.assertEqual(ms['unsupported'],len(valid)-len(available))
                    for kind in ['centroid_only','plus_registration']:
                        cov=[np.asarray(v[kind]['covariance_arcsec2']) for v in available]
                        for level,threshold in cuts.items():
                            report=ms[kind]['coverage'][level];self.assertEqual(report['denominator'],len(available))
                            self.assertEqual(report['inside'],sum(v[kind]['q']<=threshold for v in available))
                            n=len(available);k=report['inside']
                            if n:
                                z=1.959963984540054;p=k/n;den=1+z*z/n
                                center=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
                                np.testing.assert_allclose(report['wilson_95'],[max(0,center-half),min(1,center+half)],atol=1e-12)
                            else:self.assertIsNone(report['wilson_95'])
                        if cov:
                            areas=[np.pi*cuts['68']*np.sqrt(np.linalg.det(a)) for a in cov]
                            axes=[np.sqrt(cuts['68']*np.linalg.eigvalsh(a).max()) for a in cov]
                            self.assertAlmostEqual(ms[kind]['median_ellipse68_area_arcsec2'],float(np.median(areas)),places=9)
                            self.assertAlmostEqual(ms[kind]['p90_ellipse68_semimajor_arcsec'],float(np.percentile(axes,90)),places=9)
                if valid:
                    errors=np.array([r['error_east_north_arcsec'] for r in valid]);self.assertAlmostEqual(summary['rms_arcsec'],float(np.sqrt(np.mean(np.sum(errors**2,axis=1)))),places=10)

    def test_every_public_row_matches_optional_raw(self):
        path=ROOT/'data/raw/benchmark/sandwich-development.json'
        if not path.exists():self.skipTest('Raw cache unavailable')
        raw=json.loads(path.read_text(encoding='utf-8'))
        for case in self.data['cases']:
            original=next(c for c in raw['cases'] if c['field']==case['field'] and c['snr_per_frame']==case['snr_per_frame'])
            for a,b in zip(case['records'],original['records']):
                for k in ['draw','numeric_valid','accepted','quality_reasons','error_east_north_arcsec','methods']:
                    if k in b:self.assertEqual(a[k],b[k])
                for x,y in zip(a.get('epochs',[]),b.get('epochs',[])):
                    for k in ['position_px','covariance_px2','success','at_boundary','quality','profile','mode_diagnostic']:
                        self.assertEqual(x[k],y[k])
                    if 'exposures' in x['sandwich']:
                        self.assertEqual(x['sandwich']['exposures'],[[e['obs_id'],e['score'],e['residual_jacobian_score']] for e in y['sandwich']['exposures']])


if __name__=='__main__':unittest.main()

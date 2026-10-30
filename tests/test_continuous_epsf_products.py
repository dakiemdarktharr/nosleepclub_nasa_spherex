import hashlib
import json
from pathlib import Path
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SUMMARY=ROOT/'web/data/continuous-epsf/development-summary.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class ContinuousEpsfProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product=json.loads(SUMMARY.read_text(encoding='utf-8'))

    def test_provenance_and_optional_raw_hashes(self):
        p=self.product['provenance']
        self.assertEqual(p['design_sha256'],sha(ROOT/p['design_path']))
        self.assertEqual(p['builder_sha256'],sha(ROOT/'scripts/build_continuous_epsf_report.py'))
        self.assertEqual(len(self.product['field_provenance']),3)
        for path,key in [('data/raw/benchmark/continuous-epsf-development.json','raw_report_sha256'),
                         ('data/raw/benchmark/bias-gaussian64-development.json','paired_baseline_sha256'),
                         ('data/raw/benchmark/profile-gaussian64-development.json','baseline_profile_sha256')]:
            file=ROOT/path
            if file.exists():self.assertEqual(sha(file),p[key])

    def test_every_q_and_group_summary_recomputes(self):
        cases=self.product['cases']; self.assertEqual(len(cases),6)
        groups={'baseline_numeric':lambda b,c:b['valid'],'baseline_accepted':lambda b,c:b['accepted'],
                'candidate_numeric':lambda b,c:c['valid'],'candidate_accepted':lambda b,c:c['accepted'],
                'common_numeric':lambda b,c:b['valid'] and c['valid'],'common_accepted':lambda b,c:b['accepted'] and c['accepted']}
        for case in cases:
            rows=case['paired_draws'];self.assertEqual([r['draw'] for r in rows],list(range(64)))
            for row in rows:
                for item in [row['baseline'],row['candidate']]:
                    if not item['valid']:continue
                    error=np.asarray(item['error'])
                    for qkey,covkey in [('q','covariance'),('profile_q','profile_covariance')]:
                        if item.get(qkey) is None:continue
                        cov=np.asarray(item[covkey]);self.assertGreater(np.linalg.eigvalsh(cov).min(),0)
                        self.assertAlmostEqual(item[qkey],float(error@np.linalg.solve(cov,error)),places=8)
            for label,select in groups.items():
                subset=[r for r in rows if select(r['baseline'],r['candidate'])]
                summary=case['gaussian_summary'][label];self.assertEqual(summary['count'],len(subset))
                for label2,side,qkey in [('baseline_gn','baseline','q'),('baseline_profile','baseline','profile_q'),
                                         ('candidate_gn','candidate','q'),('candidate_profile','candidate','profile_q')]:
                    q=[r[side][qkey] for r in subset if r[side]['valid'] and r[side].get(qkey) is not None]
                    entry=summary[label2];self.assertEqual(entry['available'],len(q))
                    self.assertEqual(entry['within68'],sum(x<=self.product['ellipse_thresholds']['68'] for x in q))
                    self.assertEqual(entry['within95'],sum(x<=self.product['ellipse_thresholds']['95'] for x in q))
                    covkey='profile_covariance' if qkey=='profile_q' else 'covariance'
                    areas=[np.pi*self.product['ellipse_thresholds']['68']*np.sqrt(np.linalg.det(r[side][covkey]))
                           for r in subset if r[side]['valid'] and r[side].get(qkey) is not None]
                    if areas:self.assertAlmostEqual(entry['median_area68_arcsec2'],float(np.median(areas)),places=10)
                for side in ['baseline','candidate']:
                    errors=[np.linalg.norm(r[side]['error']) for r in subset if r[side]['valid'] and 'error' in r[side]]
                    entry=summary[side+'_error'];self.assertEqual(entry['available'],len(errors))
                    if errors:self.assertAlmostEqual(entry['rms_arcsec'],float(np.sqrt(np.mean(np.square(errors)))),places=10)
                common=[r for r in subset if r['baseline']['valid'] and r['candidate']['valid']]
                self.assertEqual(summary['paired_error_count'],len(common))
                if common:
                    rms=lambda side:np.sqrt(np.mean([np.dot(r[side]['error'],r[side]['error']) for r in common]))
                    self.assertAlmostEqual(summary['paired_rms_delta_arcsec'],float(rms('candidate')-rms('baseline')),places=10)

    def test_public_rows_match_raw_cache_when_present(self):
        path=ROOT/'data/raw/benchmark/continuous-epsf-development.json'
        if not path.exists():self.skipTest('Raw cache not available')
        raw=json.loads(path.read_text(encoding='utf-8'))
        for case in self.product['cases']:
            source=next(c for c in raw['cases'] if c['field']==case['field'] and c['snr_per_frame']==case['snr_per_frame'])
            self.assertEqual(case['baseline_replay'],source['baseline_replay'])
            for row,original in zip(case['paired_draws'],source['records']):
                for side in ['baseline','candidate']:
                    a=row[side];b=original[side]
                    self.assertEqual(a['valid'],b['numeric_valid']);self.assertEqual(a['accepted'],b['accepted'])
                    self.assertEqual(a['reasons'],b.get('quality_reasons',[]))
                    if 'error' in a:self.assertEqual(a['error'],b['error_east_north_arcsec'])
                    if 'point' in a:self.assertEqual(a['point'],[b['before']['position_px'],b['after']['position_px']])
                    if a.get('covariance') is not None:self.assertEqual(a['covariance'],b['covariance_arcsec2' if side=='baseline' else 'gauss_newton_covariance_arcsec2'])
                    if a.get('q') is not None:self.assertEqual(a['q'],b['mahalanobis2_raw' if side=='baseline' else 'gauss_newton_q'])
                    if side=='candidate' and a.get('profile_q') is not None:
                        self.assertEqual(a['profile_q'],b['profile_q']);self.assertEqual(a['profile_covariance'],b['profile_covariance_arcsec2'])
            for side in ['baseline','candidate']:
                a=case['original_background'][side];b=source['original_background'][side]
                self.assertEqual(a['error'],b['error_east_north_arcsec'])


if __name__=='__main__':unittest.main()

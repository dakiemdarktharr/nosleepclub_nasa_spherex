"""Catalog units, ePSF interpolation, lock integrity and all-attempt accounting."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
import numpy as np
from scipy.ndimage import spline_filter
from scripts import release_analysis as release
from tests.test_motion import synthetic_frame

ROOT=Path(__file__).resolve().parents[1]


class CatalogAndPSF(unittest.TestCase):
    def test_tile_corrections_are_additive_and_ra_uses_cos_declination(self):
        row={'ra_pm':130.,'dec_pm':-30.,'pmra':.1,'pmdec':-.2}
        c={'offsetra_ta':.00001,'offsetdec':-.00002,'offsetpmra':.01,'offsetpmdec':.02}
        got=release.corrected_position(row,c,57170+365.25)
        expected=[130.+.00001/np.cos(np.deg2rad(-30))+.11/(3600*np.cos(np.deg2rad(-30))),-30.-.00002-.18/3600]
        np.testing.assert_allclose(got,expected,rtol=0,atol=1e-12)

    def test_bilinear_psf_is_continuous_and_normalized_over_zones(self):
        f=synthetic_frame();template=f['epsf_table'];table=np.repeat(template,4)
        yy,xx=np.indices((33,33))
        for i,(x,y) in enumerate([(0.,0.),(63.,0.),(0.,63.),(63.,63.)]):
            table['XCENTER'][i]=x;table['YCENTER'][i]=y
            table['EPSF'][i]=np.exp(-((xx-16-i*.1)**2+(yy-16)**2)/(2*4.2**2))
        f['epsf_table']=table
        value,_=release.epsf(f,31.5,31.5,'bilinear')
        expected=sum(p/p.sum() for p in table['EPSF'])/4*25
        np.testing.assert_allclose(value,spline_filter(expected,order=3),atol=1e-11)
        a,_=release.epsf(f,31.5-1e-4,31.5,'bilinear');b,_=release.epsf(f,31.5+1e-4,31.5,'bilinear')
        self.assertLess(np.max(np.abs(a-b)),1e-6)


class ReleaseEvidence(unittest.TestCase):
    def test_protocol_has_30_new_disjoint_patches_and_exact_frozen_sources(self):
        p=release.validate_lock();xy=np.array(p['positions_px']);old=np.array(p['excluded_old_positions_px'])
        self.assertEqual(len(xy),30)
        distances=np.linalg.norm(xy[:,None]-xy[None,:],axis=2);np.fill_diagonal(distances,np.inf)
        self.assertGreaterEqual(distances.min(),20.)
        self.assertGreaterEqual(np.linalg.norm(xy[:,None]-old[None,:],axis=2).min(),20.)
        self.assertEqual(p['source_sha256'],release.sources())
        self.assertEqual(p['discovery']['qr3']['rows'],0);self.assertEqual(p['discovery']['qr3-tap']['rows'],0)
        self.assertEqual(p['catalog_screening']['selected'],len(p['catalog']))

    def test_results_retain_every_attempt_and_match_lock(self):
        for name in ['broad','strict']:
            path=ROOT/f'web/data/release/{name}.json'
            if not path.exists():self.skipTest('Long experiment not yet complete')
            p=json.loads(path.read_text());r=p['result']
            self.assertEqual(p['protocol_sha256'],sha256((ROOT/'web/data/release/protocol.json').read_bytes()).hexdigest())
            self.assertEqual(p['source_sha256'],release.sources());self.assertEqual(len(r['records']),720)
            identities={(v['position_index'],v['model'],v['truth_psf'],v['flux_scale'],tuple(v['truth_delta_px'])) for v in r['records']}
            self.assertEqual(len(identities),720)
            self.assertTrue(all(g['attempted']==60 for g in r['groups']))
            self.assertTrue(all(g['within_68_ellipse']<=g['valid']<=60 for g in r['groups']))

    def test_summary_input_hashes_and_gate_cannot_hide_failed_groups(self):
        from scripts import summarize_release
        path=ROOT/'web/data/release/summary.json';summary=json.loads(path.read_text())
        self.assertEqual(summary['source_sha256'],sha256(Path(summarize_release.__file__).read_bytes()).hexdigest())
        for name,digest in summary['input_sha256'].items():
            self.assertEqual(digest,sha256((path.parent/name).read_bytes()).hexdigest())
        self.assertEqual(len(summary['groups']),16)
        self.assertEqual(summary['point_estimate_gate_passed'],[])
        for group in summary['groups']:
            low,high=group['improvement_95_interval_percent']
            self.assertLessEqual(low,high)
            self.assertTrue(0<group['common_valid_pairs']<=60)

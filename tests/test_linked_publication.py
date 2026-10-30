import copy
from hashlib import sha256
import json
import unittest
import xml.etree.ElementTree as ET

import numpy as np

from scripts import publish_linked_study as publication
from scripts import run_wise_linked_study as study


def seal(row):
    row.pop('record_sha256',None)
    row['record_sha256']=sha256(study.encoded(row)).hexdigest()
    return row


def fit_record(config,variant,epoch,delta):
    position=np.array([31.5,31.5])+(np.array(delta) if epoch=='after' else 0)
    flux_coefficient=1. if variant['mode']=='independent' else 1.2
    obs=config+'-'+epoch
    residual=np.array([.1,-.2,.3,-.4,.5,-.6,.7,-.8]);weight=np.ones(8)
    chi=float(residual@residual)
    starts=[{'success':True,'position':position.tolist(),'chi2':chi} for _ in range(5)]
    mode={'position':position.tolist(),'chi2':chi,'delta_chi2':0.,'origin':'point','member_count':6}
    fit={'mode':variant['mode'],'data_unit':'MJy / sr','position':position.tolist(),'at_boundary':False,
         'position_rank':2,'position_covariance_px2':[[2.,.2],[.2,1.]],'profile_hessian':{'supported':False},
         'residuals':[residual.tolist()],'weights':[weight.tolist()],'weighted_residual':residual.tolist(),
         'nuisance_ranks':[1],'dof':4,'source_rank':1,'chi2_raw':chi,'chi2_weighted':chi,
         'flux_basis':[[flux_coefficient]],'flux_parameters_jy':[2.], 'flux_covariance_jy2':[[4.]],
         'per_frame_flux_jy':[2*flux_coefficient], 'per_frame_flux_covariance_jy2':[[4*flux_coefficient**2]],
         'per_frame_error_jy':[2*flux_coefficient], 'conditional_frame_snr':[1.], 'negative_frame_flux':[False],
         'irls':{'converged':True,'iterations':2,'max_iterations':20,'next_weight_max_difference':0.,
                 'position_max_change':0.,'weight_tolerance':1e-3,'position_tolerance_px':1e-4},
         'inference_supported':True,'inference_reasons':[],
         'final_mode_audit':{'requested':True,'starts':starts,'modes':[mode],'near_best_modes':[mode],
                             'near_best_count':1,'all_starts_failed':False,'point_chi2':chi,
                             'best_improvement_chi2':0.,'better_than_point':False}}
    sample={'obs_id':obs,'x':list(range(8)),'y':[0]*8,'error_mjysr':[1.]*8,'selected_pixels':8,'nuisance_rank':1,
            'epsf_zone':1,'nuisance_provenance':'synthetic','renderer_provenance':'synthetic',
            'cutout_url':'https://synthetic.invalid','raw_sha256':'synthetic'}
    predictions=[] if variant['mode']=='independent' else [{'obs_id':obs,'relative_coefficient':flux_coefficient}]
    return seal({'configuration':config,'variant':variant['id'],'epoch':epoch,'obs_ids':[obs],
                 'status':'fit_completed','samples':[sample],'predictions':predictions,'fit':fit})


def fixture():
    rows=[]
    for config in publication.CONFIGS:
        for variant in publication.VARIANTS:
            for epoch in ('before','after'):
                if config=='broad' and variant['id'] in ('independent','shared_r7_68_a0'):
                    delta=(.1,.2) if variant['id']=='independent' else (.4,.3)
                    rows.append(fit_record(config,variant,epoch,delta))
                else:
                    rows.append(seal({'configuration':config,'variant':variant['id'],'epoch':epoch,
                                      'obs_ids':[],'status':'preparation_failed','error':'synthetic unavailable'}))
    return rows


class LinkedPublicationTests(unittest.TestCase):
    def test_attempt_counts_pairs_failures_and_spread(self):
        audit=publication.audit_records(fixture())
        self.assertEqual(audit['counts']['planned_epoch_attempts'],28)
        self.assertEqual(audit['counts']['fit_completed'],4)
        self.assertEqual(audit['counts']['failures'],24)
        self.assertEqual(len(audit['pairs']),14)
        self.assertEqual(sum(r['status']=='preparation_failed' for r in audit['attempt_audits']),24)
        expected=np.linalg.norm(publication.T@np.array([.3,.1]))
        broad=audit['configurations'][0]
        self.assertAlmostEqual(broad['max_pairwise_spread_arcsec'],expected,places=12)
        self.assertAlmostEqual(broad['maximum_change_from_independent_arcsec'],expected,places=12)
        self.assertEqual(audit['configurations'][1]['available_pairs'],0)
        self.assertIsNone(audit['configurations'][1]['max_pairwise_spread_arcsec'])

    def test_renderer_metadata_failure_is_screened_and_counted(self):
        rows=fixture();row=rows[0];row['renderer_metadata_failed']=True;row['fit']['inference_supported']=False
        seal(row)
        audit=publication.audit_records(rows)
        self.assertEqual(audit['counts']['renderer_metadata_failures'],1)
        result=next(a for a in audit['attempt_audits'] if (a['configuration'],a['variant'],a['epoch'])==(row['configuration'],row['variant'],row['epoch']))
        self.assertIn('renderer_metadata_failed',result['solver_screening_reasons'])
        self.assertFalse(result['solver_screening_passed'])

    def test_tampering_detected_even_with_recomputed_checksum(self):
        for change in ('residual','flux','flux_covariance','snr','convergence','mode','boundary','weight','pixel_order'):
            rows=fixture();row=rows[0];fit=row['fit']
            if change=='residual':fit['residuals'][0][0]+=1
            if change=='flux':fit['per_frame_flux_jy'][0]+=1
            if change=='flux_covariance':fit['per_frame_flux_covariance_jy2'][0][0]+=1
            if change=='snr':fit['conditional_frame_snr'][0]+=1
            if change=='convergence':fit['irls']['converged']=False
            if change=='mode':fit['final_mode_audit']['near_best_count']=2
            if change=='boundary':fit['at_boundary']=True
            if change=='weight':fit['weights'][0][0]=-1.
            if change=='pixel_order':row['samples'][0]['x'][0:2]=[1,0]
            seal(row)
            with self.subTest(change=change),self.assertRaises(ValueError):publication.audit_records(rows)

    def test_duplicate_missing_and_unverified_checksum_rejected(self):
        rows=fixture()
        with self.assertRaises(ValueError):publication.audit_records(rows[:-1])
        rows[-1]=copy.deepcopy(rows[0])
        with self.assertRaises(ValueError):publication.audit_records(rows)
        rows=fixture();rows[0]['fit']['chi2_raw']+=1
        with self.assertRaisesRegex(ValueError,'checksum'):publication.audit_records(rows)

    def test_public_products_recompute_and_provenance(self):
        if not publication.FULL.exists() or not publication.OVERVIEW.exists():
            self.skipTest('public product has not been built')
        full_bytes=publication.FULL.read_bytes();full=json.loads(full_bytes)
        overview=json.loads(publication.OVERVIEW.read_text(encoding='utf-8'))
        self.assertEqual(overview['provenance']['public_report_sha256'],sha256(full_bytes).hexdigest())
        self.assertEqual(overview['provenance']['public_report_bytes'],len(full_bytes))
        self.assertEqual(overview,publication.make_overview(full,sha256(full_bytes).hexdigest(),len(full_bytes)))
        self.assertEqual(full['provenance']['publisher_source_sha256'],sha256(publication.Path(publication.__file__).read_bytes()).hexdigest())
        audit=publication.audit_records(full['records'])
        publication.equal(audit['counts'],full['counts'],'counts')
        publication.equal(audit['pairs'],full['pairs'],'pairs')
        publication.equal(audit['configurations'],overview['configurations'],'configuration overview')
        self.assertEqual(len(overview['pairs']),14)
        self.assertNotIn('records',overview);self.assertNotIn('attempt_audits',overview)
        self.assertNotIn('scientific_supported',json.dumps(overview))
        self.assertLess(publication.OVERVIEW.stat().st_size,150_000)
        self.assertEqual(sum(not p['solver_screening_both'] for p in overview['pairs'] if p['configuration']=='strict'),7)
        self.assertEqual(sum(not p['solver_screening_both'] for p in overview['pairs'] if p['configuration']=='broad'),0)
        if publication.RAW.exists():
            raw_bytes=publication.RAW.read_bytes()
            self.assertEqual(sha256(raw_bytes).hexdigest(),publication.RAW_SHA)
            raw=json.loads(raw_bytes)
            publication.equal(full['records'],raw['records'],'raw rows')

    def test_figure_values_hashes_and_inert_svg(self):
        root=publication.ROOT
        manifest=json.loads((root/'web/data/linked-flux/figures.json').read_text(encoding='utf-8'))
        full=json.loads(publication.FULL.read_text(encoding='utf-8'))
        self.assertEqual(manifest['source_sha256'],full['provenance']['raw_report_sha256'])
        self.assertEqual(manifest['script_sha256'],sha256((root/'scripts/plot_linked_study.py').read_bytes()).hexdigest())
        self.assertEqual(manifest['dependency_manifest_sha256'],sha256((root/'requirements-figures.txt').read_bytes()).hexdigest())
        self.assertEqual(len(manifest['figures']),2)
        for figure in manifest['figures']:
            raw=(root/'web'/figure['path']).read_bytes()
            self.assertNotIn(b'\r',raw)
            self.assertEqual(len(raw),figure['bytes']);self.assertEqual(sha256(raw).hexdigest(),figure['sha256'])
            rows={r['variant']:r for r in full['pairs'] if r['configuration']==figure['configuration']}
            self.assertEqual(set(rows),set(figure['values_arcsec']))
            baseline=np.asarray(rows['independent']['east_north_arcsec'])
            for variant,value in figure['values_arcsec'].items():
                np.testing.assert_allclose(value,np.asarray(rows[variant]['east_north_arcsec'])-baseline,rtol=1e-12,atol=1e-12)
            for item in ET.fromstring(raw).iter():
                self.assertNotIn(item.tag.rsplit('}',1)[-1],('script','foreignObject','image'))
                for key,value in item.attrib.items():
                    if key.rsplit('}',1)[-1]=='href':self.assertTrue(value.startswith('#'))
                    self.assertFalse(key.lower().startswith('on'))


if __name__=='__main__':unittest.main()

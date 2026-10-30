import unittest

import numpy as np
from astropy import units as u

from scripts.linked_epoch_model import EpochProblem, EpochFitError, fit_epoch, audit_final_modes
from scripts.linked_flux_profile import profile_shared_amplitude


UNIT=u.MJy/u.sr
XY=np.array([(x,y) for y in range(-3,4) for x in range(-3,4)],float)


def renderer(offset=(0.,0.), fail_above=None):
    def render(p):
        if fail_above is not None and p[0]>fail_above:raise ValueError('synthetic renderer domain')
        d=XY-(p+offset)
        p0=np.exp(-np.sum(d*d,axis=1)/1.4)
        return p0/p0.sum()*(UNIT/u.Jy)
    return render


def samples(position=(.23,-.31), amplitudes=(8.,12.,10.,6.), *, noise=False, outlier=False):
    rng=np.random.default_rng(81); out=[]
    for i,amp in enumerate(amplitudes):
        t=renderer((i*.04,-i*.03)); noise_level=.008*(1+i*.2)*(1+np.abs(XY[:,0])*.1)
        nuisance=np.column_stack((np.ones(len(XY)),XY[:,0],XY[:,1]))
        data=amp*t(np.asarray(position)).value+nuisance@np.array([.2,.004,-.003])
        if noise:data=data+rng.normal(size=len(XY))*noise_level
        if outlier and i==0:data=data.copy();data[0]+=1.
        out.append({'data':data,'error':noise_level,'nuisance':nuisance,'renderer':t,
                    'coefficient':amp/10,'coefficient_provenance':'synthetic ratio',
                    'wavelength':(4.5+.2*i)*u.um})
    return out


def mode_samples(frames,mode):
    return [{k:v for k,v in f.items() if mode=='shared_tilt' or k!='wavelength'} for f in frames]


class LinkedEpochModelTests(unittest.TestCase):
    def test_profile_matches_existing_shared_and_full_design(self):
        frames=mode_samples(samples(noise=True),'shared'); position=np.array([.1,-.2])
        problem=EpochProblem(frames,data_unit=UNIT,mode='shared')
        out=problem.profile(position)
        ref=[]
        for f in frames:
            ref.append({'data':f['data'], 'error':f['error'], 'error_unit':str(UNIT),
                        'template':f['renderer'](position).value,'nuisance':f['nuisance'],
                        'coefficient':f['coefficient'],'coefficient_provenance':f['coefficient_provenance'],
                        'data_unit':str(UNIT),'amplitude_unit':'Jy','template_unit':str(UNIT/u.Jy),
                        'nuisance_unit':'1','coefficient_unit':'1'})
        old=profile_shared_amplitude(ref)
        self.assertAlmostEqual(out['flux_parameters_jy'][0],old.amplitude,places=11)
        self.assertAlmostEqual(out['flux_covariance_jy2'][0,0],old.amplitude_variance,places=11)
        for residual,existing in zip(out['residuals'],old.residuals):np.testing.assert_allclose(residual,existing,atol=1e-13)
        self.check_full_design(problem,position,out)

    def check_full_design(self,problem,position,out):
        frames=problem.frames;k=problem.k;n=sum(len(f['data']) for f in frames)
        p=k+sum(f['nuisance'].shape[1] for f in frames)
        X=np.zeros((n,p)); y=np.empty(n); row=0;col=k
        for f in frames:
            m=len(f['data']);q=f['nuisance'].shape[1]
            X[row:row+m,:k]=f['renderer'](position).value[:,None]*f['basis'][None,:]/f['error'][:,None]
            X[row:row+m,col:col+q]=f['nuisance']/f['error'][:,None]
            y[row:row+m]=f['data']/f['error'];row+=m;col+=q
        beta=np.linalg.solve(X.T@X,X.T@y); cov=np.linalg.inv(X.T@X)
        np.testing.assert_allclose(out['flux_parameters_jy'],beta[:k],rtol=2e-11,atol=1e-11)
        np.testing.assert_allclose(out['flux_covariance_jy2'],cov[:k,:k],rtol=2e-11,atol=1e-11)
        bases=np.stack([f['basis'] for f in frames])
        np.testing.assert_allclose(out['per_frame_flux_covariance_jy2'],bases@cov[:k,:k]@bases.T,rtol=2e-11,atol=1e-11)
        np.testing.assert_allclose(out['weighted_residual'],y-X@beta,atol=2e-12)

    def test_shared_tilt_and_independent_full_matrix(self):
        frames=samples(noise=True)
        for mode in ('shared_tilt','independent'):
            kwargs={'tilt_center':4.8*u.um,'tilt_scale':.3*u.um} if mode=='shared_tilt' else {}
            problem=EpochProblem(mode_samples(frames,mode),data_unit=UNIT,mode=mode,**kwargs)
            out=problem.profile(np.array([.12,-.14]))
            self.check_full_design(problem,np.array([.12,-.14]),out)

    def test_noiseless_position_normalization_and_observed_curvature(self):
        for mode in ('independent','shared'):
            with self.subTest(mode=mode):
                frames=mode_samples(samples(),mode)
                out=fit_epoch(frames,[0.,0.],data_unit=UNIT,mode=mode,observed_hessian=True)
                np.testing.assert_allclose(out['position'],[.23,-.31],atol=1e-7)
                self.assertEqual(len(out['start_reports']),7)
                self.assertEqual(out['position_rank'],2)
                self.assertFalse(out['at_boundary'])
                self.assertTrue(out['profile_hessian']['supported'])
                self.assertLess(out['chi2_raw'],1e-16)
                self.assertEqual(out['dof'],4*49-12-(4 if mode=='independent' else 1)-2)
                self.assertTrue(np.all(np.linalg.eigvalsh(out['position_covariance_px2'])>0))
        # This discrete, position-normalized renderer has a varying unnormalized
        # sum, so the derivative must recompute the complete normalization.
        raw0=np.exp(-np.sum((XY-np.array([.23,-.31]))**2,axis=1)/1.4).sum()
        raw1=np.exp(-np.sum((XY-np.array([.43,-.31]))**2,axis=1)/1.4).sum()
        self.assertGreater(abs(raw0-raw1),1e-5)

    def test_irls_uses_raw_errors_and_rebuilds_projection(self):
        frames=mode_samples(samples(noise=True,outlier=True),'shared')
        fit=fit_epoch(frames,[0,0],data_unit=UNIT,mode='shared')
        initial=[r for r in fit['start_reports'] if r['stage']=='initial' and r['success']]
        best=min(initial,key=lambda r:r['chi2'])
        p=EpochProblem(frames,data_unit=UNIT,mode='shared')
        first=p.profile(best['position'])
        w1=[np.minimum(1.,2.5/np.maximum(abs(r/f['error']),1e-300)) for r,f in zip(first['residuals'],p.frames)]
        p.set_weights(w1)
        first_fit=next(r for r in fit['start_reports'] if r['stage']=='irls_1')
        second=p.profile(first_fit['position'])
        w2=[np.minimum(1.,2.5/np.maximum(abs(r/f['error']),1e-300)) for r,f in zip(second['residuals'],p.frames)]
        for actual,expected in zip(fit['weights'],w2):np.testing.assert_allclose(actual,expected,rtol=1e-13)
        self.assertLess(fit['weights'][0][0],.03)
        self.assertLess(fit['chi2_weighted'],fit['chi2_raw'])

    def test_negative_flux_permutation_and_scale(self):
        frames=mode_samples(samples(amplitudes=(-8.,-12.,-10.,-6.)),'shared')
        # Keep positive ratios so the shared amplitude itself is negative.
        for f in frames:f['coefficient']=abs(f['coefficient'])
        result=fit_epoch(frames,[0,0],data_unit=UNIT,mode='shared')
        self.assertTrue(np.all(result['negative_frame_flux']))
        self.assertTrue(np.all(result['conditional_frame_snr']<0))
        reversed_fit=fit_epoch(frames[::-1],[0,0],data_unit=UNIT,mode='shared')
        np.testing.assert_allclose(result['position'],reversed_fit['position'],atol=1e-8)
        scaled=[{**f,'data':f['data']*7,'error':f['error']*7} for f in frames]
        bigger=fit_epoch(scaled,[0,0],data_unit=UNIT,mode='shared')
        np.testing.assert_allclose(result['position'],bigger['position'],atol=1e-8)
        np.testing.assert_allclose(bigger['flux_parameters_jy'],result['flux_parameters_jy']*7,rtol=1e-10)
        np.testing.assert_allclose(bigger['flux_covariance_jy2'],result['flux_covariance_jy2']*49,rtol=1e-10)

    def test_failed_start_boundary_and_rank_guards(self):
        frames=mode_samples(samples(),'shared')
        limited=[{**f,'renderer':renderer((i*.04,-i*.03),fail_above=.6)} for i,f in enumerate(frames)]
        fit=fit_epoch(limited,[0,0],data_unit=UNIT,mode='shared')
        self.assertTrue(any(not r['success'] for r in fit['start_reports'][:5]))
        boundary=fit_epoch(mode_samples(samples(position=(3.2,0.)),'shared'),[0,0],data_unit=UNIT,mode='shared',observed_hessian=True)
        self.assertTrue(boundary['at_boundary'])
        self.assertIsNone(boundary['position_covariance_px2'])
        self.assertFalse(boundary['profile_hessian']['supported'])
        # An identifiable amplitude does not imply an identifiable position.
        fixed=[{**f,'renderer':(lambda p, t=f['renderer']:t(np.array([0.,0.])))} for f in frames]
        fixed_fit=fit_epoch(fixed,[0,0],data_unit=UNIT,mode='shared',observed_hessian=True)
        self.assertEqual(fixed_fit['position_rank'],0)
        self.assertIsNone(fixed_fit['position_covariance_px2'])
        self.assertFalse(fixed_fit['profile_hessian']['supported'])
        bad=[{**f,'nuisance':np.column_stack([f['nuisance'],f['nuisance'][:,0]])} for f in frames]
        with self.assertRaisesRegex(ValueError,'rank deficient'):EpochProblem(bad,data_unit=UNIT,mode='shared')
        tilt=samples();
        for f in tilt:f['wavelength']=5*u.um
        p=EpochProblem(tilt,data_unit=UNIT,mode='shared_tilt',tilt_center=5*u.um,tilt_scale=1*u.um)
        with self.assertRaisesRegex(ValueError,'source design'):p.profile([0,0])
        # The projected source is numerical roundoff, not meaningful signal.
        constant=[{**f,'renderer':lambda p:np.ones(49)*(UNIT/u.Jy)} for f in frames]
        p=EpochProblem(constant,data_unit=UNIT,mode='shared')
        with self.assertRaisesRegex(ValueError,'unidentifiable'):p.profile([0,0])
        zero=[{**f,'coefficient':0.} for f in frames]
        with self.assertRaises(EpochFitError) as raised:fit_epoch(zero,[0,0],data_unit=UNIT,mode='shared')
        self.assertEqual(len(raised.exception.start_reports),5)
        self.assertTrue(all(not r['success'] for r in raised.exception.start_reports))

    def test_input_units_and_weights(self):
        frames=mode_samples(samples(),'shared')
        for change in ({'coefficient_provenance':''}, {'error':np.zeros(49)}, {'coefficient':np.nan},
                       {'data':np.full(49,np.nan)}):
            with self.subTest(change=list(change)),self.assertRaises(ValueError):
                EpochProblem([{**frames[0],**change}]+frames[1:],data_unit=UNIT,mode='shared')
        bad=[{**f,'renderer':lambda p: np.ones(49)} for f in frames]
        with self.assertRaisesRegex(ValueError,'Quantity'):EpochProblem(bad,data_unit=UNIT,mode='shared').profile([0,0])
        bad=[{**f,'renderer':lambda p: np.ones(49)*u.Jy} for f in frames]
        with self.assertRaisesRegex(ValueError,'unit mismatch'):EpochProblem(bad,data_unit=UNIT,mode='shared').profile([0,0])
        p=EpochProblem(frames,data_unit=UNIT,mode='shared')
        with self.assertRaises(ValueError):p.set_weights([np.zeros(49)]*4)

    def test_irls_convergence_and_twenty_iteration_failure(self):
        frames=mode_samples(samples(noise=True,outlier=True),'shared')
        fit=fit_epoch(frames,[0,0],data_unit=UNIT,mode='shared',max_irls_iterations=20,final_mode_audit=True)
        self.assertTrue(fit['irls']['converged'])
        self.assertGreaterEqual(fit['irls']['iterations'],2)
        self.assertLess(fit['irls']['iterations'],20)
        calculated=[]
        for residual,frame,weight in zip(fit['residuals'],frames,fit['weights']):
            updated=np.minimum(1.,2.5/np.maximum(np.abs(residual/frame['error']),1e-300))
            calculated.append(np.max(np.abs(updated-weight)))
        self.assertAlmostEqual(max(calculated),fit['irls']['next_weight_max_difference'],places=15)
        self.assertLessEqual(fit['irls']['next_weight_max_difference'],1e-3)
        self.assertLessEqual(fit['irls']['position_max_change'],1e-4)
        self.assertTrue(fit['inference_supported'])
        self.assertEqual(len(fit['final_mode_audit']['starts']),5)
        g=np.random.default_rng(12)
        base=mode_samples(samples(),'shared')
        difficult=[{**s,'data':s['data']+g.standard_t(.8,size=49)*s['error']*4} for s in base]
        not_converged=fit_epoch(difficult,[0,0],data_unit=UNIT,mode='shared',max_irls_iterations=20,
                                weight_tolerance=1e-10,position_tolerance=1e-10,final_mode_audit=True)
        self.assertEqual(not_converged['irls']['iterations'],20)
        self.assertFalse(not_converged['irls']['converged'])
        self.assertFalse(not_converged['inference_supported'])
        self.assertIn('irls_not_converged',not_converged['inference_reasons'])
        self.assertTrue(np.isfinite(not_converged['position']).all())

    def test_final_audit_better_point_and_failed_start(self):
        frames=mode_samples(samples(),'shared')
        limited=[{**f,'renderer':renderer((i*.04,-i*.03),fail_above=.6)} for i,f in enumerate(frames)]
        problem=EpochProblem(limited,data_unit=UNIT,mode='shared')
        point=np.array([-.5,.2]);cost=problem.profile(point)['weighted_residual']
        result=audit_final_modes(problem,np.zeros(2),point)
        self.assertAlmostEqual(result['point_chi2'],cost@cost,places=10)
        self.assertTrue(result['better_than_point'])
        self.assertGreater(result['best_improvement_chi2'],1e-4)
        self.assertTrue(any(not report['success'] for report in result['starts']))
        self.assertTrue(any(report['success'] for report in result['starts']))
        self.assertTrue(np.array_equal(point,[-.5,.2]))

    def test_final_audit_detects_multiple_modes_without_replacing_point(self):
        def periodic(p):
            return renderer()(np.array([.5*np.sin(np.pi*p[0]),p[1]]))
        frames=mode_samples(samples(position=(0.,.2),amplitudes=(8.,12.,10.,6.)),'shared')
        for f in frames:
            f['renderer']=periodic
            f['data']=f['coefficient']*10*periodic(np.array([0.,.2])).value+f['nuisance']@np.array([.2,.004,-.003])
        fit=fit_epoch(frames,[0,0],data_unit=UNIT,mode='shared',max_irls_iterations=20,final_mode_audit=True)
        audit=fit['final_mode_audit']
        self.assertGreaterEqual(audit['near_best_count'],2)
        self.assertFalse(fit['inference_supported'])
        self.assertIn('multiple_near_best_modes',fit['inference_reasons'])
        self.assertAlmostEqual(audit['point_chi2'],fit['chi2_weighted'],places=10)
        self.assertTrue(np.any([np.linalg.norm(m['position']-fit['position'])<1e-6 for m in audit['modes']]))


if __name__=='__main__':unittest.main()

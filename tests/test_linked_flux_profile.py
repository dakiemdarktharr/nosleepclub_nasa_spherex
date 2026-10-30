import copy
import unittest

import numpy as np
from scripts.linked_flux_profile import profile_shared_amplitude


def fixture():
    rng=np.random.default_rng(144)
    frames=[]
    x=np.linspace(-1,1,9)
    for i in range(3):
        t=np.exp(-((x-.1*i)/(.32+.05*i))**2)+.11*x
        n=np.column_stack((np.ones(len(x)),x+.12*t))
        c=[.7,1.3,1.8][i]
        frame={'data':-1.7*c*t+n@np.array([.2+i*.1,-.15])+rng.normal(0,.035,len(x)),
               'template':t,'nuisance':n,'coefficient':c,
               'coefficient_provenance':f'external response version 1 frame {i}',
               'data_unit':'Jy','amplitude_unit':'Jy','template_unit':'1','nuisance_unit':'1','coefficient_unit':'1'}
        if i==1:
            d=.13+.08*(x+1);C=np.diag(d*d)+.0015*np.ones((len(x),len(x)))
            frame.update(covariance=C,covariance_unit='Jy2')
        else:
            frame.update(error=.10+(.02+.01*i)*(x+1),error_unit='Jy')
        frames.append(frame)
    return frames


def independent_joint(frames):
    rows=sum(len(f['data']) for f in frames); cols=1+sum(f['nuisance'].shape[1] for f in frames)
    X=np.zeros((rows,cols));y=np.empty(rows);row=0;col=1
    for f in frames:
        n=len(f['data']); k=f['nuisance'].shape[1]
        local=np.column_stack([f['coefficient']*f['template'],f['nuisance']])
        L=np.linalg.cholesky(f['covariance']) if 'covariance' in f else np.diag(f['error'])
        whitened=np.linalg.solve(L,local)
        X[row:row+n,0]=whitened[:,0];X[row:row+n,col:col+k]=whitened[:,1:]
        y[row:row+n]=np.linalg.solve(L,f['data']);row+=n;col+=k
    return X,y,np.linalg.lstsq(X,y,rcond=None)[0],np.linalg.inv(X.T@X)


class LinkedFluxTests(unittest.TestCase):
    def test_joint_wls_and_profile_orthogonality(self):
        f=fixture(); out=profile_shared_amplitude(f); X,y,b,C=independent_joint(f)
        self.assertAlmostEqual(out.amplitude,b[0],places=12)
        self.assertLess(out.amplitude,0)  # negative flux remains unconstrained
        self.assertAlmostEqual(out.amplitude_variance,C[0,0],places=12)
        self.assertAlmostEqual(out.amplitude_error,np.sqrt(C[0,0]),places=12)
        np.testing.assert_allclose(np.concatenate(out.nuisance),b[1:],rtol=1e-12,atol=1e-12)
        r=np.concatenate(out.whitened_residuals)
        np.testing.assert_allclose(r,y-X@b,atol=1e-12)
        np.testing.assert_allclose(X.T@r,0,atol=1e-12)
        self.assertEqual(out.rank,7);self.assertEqual(out.nuisance_ranks,(2,2,2))
        self.assertEqual(out.dof,20);self.assertAlmostEqual(out.chi2,r@r,places=12)
        self.assertAlmostEqual(out.profile_information,1/C[0,0],places=10)
        self.assertEqual(out.coefficient_provenance[1],f[1]['coefficient_provenance'])

    def test_permutation_and_equivalent_rescaling(self):
        f=fixture();a=profile_shared_amplitude(f);b=profile_shared_amplitude(f[::-1])
        self.assertAlmostEqual(a.amplitude,b.amplitude,places=12)
        self.assertAlmostEqual(a.amplitude_error,b.amplitude_error,places=12)
        for x,y in zip(a.residuals,b.residuals[::-1]):np.testing.assert_allclose(x,y,atol=1e-12)
        scaled=copy.deepcopy(f)
        for x in scaled:
            x['template']=x['template']*1e8;x['coefficient']*=1e-8
            x['nuisance'][:,0]*=1e-6;x['nuisance'][:,1]*=1e5
        c=profile_shared_amplitude(scaled)
        self.assertAlmostEqual(a.amplitude,c.amplitude,places=12)
        self.assertAlmostEqual(a.amplitude_error,c.amplitude_error,places=12)
        for x,y in zip(a.residuals,c.residuals):np.testing.assert_allclose(x,y,atol=1e-12)

    def test_diagonal_and_full_covariance_equivalence(self):
        f=fixture(); a=profile_shared_amplitude(f);g=copy.deepcopy(f)
        for x in g:
            if 'error' in x:
                e=x.pop('error');x.pop('error_unit');x['covariance']=np.diag(e**2);x['covariance_unit']='Jy2'
        b=profile_shared_amplitude(g)
        self.assertAlmostEqual(a.amplitude,b.amplitude,places=12)
        self.assertAlmostEqual(a.amplitude_error,b.amplitude_error,places=12)
        diag=copy.deepcopy(g);diag[1]['covariance']=np.diag(np.diag(diag[1]['covariance']))
        self.assertGreater(abs(profile_shared_amplitude(diag).amplitude_error-a.amplitude_error),1e-7)

    def test_data_error_scale_and_covariance_symmetry_at_small_and_large_scales(self):
        f=fixture(); original=profile_shared_amplitude(f)
        for scale in (1e-7,1e7):
            g=copy.deepcopy(f)
            for x in g:
                x['data']*=scale
                if 'error' in x:x['error']*=scale
                else:x['covariance']*=scale**2
            out=profile_shared_amplitude(g)
            self.assertAlmostEqual(out.amplitude/scale,original.amplitude,places=11)
            self.assertAlmostEqual(out.amplitude_error/scale,original.amplitude_error,places=11)
            self.assertAlmostEqual(out.chi2,original.chi2,places=11)
            # A 10% asymmetric off-diagonal must fail regardless of units.
            g[1]['covariance'][0,1]+=g[1]['covariance'][0,0]*.1
            with self.assertRaises(ValueError):profile_shared_amplitude(g)

    def test_rank_guards_near_blend_and_dof(self):
        f=fixture();singular=copy.deepcopy(f);singular[0]['nuisance'][:,1]=singular[0]['nuisance'][:,0]
        with self.assertRaises(ValueError):profile_shared_amplitude(singular)
        blend=copy.deepcopy(f)
        for x in blend:x['template']=x['nuisance'][:,0]+1e-12*x['template']
        with self.assertRaises(ValueError):profile_shared_amplitude(blend)
        zero=copy.deepcopy(f)
        for x in zero:x['coefficient']=0
        with self.assertRaises(ValueError):profile_shared_amplitude(zero)
        one=copy.deepcopy(f[0]);one['data']=one['data'][:3];one['template']=one['template'][:3];one['nuisance']=one['nuisance'][:3];one['error']=one['error'][:3]
        with self.assertRaises(ValueError):profile_shared_amplitude([one])

    def test_invalid_data_units_provenance_and_covariance(self):
        for mutate in ('unit','template_unit','coef_unit','provenance','nan','error','shape','both','unknown','covunit','asym','nonspd','coefficient'):
            f=fixture()
            if mutate=='unit':f[0]['data_unit']='mJy'
            if mutate=='template_unit':f[0]['template_unit']='Jy'
            if mutate=='coef_unit':f[0]['coefficient_unit']='s'
            if mutate=='provenance':f[0]['coefficient_provenance']=' '
            if mutate=='nan':f[0]['data'][0]=np.nan
            if mutate=='error':f[0]['error'][0]=0
            if mutate=='shape':f[0]['template']=f[0]['template'][:-1]
            if mutate=='both':f[0]['covariance']=np.eye(9);f[0]['covariance_unit']='Jy2'
            if mutate=='unknown':f[0]['unknown']=1
            if mutate=='covunit':f[1]['covariance_unit']='Jy'
            if mutate=='asym':f[1]['covariance'][0,1]+=.005
            if mutate=='nonspd':f[1]['covariance'][0,0]=-1
            if mutate=='coefficient':f[0]['coefficient']=np.nan
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):profile_shared_amplitude(f)

    def test_no_nuisance_and_zero_response_frame(self):
        f=fixture();f[0]['nuisance']=np.empty((9,0));f[0]['coefficient']=0
        out=profile_shared_amplitude(f); X,y,b,C=independent_joint(f)
        self.assertEqual(out.nuisance_ranks,(0,2,2));self.assertEqual(len(out.nuisance[0]),0)
        self.assertAlmostEqual(out.amplitude,b[0],places=12)
        self.assertAlmostEqual(out.amplitude_variance,C[0,0],places=12)

    def test_integrated_flux_unit_and_surface_brightness_template(self):
        f=fixture();original=profile_shared_amplitude(f)
        for x in f:
            x['data_unit']='MJy / sr';x['amplitude_unit']='Jy';x['template_unit']='MJy / (Jy sr)'
            if 'error' in x:x['error_unit']='MJy / sr'
            else:x['covariance_unit']='MJy2 / sr2'
        out=profile_shared_amplitude(f)
        self.assertEqual(out.amplitude_unit,'Jy')
        self.assertEqual(out.data_unit,'MJy / sr')
        self.assertAlmostEqual(out.amplitude,original.amplitude,places=12)
        f[1]['template_unit']='1 / sr'
        with self.assertRaises(ValueError):profile_shared_amplitude(f)

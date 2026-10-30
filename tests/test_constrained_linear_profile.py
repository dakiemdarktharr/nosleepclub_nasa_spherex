import itertools
import unittest

import numpy as np
from astropy import units as u
from scipy.optimize import lsq_linear

from scripts.constrained_linear_profile import profile_linear


def enumerate_active_sets(y,e,free,neighbors,weights):
    """Independent exhaustive reference for small numbers of bounds."""
    w=np.sqrt(weights)/e
    best=None
    for selected in itertools.product((False,True),repeat=neighbors.shape[1]):
        selected=np.asarray(selected,bool)
        X=np.column_stack((free,neighbors[:,selected]))
        if X.shape[1]:beta=np.linalg.lstsq(X*w[:,None],y*w,rcond=None)[0]
        else:beta=np.empty(0)
        if np.any(beta[free.shape[1]:]<-1e-10):continue
        full=np.zeros(neighbors.shape[1]);full[selected]=beta[free.shape[1]:]
        resid=(y-free@beta[:free.shape[1]]-neighbors@full)*w
        candidate=(float(resid@resid),beta[:free.shape[1]],full)
        if best is None or candidate[0]<best[0]:best=candidate
    return best


def synthetic():
    rng=np.random.default_rng(181)
    free=rng.normal(size=(24,2));neighbors=rng.normal(size=(24,3))
    error=rng.uniform(.3,1.4,24);weights=rng.uniform(.2,1.,24)
    y=free@np.array([-1.7,.5])+neighbors@np.array([1.2,0.,.6])+rng.normal(0,.7,24)
    return y,error,free,neighbors,weights


class ConstrainedProfileTests(unittest.TestCase):
    def test_quantities_cannot_silently_lose_units(self):
        values=synthetic()
        for index in range(5):
            bad=list(values);bad[index]=bad[index]*u.Jy
            with self.subTest(input=index),self.assertRaisesRegex(ValueError,'caller-declared units'):
                profile_linear(*bad)

    def test_enumeration_and_full_bvls_agree(self):
        y,e,F,N,w=synthetic();result=profile_linear(y,e,F,N,w)
        chi,free,neighbors=enumerate_active_sets(y,e,F,N,w)
        np.testing.assert_allclose(result['free_coefficients'],free,rtol=1e-11,atol=1e-11)
        np.testing.assert_allclose(result['nonnegative_coefficients'],neighbors,rtol=1e-11,atol=1e-11)
        self.assertAlmostEqual(result['chi2'],chi,places=11)
        X=np.column_stack((F,N));white=np.sqrt(w)/e
        reference=lsq_linear(X*white[:,None],y*white,bounds=(np.r_[-np.inf*np.ones(2),np.zeros(3)],np.full(5,np.inf)),method='bvls',tol=1e-12)
        self.assertTrue(reference.success)
        np.testing.assert_allclose(np.r_[result['free_coefficients'],result['nonnegative_coefficients']],reference.x,atol=1e-10)
        np.testing.assert_allclose(result['model'],X@reference.x,atol=1e-10)
        np.testing.assert_allclose(result['weighted_residual'],(y-result['model'])*white,atol=1e-14)
        self.assertLess(result['free_coefficients'][0],0.)

    def test_random_cases_against_active_set_enumeration(self):
        rng=np.random.default_rng(1520)
        for trial in range(24):
            n=12;p=trial%3;q=1+trial%3
            F=rng.normal(size=(n,p));N=rng.normal(size=(n,q))
            error=rng.uniform(.1,2,n);weights=rng.uniform(.05,1,n);y=rng.normal(size=n)
            result=profile_linear(y,error,F,N,weights)
            chi,free,neighbors=enumerate_active_sets(y,error,F,N,weights)
            with self.subTest(trial=trial):
                self.assertAlmostEqual(result['chi2'],chi,places=10)
                np.testing.assert_allclose(result['free_coefficients'],free,atol=1e-10)
                np.testing.assert_allclose(result['nonnegative_coefficients'],neighbors,atol=1e-10)

    def test_kkt_signs_stationarity_and_active_bound(self):
        y,e,F,N,w=synthetic();out=profile_linear(y,e,F,N,w)
        X=np.column_stack((F,N))*(np.sqrt(w)/e)[:,None]
        norms=np.linalg.norm(X,axis=0)
        normalized=(X/norms).T@out['weighted_residual']/np.max(np.abs(y*np.sqrt(w)/e))
        np.testing.assert_allclose(out['scaled_gradient_free'],normalized[:F.shape[1]],atol=1e-15)
        np.testing.assert_allclose(out['scaled_gradient_nonnegative'],normalized[F.shape[1]:],atol=1e-15)
        active=out['active_mask'];self.assertTrue(active.any());self.assertTrue((~active).any())
        self.assertTrue(np.all(out['nonnegative_coefficients'][active]==0))
        self.assertTrue(np.all(normalized[F.shape[1]:][active]<=1e-8))
        self.assertLess(np.max(np.abs(normalized[F.shape[1]:][~active])),1e-8)
        self.assertLess(out['scaled_complementarity_violation'],1e-8)

    def test_positive_column_rescaling_extreme_units_and_permutation(self):
        y,e,F,N,w=synthetic();base=profile_linear(y,e,F,N,w)
        fs=np.array([1e-180,1e120]);ns=np.array([1e-150,1e80,1e-12])
        out=profile_linear(y,e,F*fs,N*ns,w)
        np.testing.assert_allclose(out['free_coefficients']*fs,base['free_coefficients'],rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(out['nonnegative_coefficients']*ns,base['nonnegative_coefficients'],rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(out['residual'],base['residual'],atol=1e-12)
        permutation=np.array([2,0,1]);reordered=profile_linear(y,e,F,N[:,permutation],w)
        np.testing.assert_allclose(reordered['nonnegative_coefficients'],base['nonnegative_coefficients'][permutation],atol=1e-12)
        np.testing.assert_allclose(reordered['residual'],base['residual'],atol=1e-12)

    def test_empty_blocks_and_all_boundary(self):
        y=np.array([-1.,-2.,-3.,-4.]);e=np.ones(4)
        N=np.eye(4);empty=np.empty((4,0))
        out=profile_linear(y,e,empty,N)
        self.assertTrue(out['active_mask'].all());np.testing.assert_array_equal(out['nonnegative_coefficients'],0.)
        self.assertAlmostEqual(out['chi2'],30.)
        free=profile_linear(y,e,np.ones((4,1)),empty)
        self.assertAlmostEqual(free['free_coefficients'][0],-2.5)
        both_empty=profile_linear(y,e,empty,empty)
        self.assertEqual(both_empty['rank'],0);np.testing.assert_array_equal(both_empty['model'],0.)
        zero=profile_linear(np.zeros(4),e,empty,N)
        self.assertEqual(zero['chi2'],0.);self.assertTrue(zero['active_mask'].all())

    def test_reject_rank_loss_near_blend_and_bad_inputs(self):
        y,e,F,N,w=synthetic()
        with self.assertRaisesRegex(ValueError,'rank deficient'):profile_linear(y,e,F,np.column_stack((N,F[:,0])),w)
        almost=F[:,0]+1e-12*N[:,0]
        with self.assertRaisesRegex(ValueError,'rank deficient'):profile_linear(y,e,F,almost[:,None],w)
        cases=[(y,np.zeros_like(e),F,N,w),(y,e,F,np.zeros_like(N),w),
               (y,e,F[:-1],N,w),(y,e,F,N,np.zeros_like(w)),
               (y,e,F,N,np.full_like(w,1.1)),(np.full_like(y,np.nan),e,F,N,w),
               (y,e,F,N,np.full_like(w,np.nan)),(y,e,F,np.full_like(N,np.inf),w),
               (y,e,np.zeros((len(y),25)),N,w)]
        for index,case in enumerate(cases):
            with self.subTest(case=index),self.assertRaises(ValueError):profile_linear(*case)
        with self.assertRaisesRegex(ValueError,'underflow'):
            profile_linear(np.ones(2)*1e-300,np.ones(2)*1e100,np.empty((2,0)),np.empty((2,0)))


if __name__=='__main__':unittest.main()

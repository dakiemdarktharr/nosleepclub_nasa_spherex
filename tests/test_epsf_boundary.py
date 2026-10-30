import unittest

import numpy as np
from scipy.ndimage import spline_filter

from scripts import diagnose_epsf_boundary as boundary
from scripts import profile_uncertainty as profile


class BoundaryDiagnosticTests(unittest.TestCase):
    def test_quadratic_hessian_and_original_formula(self):
        matrix=np.array([[8.,-2.],[-2.,5.]])
        factor=np.linalg.cholesky(matrix).T
        residual=lambda p:factor@np.asarray(p)+np.array([.3,-.7])
        x=np.array([.4,-.2])
        for h in [.00025,.002,.016]:
            scalar=boundary.hessian_objective(lambda p:boundary.objective(residual,p),x,h)
            np.testing.assert_allclose(scalar,matrix,atol=1e-7)
            np.testing.assert_allclose(scalar,profile.hessian(residual,x,h),atol=1e-9)

    def test_nonzero_edge_jumps_and_padding_is_continuous(self):
        raw=np.ones((5,5))
        table=np.zeros(1,dtype=[('EPSF',float,(5,5))]);table['EPSF'][0]=raw
        sample={'native_center':np.zeros(2),'jacobian':np.eye(2),'anchor':np.zeros(2),
                'x':np.array([2.,0.,1.,-1.]),'y':np.zeros(4),'epsf':spline_filter(raw/25,order=3),
                'zone':0,'frame':{'epsf_oversampling':1.,'epsf_table':table,'record':{'obs_id':'control'}},
                'data':np.array([2.,1.,0.,0.]),'error':np.ones(4),'q':np.empty((4,0))}
        left=np.array([-1e-8,0.]);right=np.array([1e-8,0.])
        original=[boundary.target_psf(sample,p)[0] for p in (left,right)]
        padded=[boundary.target_psf(sample,p,True)[0] for p in (left,right)]
        self.assertGreater(abs(original[1]-original[0]),.039)
        self.assertLess(abs(padded[1]-padded[0]),1e-8)
        fun=lambda p:boundary.objective(lambda x:boundary.residual([sample],x),p)
        self.assertGreater(abs(fun(right)-fun(left)),.1)
        hits=boundary.crossings([sample],np.zeros(2),np.array([1.,0.]))
        self.assertTrue(any(h['pixel_xy_native']==[2.,0.] and abs(h['offset_sky_px'])<1e-12 for h in hits))


if __name__=='__main__':unittest.main()

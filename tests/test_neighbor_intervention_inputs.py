import copy
import unittest

import astropy.units as u
from astropy.io import fits
import numpy as np

from scripts import neighbor_intervention_inputs as adapter
from scripts import native_gain_binding as active
from scripts import motion_analysis as motion
from scripts.constrained_linear_profile import profile_linear


def table_fixture():
    table=np.zeros(4,dtype=[('XCENTER','f8'),('YCENTER','f8'),('EPSF','f8',(33,33))])
    yy,xx=np.indices((33,33))
    for index,(x,y) in enumerate(( (100,100),(200,100),(100,200),(200,200) )):
        table[index]['XCENTER']=x;table[index]['YCENTER']=y
        table[index]['EPSF']=np.exp(-((xx-16)**2+(yy-16)**2)/(2*(2.8+index*.2)**2))*(index+1)
    return table


def prepared_fixture():
    primary=fits.Header();primary['VERSION']='6.4+psffix1'
    header=fits.Header()
    fields={'DETECTOR':6,'DETCOORD':'sky','WCSNAMEA':'0-based active pixel coordinates',
        'WCSAXESA':2,'CTYPE1A':'LINEAR','CTYPE2A':'LINEAR','CUNIT1A':'pixel','CUNIT2A':'pixel',
        'CRPIX1A':-99.,'CRPIX2A':-99.,'CRVAL1A':0.,'CRVAL2A':0.,'CDELT1A':1.,'CDELT2A':1.,
        'NAXIS1':64,'NAXIS2':64}
    for key,value in fields.items():header['HIERARCH '+key if len(key)>8 else key]=value
    header.add_history('[CALIB] abs_gain_matrix '+active.UUID)
    frame={'data':np.zeros((64,64)),'offset':np.zeros(2),'wcs':motion.WCS.deepcopy(),
        'record':{'collection':'spherex_qr2','cutout_url':'https://synthetic.invalid/1','sha256':'synthetic'},
        'image_header':header,'primary_header':primary,'epsf_oversampling':5,
        'epsf_table':table_fixture(),'epsf_provenance':'synthetic PSF grid, not telescope truth'}
    mask=np.zeros((64,64),bool);mask[24:40,24:40]=True;y,x=np.nonzero(mask)
    b=np.column_stack((np.ones(len(x)),(x-31.5)/6,(y-31.5)/6))
    sample={'frame':frame,'x':x,'y':y,'background':b,'neighbour_ids':['known-1'],
            'neighbours':[('known-1',np.array([34.7,31.2]))]}
    return [{'obs_id':'synthetic','data':np.zeros(len(x)),'error':np.full(len(x),.01),
             'data_unit':'MJy/sr','sample':sample,'selection_mask':mask,
             'renderer_provenance':'synthetic geometry','subtraction_provenance':'synthetic background'}]


class SemanticInputTests(unittest.TestCase):
    def test_spatial_interpolation_has_hand_computed_weights_and_no_recentering(self):
        table=table_fixture();raw,meta=adapter.select_epsf(table,[125,175],'bilinear')
        weights=np.array([.1875,.0625,.5625,.1875])
        expected=sum(w*row['EPSF']/row['EPSF'].sum() for w,row in zip(weights,table))
        np.testing.assert_allclose(raw,expected,rtol=1e-14,atol=1e-17)
        by_index=dict(zip(meta['table_indices'],meta['table_weights']))
        np.testing.assert_allclose([by_index[i] for i in range(4)],weights)
        self.assertEqual(meta['clamped_axes'],[False,False]);self.assertAlmostEqual(raw.sum(),1.)
        nearest,description=adapter.select_epsf(table,[125,175],'nearest')
        self.assertEqual(description['table_indices'],[2])
        np.testing.assert_allclose(nearest,table['EPSF'][2]/table['EPSF'][2].sum())

    def test_edge_clamp_is_explicit_and_bad_grid_refused(self):
        table=table_fixture();raw,meta=adapter.select_epsf(table,[20,175],'bilinear')
        self.assertEqual(meta['clamped_axes'],[True,False]);self.assertEqual(set(meta['table_indices']),{0,2})
        for point in ([2040,100],[-1,100],[np.nan,100]):
            with self.assertRaises(ValueError):adapter.select_epsf(table,point,'nearest')
        for bad in (table[:-1],np.r_[table,table[:1]]):
            with self.assertRaisesRegex(ValueError,'grid'):adapter.select_epsf(bad,[125,175],'bilinear')
        bad=table.copy();bad['EPSF'][0]*=-1
        with self.assertRaises(ValueError):adapter.select_epsf(bad,[100,100],'nearest')

    def test_semantic_jy_amplitudes_recover_signed_target_and_neighbor(self):
        original=prepared_fixture();items=adapter.prepare_semantic(original,[31.5,31.5],epsf_kind='bilinear')
        item=items[0];truth=np.array([31.8,31.2]);target=item['renderer'](truth)
        self.assertEqual(target.unit,u.MJy/u.sr/u.Jy)
        source=target.to_value(u.MJy/u.sr/u.Jy)
        B=item['background_design'];N=item['neighbor_design']
        y=-.0003*source+N[:,0]*.0002+B@np.array([-.03,.02,-.01])
        result=profile_linear(y,item['error'],np.column_stack((source,B)),N)
        np.testing.assert_allclose(result['free_coefficients'],[-.0003,-.03,.02,-.01],rtol=1e-10,atol=1e-12)
        np.testing.assert_allclose(result['nonnegative_coefficients'],[.0002],rtol=1e-10,atol=1e-12)
        self.assertEqual(item['neighbor_ids'],['known-1'])
        self.assertEqual(item['metadata']['neighbors'][0]['id'],'known-1')
        np.testing.assert_array_equal(item['data'],original[0]['data'])
        np.testing.assert_array_equal(item['error'],original[0]['error'])
        self.assertEqual(set(adapter.model_samples(items)[0]),{'obs_id','data','error','background_design','neighbor_design','neighbor_ids','neighbor_unit','renderer'})

    def test_quadratic_and_spatial_variants_preserve_pixel_and_neighbor_selection(self):
        original=prepared_fixture();baseline=adapter.prepare_semantic(original,[31.5,31.5])[0]
        extended=adapter.prepare_semantic(original,[31.5,31.5],background_order=2,epsf_kind='bilinear')[0]
        self.assertEqual(extended['background_design'].shape[1],6)
        for key in ('x','y'):self.assertEqual(baseline['metadata'][key],extended['metadata'][key])
        self.assertEqual(baseline['neighbor_ids'],extended['neighbor_ids'])
        self.assertFalse(np.shares_memory(baseline['data'],original[0]['data']))
        b=baseline['background_design'];np.testing.assert_allclose(extended['background_design'][:,3:],np.column_stack((b[:,1]**2,b[:,1]*b[:,2],b[:,2]**2)))

    def test_empty_neighbor_and_input_identity_guards(self):
        original=prepared_fixture();original[0]['sample']['neighbour_ids']=[]
        result=adapter.prepare_semantic(original,[31.5,31.5])[0]
        self.assertEqual(result['neighbor_design'].shape,(256,0));self.assertEqual(result['neighbor_ids'],[])
        for mutate in ('ids','missing','mask','units','order','duplicate'):
            bad=prepared_fixture()
            if mutate=='ids':bad[0]['sample']['neighbour_ids']=['known-1','known-1']
            if mutate=='missing':bad[0]['sample']['neighbour_ids']=['absent']
            if mutate=='mask':bad[0]['selection_mask'][24,24]=False
            if mutate=='units':bad[0]['data_unit']='uJy'
            if mutate=='order':bad[0]['sample']['x']=bad[0]['sample']['x'][::-1]
            if mutate=='duplicate':bad.append(copy.deepcopy(bad[0]))
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):adapter.prepare_semantic(bad,[31.5,31.5])
        with self.assertRaises(ValueError):adapter.prepare_semantic(prepared_fixture(),[31.5,31.5],background_order=True)


if __name__=='__main__':unittest.main()

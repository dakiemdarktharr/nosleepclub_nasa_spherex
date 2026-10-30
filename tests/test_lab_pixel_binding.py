import unittest

from astropy.io import fits
import numpy as np

from scripts import lab_pixel_binding as binding
from scripts import lab_spectral_response as lab


class PixelBindingTests(unittest.TestCase):
    def test_hdu_specific_flip_is_not_package_wide(self):
        x=np.array([0,1,3]);y=np.array([0,2,1]);shape=(3,4)
        sx,sy=binding.active_to_map_indices(x,y,shape,'sky')
        dx,dy=binding.active_to_map_indices(x,y,shape,'DEVICE')
        np.testing.assert_array_equal(sx,[0,1,3]);np.testing.assert_array_equal(sy,y)
        np.testing.assert_array_equal(dx,[3,2,0]);np.testing.assert_array_equal(dy,y)
        array=np.arange(12).reshape(shape)
        sky=binding.CalibrationMap(array,'sky','channel',(),None,None)
        device=binding.CalibrationMap(array,'DEVICE','parameter',(),'um','documentation')
        np.testing.assert_array_equal(sky.values(x,y),[0,9,7])
        np.testing.assert_array_equal(device.values(x,y),[3,10,4])

    def test_invalid_and_ambiguous_coordinates_refused(self):
        for x,y in (([.1],[1]),([-1],[1]),([4],[1]),([0],[3]),([np.nan],[1]),([True],[1])):
            with self.assertRaises(ValueError):binding.active_to_map_indices(x,y,(3,4),'sky')
        with self.assertRaises(ValueError):binding.active_to_map_indices([0],[1],(3,4),'unknown')
        with self.assertRaises(ValueError):binding.active_to_map_indices([0],[1],(3,4),'sky',detector=3)
        h=fits.Header();h.append(('DETCOORD','sky'));h.append(('DETCOORD','DEVICE'))
        with self.assertRaises(ValueError):binding.unique(h,'DETCOORD')

    @unittest.skipUnless(lab.ARCHIVE.exists(),'ignored R7 laboratory archive not cached')
    def test_actual_mixed_orientation_and_map_identity(self):
        with lab.LabArchive() as archive:
            maps=binding.read_maps(archive)
            self.assertEqual(maps['channel'].orientation,'sky')
            self.assertEqual(maps['center'].orientation,'DEVICE')
            self.assertEqual(maps['width'].orientation,'DEVICE')
            # Coordinates selected geometrically, not by an observed residual.
            x,y=900,1000
            result=binding.bind_pixel(maps,x,y)
            self.assertEqual(result['channel'],int(maps['channel'].array[y,x]))
            self.assertEqual(result['center_um'],float(maps['center'].array[y,2039-x]))
            self.assertEqual(result['width_um'],float(maps['width'].array[y,2039-x]))
            self.assertEqual(result['parameter_map_xy'],[1139,1000])
            self.assertEqual(len(archive.used),3)


if __name__ == '__main__':
    unittest.main()

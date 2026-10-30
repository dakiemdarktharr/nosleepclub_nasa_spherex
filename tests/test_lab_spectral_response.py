import unittest

import numpy as np

from scripts import lab_spectral_response as lab


class LabSpectralResponseTests(unittest.TestCase):
    def test_curve_retains_signed_measurements_and_line_endings(self):
        wave, response = lab.parse_curve(b'Wavelength_um,NormTransmission\r\r\n4.4,-0.001\r\r\n4.5,1\r\r\n4.6,0\r\r\n')
        np.testing.assert_array_equal(wave, [4.4,4.5,4.6])
        np.testing.assert_array_equal(response, [-.001,1,0])
        for raw in (b'Wavelength,NormTransmission\n1,1\n2,1\n',
                    b'Wavelength_um,NormTransmission\n1,1\n1,1\n',
                    b'Wavelength_um,NormTransmission\n1,nan\n2,1\n',
                    b'Wavelength_um,NormTransmission\n1,-1\n2,-1\n',
                    b'Wavelength_um,NormTransmission\n1,1,3\n2,1\n'):
            with self.assertRaises(ValueError): lab.parse_curve(raw)

    def test_summary_requires_exact_channel_identity(self):
        header = b'SpecCh,BandCenter_um,BandWidth_um,BandCenter_Allpix_um,BandWidth_Allpix_um\n'
        raw = header + b'1,4.4,.03,4.4,.04\n2,4.5,.03,4.5,.04\n'
        self.assertEqual(lab.parse_summary(raw, 2).shape, (2,5))
        with self.assertRaises(ValueError): lab.parse_summary(raw, 3)
        with self.assertRaises(ValueError): lab.parse_summary(raw.replace(b'2,4.5', b'1,4.5'), 2)
        with self.assertRaises(ValueError): lab.parse_summary(raw.replace(b'.03', b'-.03'), 2)

    @unittest.skipUnless(lab.ARCHIVE.exists(), 'ignored laboratory tar not cached')
    def test_pinned_real_archive_and_selected_files(self):
        with lab.LabArchive() as archive:
            _, summary = archive.summary()
            self.assertEqual(summary.shape, (17,5))
            for kind in ('Cent','Allpix'):
                for channel in range(1,18):
                    name, wave, response = archive.curve(channel, kind=kind)
                    self.assertEqual(len(wave), len(response))
                    self.assertGreater(response.max(), 0)
                    self.assertEqual(len(archive.used[name]['sha256']),64)
            self.assertEqual(len(archive.used),35)
            with self.assertRaises(ValueError): archive.read('../escape')
            with self.assertRaises(ValueError): archive.curve(0)


if __name__ == '__main__':
    unittest.main()

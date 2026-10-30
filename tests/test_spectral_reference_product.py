from hashlib import sha256
import json
import unittest

from scripts import audit_spectral_reference_v2 as audit


class SpectralReferenceProductTests(unittest.TestCase):
    def read(self):
        return json.loads(audit.OUTPUT.read_text(encoding='utf-8'))

    def test_frozen_product_hashes_and_source_provenance(self):
        result = self.read()
        self.assertEqual(sha256(audit.OUTPUT.read_bytes()).hexdigest(), '21a07ae84771d4267c8afc992005a74eb82554c375e4c62cee21c3049187a97b')
        self.assertEqual(sha256(audit.DESIGN.read_bytes()).hexdigest(), result['protocol_sha256'])
        self.assertEqual(result['protocol_sha256'], 'fd7c0c6141d7a8b204190b04ca140017e9b0316585df07d21d913937c37718c9')
        self.assertEqual(result['protocol_commit'], 'f5a1e518a4d0f28268337f42af0bbabdfc605e78')
        for name, expected in result['source_hashes'].items():
            self.assertEqual(audit.lab.digest(audit.ROOT/name), expected, name)
        self.assertEqual(result['inputs'][audit.relative(audit.jwst.PATH)]['sha256'], audit.jwst.FILE_SHA256)
        self.assertEqual(len(result['laboratory']['selected_member_hashes']), 35)

    def test_all_conditions_and_missing_support_remain_visible(self):
        result = self.read()
        rows = result['records']
        expected = {(kind, channel, shift) for kind in ('Cent','Allpix') for channel in range(1,18) for shift in (-.0064,0.,.0064)}
        self.assertEqual({(r['kind'],r['channel'],r['shift_um']) for r in rows}, expected)
        self.assertEqual(len(rows), len(expected))
        for status in ('full_support','partial_only','numerical_failure'):
            self.assertEqual(sum(r['status']==status for r in rows), result['counts'][status])
        self.assertEqual(sum(result['counts'][s] for s in ('full_support','partial_only','numerical_failure')), result['counts']['attempted'])
        self.assertEqual(result['counts'], {'attempted':102,'full_support':0,'partial_only':102,'numerical_failure':0})
        for row in rows:
            self.assertIsNone(row['full_band_mean_jy'])
            self.assertIsNone(row['full_mean_to_monochromatic_ratio'])
            self.assertIsNone(row['full_mean_relative_to_zero_shift_percent'])
            self.assertGreater(row['unsupported_absolute_fraction'],0)
            self.assertLess(row['unsupported_absolute_fraction'],1)
            self.assertAlmostEqual(row['unsupported_absolute_weight']/row['full_absolute_weight'], row['unsupported_absolute_fraction'],places=13)
            self.assertEqual(len(row['supported_weights_sha256']),64)

    @unittest.skipUnless(audit.lab.ARCHIVE.exists() and audit.jwst.PATH.exists(), 'ignored laboratory and MAST inputs not cached')
    def test_real_inputs_reproduce_recorded_diagnostic(self):
        result = self.read()
        rebuilt = audit.build()
        # Current HEAD may be a later release; inputs and method must still be
        # byte-identical to the recorded source hashes. Do not rewrite history.
        rebuilt['protocol_commit'] = result['protocol_commit']
        self.assertEqual(rebuilt, result)


if __name__ == '__main__':
    unittest.main()

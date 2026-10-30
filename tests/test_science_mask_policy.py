import json
from pathlib import Path

from astropy.io import fits
import numpy as np
import unittest

from scripts import science_mask_policy as p
from scripts import audit_science_masks as audit


def header():
    h = fits.Header()
    for name in sorted(p.REQUIRED):
        h['MP_' + name] = p.VERIFIED_BITS[name]
    return h


class ScienceMaskPolicyTests(unittest.TestCase):
 def test_target_and_background_flags_and_validity(self):
     source, full, transient = 1 << 21, 1 << 12, 1
     f = np.array([0, source, full, full | source, transient, source | transient,
                   0, 0, 0, 0], dtype=np.uint64)
     image = np.array([1, 1, 1, 1, 1, 1, np.nan, 1, 1, 1])
     var = np.array([1, 1, 1, 1, 1, 1, 1, 0, -1, np.inf])
     target, background = p.science_masks(f, image, var, header(), 'spherex_qr2')
     assert target.tolist() == [True, True, False, False, False, False, False, False, False, False]
     assert background.tolist() == [True, False, False, False, False, False, False, False, False, False]


 def test_reject_mismatch_unknown_bits_and_bad_inputs(self):
     h = header()
     z = np.ones(1)
     for flags in (np.array([-1]), np.array([np.nan]), np.array([0.0]), np.array([True]),
                   np.array([1 << 63], dtype=np.uint64), np.array([1 << 22], dtype=np.uint64)):
         with self.assertRaises(ValueError):
             p.science_masks(flags, z, z, h, 'spherex_qr2')
     with self.assertRaises(ValueError):
         p.science_masks(np.array([0]), z, z, h, 'other')
     with self.assertRaises(ValueError):
         p.science_masks(np.array([0, 0]), z, z, h, 'spherex_qr2')
     bad = h.copy(); bad['MP_FULLSAMPLE'] = 13
     with self.assertRaises(ValueError):
         p.validate_layout(bad, 'spherex_qr2')
     bad = h.copy(); bad['MP_NEW_FLAG'] = 31
     with self.assertRaises(ValueError):
         p.validate_layout(bad, 'spherex_qr3')
     bad = h.copy(); del bad['MP_SOURCE']
     with self.assertRaises(ValueError):
         p.validate_layout(bad, 'spherex_qr2')
     bad = h.copy(); bad.append(('HIERARCH MP_SOURCE', 21))
     with self.assertRaises(ValueError):
         p.validate_layout(bad, 'spherex_qr2')
     h['MP_GHOST'] = 22
     target, _ = p.science_masks(np.array([1 << 22], dtype=np.uint64), z, z, h, 'spherex_qr3')
     assert not target[0]


 def test_count_region_independent_explicit_example(self):
     f = np.array([0, 1 << 21, 1 << 12, (1 << 12) | (1 << 21), 1, 0], dtype=np.uint64)
     im = np.array([1, 1, 1, 1, 1, np.nan]); v = np.ones(6)
     t, b = p.science_masks(f, im, v, header(), 'spherex_qr2')
     c = audit.count_region(f, im, v, t, b, np.ones(6, dtype=bool))
     assert c == {'pixels': 6, 'numeric_science': 5, 'fullsample_any': 2,
         'legacy_science_good': 4, 'legacy_science_good_fullsample': 2,
         'legacy_web_good': 4, 'legacy_web_good_fullsample': 2,
         'strict_target_good': 2, 'strict_background_good': 1}


 def test_public_product_totals_and_optional_raw_replay(self):
     path = Path('web/data/mask-audit/development-audit.json')
     product = json.loads(path.read_text(encoding='utf-8'))
     assert product['records_count'] == len(product['records']) == 31
     for region, totals in product['totals'].items():
         for key, value in totals.items():
             assert value == sum(row['regions'][region][key] for row in product['records'])
     for path, expected in product['source_sha256'].items():
         assert audit.digest(Path(path)) == expected
     if audit.MANIFEST.exists():
         assert audit.build() == product

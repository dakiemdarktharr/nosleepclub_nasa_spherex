"""Synthetic factorial, denominator, statistics and gate-contract checks."""
import copy
import json
from itertools import product
import unittest

from astropy import units as u
import numpy as np

from scripts.signal_control_metrics import clopper_pearson, summarize_signal_control


def fixture():
    keys = []
    for g, t, p, s, f, a in product(('g0', 'g1'), ('matched', 'gaussian'), ('0', '1', '2', '3'),
                                     ('isolated', 'modeled', 'omitted'), ('600', '1200'), ('baseline', 'corrected')):
        keys.append(('noiseless', g, t, p, s, f, '0', a))
    for g, p, s, d, a in product(('g0', 'g1'), ('0', '3'), ('isolated', 'modeled', 'omitted'),
                                  range(16), ('baseline', 'corrected')):
        keys.append(('noisy', g, 'gaussian', p, s, '1200', str(d), a))
    for g, p, d, a in product(('g0', 'g1'), ('0', '3'), range(8), ('baseline', 'corrected')):
        keys.append(('null', g, 'none', p, 'isolated', '0', str(d), a))
    records = []
    for key in keys:
        section, _, _, _, scene, flux, draw, _ = key;truth = int(flux)*1e-6
        payload = {'status':'fit_completed', 'numerical_support':True, 'true_flux_jy':truth,
                   'target_flux_jy': ((1. if int(draw) % 2 == 0 else -1.)*1e-5 if section == 'null' else truth),
                   'position_native_error': None if section == 'null' else [0., 0.],
                   'distance_to_companion_native': None if scene == 'isolated' else 1.5}
        records.append({'key':list(key), 'payload':payload})
    return keys, records


def index(records):return {tuple(r['key']): r['payload'] for r in records}


class SignalControlMetricTests(unittest.TestCase):
    def test_complete_factorial_keeps_null_separate_and_gates(self):
        keys, records = fixture();out = summarize_signal_control(records, keys)
        self.assertEqual(out['section_counts'], {'noiseless':192, 'noisy':384, 'null':64})
        self.assertEqual((out['paired']['planned'], out['paired']['both_completed'], out['paired']['missing']), (320, 320, 0))
        self.assertEqual(out['noiseless_clean_gate']['planned'], 128)
        self.assertEqual(out['noiseless_preservation_guard']['planned_pairs'], 64)
        self.assertTrue(out['noiseless_clean_gate']['passed'])
        self.assertEqual(len(out['noisy_clean_gates']), 16)
        self.assertTrue(out['noisy_clean_all_gates_passed'])
        self.assertTrue(out['noiseless_preservation_guard']['passed'])
        self.assertTrue(out['old_assessment_blocked']);self.assertFalse(out['promotion'])
        self.assertEqual(len(out['null_strata']), 8)
        for group in out['null_strata']:
            self.assertEqual(group['planned'], 8);self.assertEqual(group['positive_supported'], 4)
            self.assertNotIn('detection', group);self.assertNotIn('flux_ratio', group)
        null_record = next(r for r in out['records'] if r['key'][0] == 'null')
        self.assertIsNone(null_record['values']['position_native_error']);self.assertIsNone(null_record['values']['flux_ratio'])
        json.dumps(out, allow_nan=False)

    def test_failure_and_sample_gate_are_counted_on_all_planned(self):
        keys, records = fixture();items = index(records)
        nkey = ('noisy','g0','gaussian','0','modeled','1200','0','corrected')
        items[nkey].clear();items[nkey].update(status='fit_failed', error='synthetic fit failure')
        ckey = ('noiseless','g0','matched','1','isolated','600','0','corrected')
        items[ckey].clear();items[ckey].update(status='preparation_failed', error='synthetic preparation failure')
        out = summarize_signal_control(records, keys)
        self.assertFalse(out['noiseless_clean_gate']['passed'])
        self.assertFalse(out['noiseless_preservation_guard']['passed'])
        self.assertEqual(out['paired']['missing'], 2)
        pair = next(p for p in out['paired']['rows'] if p['key_without_arm'] == list(ckey[:-1]))
        self.assertFalse(pair['both_completed']);self.assertTrue(pair['new_numerical_refusal'])
        gate = next(g for g in out['noisy_clean_gates'] if g['geometry']=='g0' and g['phase']=='0'
                    and g['scene']=='modeled' and g['arm']=='corrected')
        self.assertEqual((gate['planned'], gate['success']), (16, 15))
        self.assertTrue(gate['observed_sample_gate_passed'])
        items[('noisy','g0','gaussian','0','modeled','1200','1','corrected')]['numerical_support'] = False
        out = summarize_signal_control(records, keys)
        self.assertFalse(out['noisy_clean_all_gates_passed'])

    def test_signed_bias_cancellation_does_not_hide_radial_error_or_switch(self):
        keys, records = fixture();items = index(records)
        for d in range(16):
            key = ('noisy','g0','gaussian','0','modeled','1200',str(d),'baseline')
            items[key]['position_native_error'] = [.08 if d%2 else -.08, 0.]
            items[key]['target_flux_jy'] = .0012*(.9 if d%2 else 1.1)
        out = summarize_signal_control(records, keys)
        group = next(g for g in out['strata'] if g['section']=='noisy' and g['geometry']=='g0'
                     and g['phase']=='0' and g['scene']=='modeled' and g['arm']=='baseline')
        m = group['all_completed']
        self.assertAlmostEqual(m['mean_dx_dy_native_px'][0], 0., places=14)
        self.assertAlmostEqual(m['rms_radial_native_px'], .08)
        self.assertAlmostEqual(m['mean_flux_ratio'], 1.);self.assertGreater(m['flux_ratio_mcse'], 0.)
        key = ('noisy','g0','gaussian','0','omitted','1200','0','baseline')
        items[key]['position_native_error'] = [1.49, 0.];items[key]['distance_to_companion_native'] = .01
        out = summarize_signal_control(records, keys)
        switched = next(r for r in out['records'] if r['key'] == list(key))
        self.assertEqual(switched['values']['identity'], 'companion')
        self.assertEqual(len(out['noisy_clean_gates']), 16)  # omitted is stress only
        self.assertTrue(out['noisy_clean_all_gates_passed'])
        items[key]['distance_to_companion_native'] = None
        out = summarize_signal_control(records, keys)
        self.assertEqual(next(r for r in out['records'] if r['key'] == list(key))['values']['identity'], 'unknown')

    def test_secondary_guard_does_not_drop_pairs_or_hide_worsening(self):
        keys, records = fixture();items = index(records)
        key = ('noiseless','g1','gaussian','3','modeled','1200','0','corrected')
        items[key]['position_native_error'] = [.021, 0.]
        items[key]['target_flux_jy'] = .0012*1.021
        out = summarize_signal_control(records, keys)
        self.assertTrue(out['noiseless_clean_gate']['passed'])
        self.assertFalse(out['noiseless_preservation_guard']['passed'])
        bad = next(r for r in out['noiseless_preservation_guard']['rows'] if r['key_without_arm'] == list(key[:-1]))
        self.assertFalse(bad['passed'])
        pair = next(r for r in out['paired']['rows'] if r['key_without_arm'] == list(key[:-1]))
        np.testing.assert_allclose(pair['delta_position_native_px'], [.021, 0.])
        self.assertAlmostEqual(pair['delta_flux_ratio'], .021)

    def test_exact_intervals_and_strict_input_validation(self):
        np.testing.assert_allclose(clopper_pearson(16,16), [.7940927857921772, 1.], atol=1e-14)
        np.testing.assert_allclose(clopper_pearson(0,8), [0., .36941664755281917], atol=1e-14)
        np.testing.assert_allclose(clopper_pearson(15,16)[0], .697679261565468, atol=1e-14)
        for values in ((True, 16), (1, 0), (-1, 16), (17, 16)):
            with self.subTest(values=values), self.assertRaises(ValueError):clopper_pearson(*values)
        keys, original = fixture()
        for field, value in (('target_flux_jy', True), ('target_flux_jy', np.nan),
                             ('true_flux_jy', .5*u.Jy), ('true_flux_jy', 0.),
                             ('position_native_error', [True, 0.]), ('position_native_error', [np.inf, 0.])):
            records = copy.deepcopy(original);records[0]['payload'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):summarize_signal_control(records, keys)
        with self.assertRaises(ValueError):summarize_signal_control(original[:-1], keys)
        with self.assertRaises(ValueError):summarize_signal_control(original[:-1]+[original[0]], keys)
        with self.assertRaises(ValueError):summarize_signal_control(original, keys[:-1]+[keys[0]])
        bad = copy.deepcopy(original);bad[0]['payload']['status'] = 'unknown'
        with self.assertRaises(ValueError):summarize_signal_control(bad, keys)
        wrong = list(keys);wrong[0] = (*wrong[0][:-1], 'unknown')
        with self.assertRaises(ValueError):summarize_signal_control(original, wrong)
        wrong = list(keys);badkey = list(wrong[0]);badkey[3] = '4';wrong[0] = tuple(badkey)
        with self.assertRaisesRegex(ValueError, 'factorial'):summarize_signal_control(original, wrong)
        wrong = list(keys);badkey = list(wrong[0]);badkey[0] = 'unexpected';wrong[0] = tuple(badkey)
        with self.assertRaisesRegex(ValueError, 'unknown'):summarize_signal_control(original, wrong)


if __name__ == '__main__':unittest.main()

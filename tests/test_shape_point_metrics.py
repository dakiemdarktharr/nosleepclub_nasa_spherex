"""Deterministic primary-set summaries; no images, fits, or random draws."""
import copy
import json
import unittest

import numpy as np

from scripts.shape_point_metrics import summarize_primary
from scripts.run_shape_point_study import RULES


def sample():
    keys = [(f's{i}', f'e{j}') for i in range(7) for j in range(8)]
    seasons = {f'e{j}': 'before' if j < 4 else 'after' for j in range(8)}
    def record(radial, support=True):
        return {'status': 'fit_completed', 'fit': {'numerical_support': support},
                'residual_east_north_arcsec': [radial, 0.]}
    return keys, {k: record(.3) for k in keys}, {k: record(.4) for k in keys}, seasons


def summarize(keys, new, old, seasons, rules=None):
    return summarize_primary(keys, new, old, seasons, rules or RULES['primary_gate'])


class ShapePointMetricsTests(unittest.TestCase):
    def test_all_pairs_equal_source_and_frozen_gates(self):
        keys, new, old, seasons = sample();out = summarize(keys, new, old, seasons)
        self.assertEqual(out['planned'], 56);self.assertEqual(out['common_completed_pairs'], 56)
        self.assertEqual(out['paired_source_count'], 7);self.assertEqual(out['supported_source_count'], 7)
        self.assertAlmostEqual(out['equal_source_mean_radial_improvement_arcsec'], .1)
        self.assertAlmostEqual(out['paired_point_rms_radial_arcsec'], .3)
        self.assertAlmostEqual(out['pooled_point_p90_radial_arcsec'], .3)
        self.assertTrue(all(out['gates'].values()));self.assertTrue(out['developmental_gates_passed'])
        self.assertFalse(out['promotion'])
        json.dumps(out, allow_nan=False)

    def test_partial_worst_source_is_retained_in_equal_source_mean(self):
        keys, new, old, seasons = sample()
        for key in [k for k in keys if k[0] == 's6']:
            old[key]['fit']['numerical_support'] = False
            new[key] = {'status': 'fit_failed', 'error': 'synthetic failure'}
        new[('s6', 'e0')] = {'status': 'fit_completed', 'fit': {'numerical_support': False},
                               'residual_east_north_arcsec': [5., 0.]}
        out = summarize(keys, new, old, seasons)
        source = next(x for x in out['source_rows'] if x['source_id'] == 's6')
        self.assertEqual(source['pair_count'], 1);self.assertFalse(source['support_gate_met'])
        self.assertEqual(out['supported_source_count'], 6);self.assertEqual(out['paired_source_count'], 7)
        self.assertTrue(out['gates']['source_season_support'])
        self.assertAlmostEqual(out['equal_source_point_mean_radial_arcsec'], (6*.3+5.)/7)
        self.assertFalse(out['gates']['equal_source_improvement'])
        self.assertEqual(out['common_completed_pairs'], 49)

    def test_missing_failures_and_numerical_refusals_are_not_dropped(self):
        keys, new, old, seasons = sample()
        del new[('s0', 'e0')]
        new[('s0', 'e1')] = {'status': 'fit_failed', 'error': 'synthetic failed'}
        new[('s0', 'e2')]['fit']['numerical_support'] = False
        old[('s1', 'e0')] = {'status': 'preparation_failed', 'error': 'old missing'}
        for key in [k for k in keys if k[0] == 's6']:
            new[key] = {'status': 'preparation_failed', 'error': 'no new fit'}
            old[key]['fit']['numerical_support'] = False
        out = summarize(keys, new, old, seasons)
        self.assertEqual(out['new_numerical_refusals'], 3)
        self.assertFalse(out['gates']['all_planned_records_available'])
        self.assertFalse(out['gates']['no_new_numerical_refusals'])
        self.assertEqual(out['baseline_status_counts']['preparation_failed'], 1)
        self.assertEqual(out['point_status_counts']['missing'], 1)
        missing_source = next(x for x in out['source_rows'] if x['source_id'] == 's6')
        self.assertEqual(missing_source['pair_count'], 0);self.assertIsNone(missing_source['point_mean_radial_arcsec'])
        self.assertEqual(len(out['rows']), 56);self.assertFalse(out['developmental_gates_passed'])
        rows = {tuple(r['key']): r for r in out['rows']}
        self.assertEqual(rows[('s1', 'e0')]['baseline_status'], 'preparation_failed')
        self.assertTrue(rows[('s0', 'e0')]['new_numerical_refusal'])
        self.assertTrue(rows[('s0', 'e2')]['common_completed'])  # no numerical selection
        json.dumps(out, allow_nan=False)

    def test_inclusive_boundaries_and_invalid_allocations(self):
        keys, new, old, seasons = sample();rules = dict(RULES['primary_gate'])
        for key in keys:
            old[key]['residual_east_north_arcsec'] = [.625, 0.]
            new[key]['residual_east_north_arcsec'] = [.5, 0.]
        rules.update(equal_source_mean_radial_improvement_min_arcsec=.125,
                     paired_new_rms_max_arcsec=.5, paired_new_p90_max_arcsec=.5)
        out = summarize(keys, new, old, seasons, rules)
        self.assertTrue(out['gates']['equal_source_improvement'])
        self.assertTrue(out['gates']['paired_new_rms']);self.assertTrue(out['gates']['paired_new_p90'])
        self.assertTrue(out['developmental_gates_passed'])
        bad = copy.deepcopy(new);bad[keys[0]]['residual_east_north_arcsec'] = [True, .1]
        for arguments in ((keys[:-1], new, old, seasons), (keys[:-1]+[keys[0]], new, old, seasons),
                          (keys, bad, old, seasons), (keys, new, old, {'e0': 'before'})):
            with self.subTest(arguments=len(arguments[0])), self.assertRaises(ValueError):
                summarize(*arguments)
        bad = copy.deepcopy(new);bad[keys[0]]['residual_east_north_arcsec'] = [np.nan, 0.]
        with self.assertRaises(ValueError):summarize(keys, bad, old, seasons)


if __name__ == '__main__': unittest.main()

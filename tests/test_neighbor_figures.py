"""Check the shipped plot evidence without requiring the optional plotting stack."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'web/data/neighbor-intervention'


class NeighborFigureTests(unittest.TestCase):
    def test_full_denominators_coordinates_sources_and_inert_svg(self):
        path = FOLDER / 'figures.json'
        if not path.exists():
            self.skipTest('audited products have not yet been plotted')
        manifest = json.loads(path.read_text(encoding='utf-8'))
        overview = json.loads((FOLDER / 'overview.json').read_text(encoding='utf-8'))
        controls = json.loads((FOLDER / 'controls.json').read_text(encoding='utf-8'))
        for key, source in (
            ('source_overview_sha256', FOLDER / 'overview.json'),
            ('source_controls_sha256', FOLDER / 'controls.json'),
            ('script_sha256', ROOT / 'scripts/plot_neighbor_intervention.py'),
            ('dependency_manifest_sha256', ROOT / 'requirements-figures.txt'),
        ):
            self.assertEqual(manifest[key], sha256(source.read_bytes()).hexdigest())
        self.assertEqual(len(manifest['figures']), 3)
        real = [f for f in manifest['figures'] if f['role'] == 'real_model_sensitivity']
        self.assertEqual({f['configuration'] for f in real}, {'broad', 'strict'})
        for figure in real:
            group = next(g for g in overview['real']['configurations']
                         if g['configuration'] == figure['configuration'])
            rows = {r['variant']: r for r in group['pairs']}
            baseline = rows['plane_nearest_free']['east_north_arcsec']
            expected = {v: np.asarray(r['east_north_arcsec']) - baseline for v, r in rows.items()
                        if baseline is not None and r['east_north_arcsec'] is not None}
            self.assertEqual(figure['planned_pairs'], 8)
            self.assertEqual(figure['plotted_pairs'], len(expected))
            self.assertEqual(set(figure['missing_variants']), set(rows) - set(expected))
            self.assertEqual(set(figure['plotted_delta_east_north']), set(expected))
            for variant, value in expected.items():
                np.testing.assert_allclose(figure['plotted_delta_east_north'][variant], value,
                                           atol=1e-12, rtol=1e-12)
            self.assertEqual(figure['minimum_axis_span_arcsec'], .1)
        error_figure = next(f for f in manifest['figures']
                            if f['role'] == 'all_common_completed_control_errors')
        expected = []
        for row in controls['paired_draws']:
            a, b = (row['arms'][v] for v in ('plane_nearest_free', 'plane_nearest_nonnegative'))
            if a['completed'] and b['completed']:
                expected.append({'case': row['case'], 'draw': row['draw'],
                                 'free_error_arcsec': a['error_arcsec'],
                                 'nonnegative_error_arcsec': b['error_arcsec'],
                                 'both_numerically_supported': bool(
                                     a['numerical_support_both'] and b['numerical_support_both'])})
        self.assertEqual(error_figure['planned_paired_draws'], 64)
        self.assertEqual(error_figure['plotted_paired_draws'], len(expected))
        self.assertEqual(error_figure['points'], expected)
        for figure in manifest['figures']:
            self.assertEqual(figure['units'], 'arcsec')
            raw = (ROOT / 'web' / figure['path']).read_bytes()
            self.assertEqual(figure['bytes'], len(raw))
            self.assertEqual(figure['sha256'], sha256(raw).hexdigest())
            self.assertNotIn(b'\r', raw)
            self.assertTrue(all(line == line.rstrip(b' \t') for line in raw.split(b'\n')))
            for node in ET.fromstring(raw).iter():
                self.assertNotIn(node.tag.rsplit('}', 1)[-1], ('script', 'foreignObject', 'image'))
                for key, value in node.attrib.items():
                    if key.rsplit('}', 1)[-1] == 'href':
                        self.assertTrue(value.startswith('#'))
                    self.assertFalse(key.lower().startswith('on'))


if __name__ == '__main__':
    unittest.main()

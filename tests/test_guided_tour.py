"""The color-reading tour points to actual displayed pixels, not invented examples."""
import json
from hashlib import sha256
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'web/assets/mission/epsilon-sequence'


class GuidedTourTests(unittest.TestCase):
    def test_tour_colors_match_provenanced_preview_pixels(self):
        activity = json.loads((DIRECTORY / 'activities.json').read_text(encoding='utf-8'))
        archive = json.loads((DIRECTORY / 'provenance.json').read_text(encoding='utf-8'))
        first = activity['cases'][0]
        observations = {row['obs_id']: row for row in archive['observations']}
        self.assertEqual([point['display_rgb'] for point in first['tutorial']],
                         [[255, 140, 0], [255, 255, 255], [0, 0, 0]])
        for point in first['tutorial']:
            row = observations[first['observations'][0 if point['side'] == 'A' else 1]]
            path = DIRECTORY / row['image']
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), row['png_sha256'])
            with Image.open(path) as image:
                self.assertEqual(image.convert('RGB').getpixel((point['x'], point['y'])), tuple(point['display_rgb']))
            self.assertEqual(set(point['title']), {'vi', 'en'})
            self.assertEqual(set(point['explanation']), {'vi', 'en'})

    def test_every_incorrect_choice_has_a_specific_bilingual_reason(self):
        activity = json.loads((DIRECTORY / 'activities.json').read_text(encoding='utf-8'))
        for case in activity['cases']:
            for option in case['options']:
                if option['id'] == case['answer']:
                    continue
                self.assertEqual(set(option['feedback']), {'vi', 'en'})
                self.assertTrue(all(len(reason) > 30 for reason in option['feedback'].values()))


if __name__ == '__main__':
    unittest.main()

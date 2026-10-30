"""Keep scientific controls connected through the redesigned beginner journey."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]


class Nodes(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a' and a.get('href','').startswith('#'):self.links.append(a['href'][1:])


class FrontendContract(unittest.TestCase):
    def test_unique_ids_and_working_in_page_navigation(self):
        doc=Nodes();doc.feed((ROOT/'web/index.html').read_text(encoding='utf-8'))
        self.assertEqual(len(doc.ids),len(set(doc.ids)))
        self.assertTrue(set(doc.links)-{''}<=set(doc.ids))

    def test_javascript_controls_have_targets(self):
        doc=Nodes();doc.feed((ROOT/'web/index.html').read_text(encoding='utf-8'))
        for path in [ROOT/'web/app.js',ROOT/'web/mission.js']:
            targets=set(re.findall(r'\$\("([^"\n]+)"\)',path.read_text(encoding='utf-8')))
            self.assertFalse(targets-set(doc.ids)-{'gaia-nav'},f'{path.name}: missing {targets-set(doc.ids)}')
        for name in ['quality.js','covariance.js','ablation.js','linked-evidence.js','neighbor-evidence.js']:
            targets=set(re.findall(r'el\("([^"\n]+)"\)',(ROOT/'web'/name).read_text(encoding='utf-8')))
            self.assertFalse(targets-set(doc.ids),f'{name}: missing {targets-set(doc.ids)}')

    def test_art_and_observation_sources_are_distinct(self):
        html=(ROOT/'web/index.html').read_text(encoding='utf-8')
        self.assertIn('Minh họa nghệ thuật · Canva',html)
        self.assertIn('Ảnh quan sát thật',html)
        self.assertIn('Đọc kết quả & giới hạn',html)
        for file in ['brown-dwarf-canva.webp','compare-guide-canva.webp']:
            self.assertTrue((ROOT/'web/assets'/file).exists())

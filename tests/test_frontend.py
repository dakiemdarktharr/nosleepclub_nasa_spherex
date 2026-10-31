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


class WorkflowNodes(HTMLParser):
    def __init__(self):super().__init__();self.stack=[];self.owner={};self.views={};self.tags={}
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);view=a.get('data-workflow-view') or next((v for _,v in reversed(self.stack) if v),None)
        if 'id' in a:self.owner[a['id']]=view;self.tags[a['id']]=a
        if 'data-workflow-view' in a:self.views[a['data-workflow-view']]=a
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append((tag,view))
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:del self.stack[i:];break


class FrontendContract(unittest.TestCase):
    def test_workflow_controls_belong_to_their_processing_step(self):
        doc=WorkflowNodes();doc.feed((ROOT/'web/index.html').read_text(encoding='utf-8'))
        expected={'scene-select':'data','explorer-form':'data','sky':'compare','explorer-image':'compare',
                  'motion-panel':'check','selection-detail':'check','review-note':'review',
                  'save-review':'review','explorer-note':'review','explorer-export':'review',
                  'signal-controls':'research','profile-landscape':'research','model-selection':'research'}
        for control,owner in expected.items():self.assertEqual(doc.owner[control],owner,control)
        self.assertEqual(set(doc.views),{'data','compare','check','review','research'})
        self.assertEqual([k for k,v in doc.views.items() if 'hidden' not in v],['data'])

    def test_workflow_has_visible_labels_focus_targets_and_no_inline_execution(self):
        html=(ROOT/'web/index.html').read_text(encoding='utf-8');doc=WorkflowNodes();doc.feed(html)
        for name in ['data','compare','check','review','research']:
            self.assertEqual(doc.tags[f'step-{name}-title']['tabindex'],'-1')
        self.assertEqual(doc.tags['workflow-report-title']['tabindex'],'-1')
        self.assertNotIn('class="sr-only" for="review-note"',html)
        self.assertNotRegex(html,r'<script(?![^>]*\bsrc=)[^>]*>')
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

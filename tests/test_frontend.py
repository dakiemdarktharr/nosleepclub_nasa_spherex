"""Keep scientific controls connected through the redesigned beginner journey."""
from hashlib import sha256
from html.parser import HTMLParser
import json
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
    def test_public_routes_preserve_the_original_comparison_canvas(self):
        doc=WorkflowNodes()
        doc.feed((ROOT/'web/index.html').read_text(encoding='utf-8'))
        for route in ('orbit','about','night-sky','learn'):
            self.assertIn('data-public-page',doc.tags[route])
        self.assertEqual(doc.owner['sky'],'compare')
        self.assertEqual(doc.owner['explorer-timeline'],'compare')
        self.assertIsNone(doc.owner['archived-sequence'])

    def test_public_preview_filenames_and_hashes_match_observation_provenance(self):
        assets=ROOT/'web/assets/mission'
        full=json.loads((assets/'full-fields/provenance.json').read_text(encoding='utf-8'))
        targets=json.loads((ROOT/'web/data/challenge-targets.json').read_text(encoding='utf-8'))
        self.assertEqual(set(full['fields']),{row['id'] for row in targets['targets']})
        for target in targets['targets']:
            row=full['fields'][target['id']]
            self.assertEqual((row['center_ra_deg'],row['center_dec_deg'],row['compare_fov_deg']),
                             (target['ra_deg'],target['dec_deg'],target['fov_deg']))
            image=ROOT/'web'/row['image'].lstrip('/')
            self.assertEqual(sha256(image.read_bytes()).hexdigest(),row['preview_sha256'])
            self.assertNotIn('source_file_sha256',row)
            self.assertNotIn('source_file_bytes',row)
            self.assertEqual(row['source_byte_range'][1]-row['source_byte_range'][0]+1,row['source_bytes_used'])
            self.assertRegex(row['source_byte_sha256'],r'^[a-f0-9]{64}$')

        archive=assets/'epsilon-sequence'
        saved=json.loads((archive/'provenance.json').read_text(encoding='utf-8'))
        receipt=json.loads((ROOT/'docs/data/spherex-dr1-timeline-smoke.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['settings'],receipt['settings'])
        self.assertEqual(len(saved['observations']),3)
        for loaded,verified in zip(saved['observations'],receipt['observations']):
            self.assertEqual({k:v for k,v in loaded.items() if k!='image'},verified)
            self.assertEqual(sha256((archive/loaded['image']).read_bytes()).hexdigest(),verified['png_sha256'])

    def test_workflow_controls_belong_to_their_processing_step(self):
        doc=WorkflowNodes();doc.feed((ROOT/'web/index.html').read_text(encoding='utf-8'))
        expected={'scene-select':'data','explorer-form':'data','sky':'compare','explorer-image':'compare',
                  'explorer-image-wrap':'compare','explorer-center-status':'compare','explorer-frame-meta':'compare',
                  'explorer-frame-hash':'compare','explorer-source-fits':'compare','explorer-download-fits':'compare',
                  'motion-panel':'check','selection-detail':'check','review-note':'review',
                  'save-review':'review','explorer-note':'review','explorer-export':'review',
                  'signal-controls':'research','profile-landscape':'research','model-selection':'research'}
        for control,owner in expected.items():self.assertEqual(doc.owner[control],owner,control)
        self.assertEqual(set(doc.views),{'data','compare','check','review','research'})
        self.assertEqual([k for k,v in doc.views.items() if 'hidden' not in v],['data'])
        html=(ROOT/'web/index.html').read_text(encoding='utf-8')
        primary=html.split('<nav id="main-nav"',1)[1].split('</nav>',1)[0]
        sidebar=html.split('<nav aria-label="Quy trình xử lý"',1)[1].split('</nav>',1)[0]
        for removed in ('#check-step','#review-step','data-step-link="check"','data-step-link="review"'):
            self.assertNotIn(removed,primary+sidebar)
        self.assertNotIn('id="workflow-compare-next"',html)
        self.assertNotIn('id="privacy-open"',html)
        self.assertIn('<option value="0.40" selected>',html)

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
        self.assertIn('assets/mission/spherex-bauhaus.svg',html)
        self.assertIn('Ảnh SPHEREx DR1, dải D6 · NASA/IPAC IRSA',html)
        self.assertIn('Ảnh quan sát thật',html)
        self.assertIn('Đọc kết quả & giới hạn',html)
        for file in ['orbit.webp','sky.webp','field.webp','timeline.webp','compare.webp']:
            self.assertTrue((ROOT/'web/assets/guide'/file).is_file())

    def test_guided_cases_reference_two_provenanced_observations(self):
        archive=ROOT/'web/assets/mission/epsilon-sequence'
        cases=json.loads((archive/'activities.json').read_text(encoding='utf-8'))['cases']
        self.assertGreaterEqual(len(cases),3)
        examples=set()
        for case in cases:
            path=(archive/case.get('archive','provenance.json')).resolve()
            manifest=json.loads(path.read_text(encoding='utf-8'))
            reference={entry['obs_id']: entry for entry in manifest['observations']}
            first,second=[reference[obs_id] for obs_id in case['observations']]
            self.assertLess(first['mjd_obs_utc'],second['mjd_obs_utc'])
            self.assertIn(case['answer'],[option['id'] for option in case['options']])
            self.assertEqual(set(case['explanation']),{'en','vi'})
            if 'archive' in case:
                self.assertTrue(examples.isdisjoint(case['observations']))
                self.assertGreaterEqual(manifest['common_center_band_fraction_of_widest'],.75)
                self.assertEqual(first['contrast_low'],second['contrast_low'])
                self.assertEqual(first['contrast_high'],second['contrast_high'])
                for item in (first,second):
                    self.assertEqual(sha256((path.parent/item['image']).read_bytes()).hexdigest(),item['png_sha256'])
            examples.update(case['observations'])

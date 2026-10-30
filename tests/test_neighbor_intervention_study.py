from contextlib import ExitStack,contextmanager
import copy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import astropy.units as u
import numpy as np

from scripts import run_neighbor_intervention as study


def samples(epoch):
    return [{'obs_id':epoch+str(i),'data':np.ones(8),'error':np.ones(8),
        'background_design':np.ones((8,1)),'neighbor_design':np.empty((8,0)),
        'neighbor_ids':[],'neighbor_unit':str(u.MJy/u.sr/u.Jy),
        'renderer':lambda p:np.ones(8)*(u.MJy/u.sr/u.Jy),
        'metadata':{'obs_id':epoch+str(i),'x':list(range(8)),'y':[0]*8}}
        for i in range(2)]


def fake_configuration(frames,label):
    groups=[[{'record':{'obs_id':e+str(i)}} for i in range(2)] for e in ('before','after')]
    prepared=[[{'epoch':e}] for e in ('before','after')]
    return groups,prepared,[None,None]


def fake_semantic(prepared,anchor,**kwargs):return samples(prepared[0]['epoch'])


def fake_fit(items,anchor,**kwargs):
    return {'position':list(anchor),'frames':[{'obs_id':x['obs_id']} for x in items],
            'numerical_support':True,'numerical_reasons':[]}


def fake_realize(geometry,items,case,case_index,draw,epoch_index):
    ident=f"{case['id']}:{draw}:{epoch_index}"
    return items,{'realization_sha256':sha256(ident.encode()).hexdigest(),'truth_position_sky_px':[31.73,31.31]}


@contextmanager
def sandbox():
    base=study.ROOT/'data/raw/benchmark';base.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base,prefix='neighbor-unittest-') as directory:
        root=Path(directory).resolve();assert base.resolve() in root.parents
        design=root/'design.json';design.write_text('synthetic locked design',encoding='utf-8')
        output=root/'report.json'
        inventory={'sources':{},'raw':{},'opened_products':{}}
        with ExitStack() as stack:
            stack.enter_context(patch.object(study,'DESIGN',design));stack.enter_context(patch.object(study,'OUTPUT',output))
            stack.enter_context(patch.object(study,'verify_design',return_value=inventory))
            stack.enter_context(patch.object(study,'verify_frozen_commit'))
            stack.enter_context(patch.object(study,'execution_runtime',return_value={'synthetic':'runtime'}))
            stack.enter_context(patch.dict(study.RULES['controls'],{'draws_per_case':1}))
            stack.enter_context(patch.object(study.inputs,'read_verified_frames',return_value=([],{})))
            stack.enter_context(patch.object(study,'prepare_configuration',side_effect=fake_configuration))
            semantic=stack.enter_context(patch.object(study.adapter,'prepare_semantic',side_effect=fake_semantic))
            fit=stack.enter_context(patch.object(study.model,'fit_epoch',side_effect=fake_fit))
            stack.enter_context(patch.object(study,'load_gain',return_value=np.ones((1,1))))
            stack.enter_context(patch.object(study,'control_geometry',return_value=[{'synthetic':True}]))
            stack.enter_context(patch.object(study,'realize',side_effect=fake_realize))
            stack.enter_context(patch('builtins.print'))
            yield output,fit,semantic,inventory


def load(path):return json.loads(path.read_text(encoding='utf-8'))


class NeighborStudyTests(unittest.TestCase):
    def test_planned_denominators(self):
        keys=study.expected_keys()
        self.assertEqual(sum(k[0]=='real' for k in keys),32)
        self.assertEqual(sum(k[0]=='control' for k in keys),256)
        self.assertEqual(len(keys),288)

    def test_real_then_control_resume_never_refits_and_preserves_pairing(self):
        with sandbox() as (output,fit,semantic,_):
            ids=[v['id'] for v in study.VARIANTS]
            study.run(['real'],['broad','strict'],ids)
            first=load(output);self.assertEqual(len(first['records']),32);self.assertFalse(first['completed'])
            self.assertEqual(fit.call_count,32);fit.reset_mock();semantic.reset_mock()
            study.run(['real'],['broad','strict'],ids)
            self.assertEqual(fit.call_count,0);self.assertEqual(semantic.call_count,0)
            self.assertEqual(first['records'],load(output)['records'])
            study.run(['controls'],[],ids);last=load(output)
            self.assertTrue(last['completed']);self.assertEqual(last['counts'],{'planned':48,'recorded':48,'fit_completed':48,'failed':0})
            self.assertEqual(fit.call_count,16)
            for case in study.CASES:
                for epoch in ('before','after'):
                    rows=[r for r in last['records'] if r['section']=='control' and r['case']==case['id'] and r['epoch']==epoch]
                    self.assertEqual(len(rows),2);self.assertEqual(rows[0]['control'],rows[1]['control'])
                    self.assertIn('synthetic',rows[0]['data_role'])
            with self.assertRaisesRegex(RuntimeError,'completed'):study.run(['controls'],[],ids)

    def test_preparation_and_fit_failures_remain_terminal(self):
        with sandbox() as (output,fit,semantic,_):
            def fail_some(prepared,anchor,**kwargs):
                if prepared[0]['epoch']=='after' and kwargs['background_order']==2 and kwargs['epsf_kind']=='bilinear':
                    raise ValueError('synthetic quadratic/bilinear preparation failure')
                return fake_semantic(prepared,anchor,**kwargs)
            semantic.side_effect=fail_some
            count=0
            def fail_once(items,anchor,**kwargs):
                nonlocal count
                count+=1
                if count==1:raise study.model.NeighborFitError('synthetic solver failure',[{'success':False}]*9)
                return fake_fit(items,anchor,**kwargs)
            fit.side_effect=fail_once
            ids=[v['id'] for v in study.VARIANTS]
            study.run(['real'],['broad','strict'],ids);report=load(output)
            failed=[r for r in report['records'] if r['status']!='fit_completed']
            self.assertEqual(len(failed),5);self.assertTrue(all(len(r['obs_ids'])==2 for r in failed))
            self.assertEqual(len(next(r for r in failed if r['status']=='fit_failed')['start_reports']),9)
            before=fit.call_count;study.run(['real'],['broad','strict'],ids)
            self.assertEqual(fit.call_count,before)

    def test_frame_drop_or_fit_identity_change_is_failure(self):
        with sandbox() as (output,fit,semantic,_):
            semantic.side_effect=lambda prepared,anchor,**kwargs:fake_semantic(prepared,anchor,**kwargs)[:1]
            study.run(['real'],['strict'],[study.VARIANTS[0]['id']]);rows=load(output)['records']
            self.assertEqual(fit.call_count,0);self.assertEqual(len(rows),2)
            self.assertTrue(all(r['status']=='preparation_failed' and 'identities' in r['error'] for r in rows))
        with sandbox() as (output,fit,semantic,_):
            fit.side_effect=lambda *a,**kw:{'frames':[]}
            study.run(['real'],['strict'],[study.VARIANTS[0]['id']]);rows=load(output)['records']
            self.assertTrue(all(r['status']=='fit_failed' for r in rows))

    def test_pair_hash_mismatch_and_tampered_checkpoint_fail_closed(self):
        with sandbox() as (output,fit,semantic,design):
            study.run(['controls'],[],[study.CONTROL_VARIANTS[0]])
            original=load(output);self.assertEqual(len(original['records']),8)
            for field in ('rules','source_hashes','input_hashes','opened_products','runtime','protocol_sha256'):
                corrupted=copy.deepcopy(original);corrupted[field]={'tampered':True}
                output.write_bytes(study.legacy.encoded(corrupted))
                with self.subTest(field=field),self.assertRaisesRegex(RuntimeError,'provenance'):
                    study.run(['controls'],[],[study.CONTROL_VARIANTS[1]])
            bad=copy.deepcopy(original);bad['records'][0]['control']['realization_sha256']='different'
            row=bad['records'][0];row.pop('record_sha256');row['record_sha256']=sha256(study.legacy.encoded(row)).hexdigest()
            output.write_bytes(study.legacy.encoded(bad))
            with self.assertRaisesRegex(RuntimeError,'paired control'):study.run(['controls'],[],[study.CONTROL_VARIANTS[1]])
            output.write_bytes(study.legacy.encoded(original));bad=load(output);bad['records'][0]['status']='unknown'
            row=bad['records'][0];row.pop('record_sha256');row['record_sha256']=sha256(study.legacy.encoded(row)).hexdigest()
            with self.assertRaisesRegex(RuntimeError,'terminal status'):study.save(bad)
            bad=copy.deepcopy(original);bad['records'][0]['fit']['position'][0]+=1
            with self.assertRaisesRegex(RuntimeError,'checksum'):study.save(bad)

    def test_geometry_and_realization_reject_mismatched_frame_lists(self):
        with self.assertRaisesRegex(ValueError,'count'):study.control_geometry([{}],[],None)
        with self.assertRaisesRegex(ValueError,'identity'):study.control_geometry([{'obs_id':'a'}],[{'obs_id':'b'}],None)
        with self.assertRaisesRegex(ValueError,'count'):study.realize([{}],[],{},0,0,0)
        with self.assertRaisesRegex(ValueError,'identity'):study.realize([{'obs_id':'a'}],[{'obs_id':'b'}],{},0,0,0)

    def test_design_is_immutable_and_git_bytes_required(self):
        base=study.ROOT/'data/raw/benchmark';base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base,prefix='neighbor-design-test-') as directory:
            root=Path(directory).resolve();assert base.resolve() in root.parents
            source=root/'source.py';source.write_bytes(b'fixed source\n');design=root/'design.json'
            relative=study.legacy.relative(source)
            inventory={'sources':{relative:sha256(source.read_bytes()).hexdigest()},'raw':{},'opened_products':{}}
            with patch.object(study,'DESIGN',design),patch.object(study,'inventory',return_value=inventory):
                study.create_design();snapshot=design.read_bytes()
                with self.assertRaisesRegex(RuntimeError,'exists'):study.create_design()
                self.assertEqual(design.read_bytes(),snapshot)
                blobs={relative:source.read_bytes(),study.legacy.relative(design):snapshot}
                with patch.object(study.subprocess,'check_output',side_effect=lambda args,**kwargs:blobs[args[2].split(':',1)[1]]):
                    study.verify_design();source.write_bytes(b'uncommitted edit\n')
                    with self.assertRaisesRegex(RuntimeError,'uncommitted'):study.verify_design()


if __name__=='__main__':unittest.main()

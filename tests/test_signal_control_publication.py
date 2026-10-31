"""Publication checks use synthetic records; real product checks are optional."""
import copy
from contextlib import ExitStack, redirect_stdout
import gzip
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import publish_signal_controls as publication
from scripts.signal_control_metrics import summarize_signal_control
from tests.test_signal_control_metrics import fixture, index


def sealed_receipt():
    result = {'schema':'signal-control-independent-audit-1', 'status':'passed', 'planned':640,
        'counts':{'verified':639,'input_checked_unavailable':1}, 'failures':[],
        'metric_checks':{'strata':216,'null_strata':8,'pairs':320,'noiseless_clean':128,'noisy_gates':16,'preservation':64},
        'objective_checked':639, 'successful_final_starts_checked':5751,
        'audit_checkpoint_digest':'audit-digest', 'assessment_opened':False, 'promotion':False,
        'identity':{'protocol_commit':publication.COMMIT, 'study_cell_digest':'cells', 'summary_sha256':'summary',
                    'source_sha256':{'audit.py':'hash'}, 'design_sha256':'design', 'upstream':{'sample':'frozen'}}}
    return reseal(result)


def reseal(value):
    value = {k:v for k,v in value.items() if k != 'receipt_sha256'}
    value['receipt_sha256'] = sha256(publication.study.parent.calibration.legacy.encoded(value)).hexdigest()
    return value


def check_receipt(receipt):
    return publication.verify_receipt(receipt, 'cells','summary',{'audit.py':'hash'},'design',{'sample':'frozen'})


class SignalPublicationTests(unittest.TestCase):
    def test_receipt_requires_exact_hash_sources_design_and_640_valid_counts(self):
        good = sealed_receipt(); check_receipt(good)
        corrupt = copy.deepcopy(good); corrupt['planned'] = 639
        with self.assertRaisesRegex(ValueError,'checksum'):check_receipt(corrupt)
        for mutate in (
                lambda r:r.update(status='failed'), lambda r:r.update(assessment_opened=True),
                lambda r:r.update(promotion=True), lambda r:r['identity'].update(design_sha256='other'),
                lambda r:r['identity'].update(upstream={'sample':'other'}),
                lambda r:r['identity'].update(source_sha256={'audit.py':'changed'}),
                lambda r:r.update(counts={'verified':641,'input_checked_unavailable':-1}),
                lambda r:r.update(counts={'verified':639,'input_checked_unavailable':True}),
                lambda r:r.update(counts={'audit_mismatch':1,'verified':639})):
            value = copy.deepcopy(good); mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):check_receipt(reseal(value))

    def test_checkpoints_verify_cell_identity_and_objective_aggregates(self):
        rows = [] ; checked = []
        for i in range(640):
            completed = i != 639
            payload = ({'status':'fit_completed', 'fit':{'final_mode_audit':{'starts':[{'success':True}]*9}}}
                       if completed else {'status':'preparation_failed','error':'ValueError: fixed input',
                                          'failure_stage':'preparation'})
            rows.append({'key':[str(i)],'checksum':str(i),'payload':payload})
            audit = {'status':'verified' if completed else 'input_checked_unavailable', 'study_checksum':str(i),
                     'study_status':payload['status'], 'study_error':payload.get('error'),
                     'objective_available':completed, 'successful_final_starts':9 if completed else 0}
            if not completed: audit.update(replayed_preparation_error=payload['error'], replayed_failure_stage='preparation')
            checked.append({'key':[str(i)], 'payload':audit})
        journal = type('JournalFixture',(),{'records':lambda self,require_complete:checked})()
        receipt = sealed_receipt()
        with patch.object(publication.study.parent.calibration,'record_digest',return_value='audit-digest'):
            self.assertEqual(len(publication.verify_checkpoints(receipt,rows,journal)),640)
            checked[0]['payload']['study_checksum'] = 'tampered'
            with self.assertRaisesRegex(ValueError,'binding'):publication.verify_checkpoints(receipt,rows,journal)
            checked[0]['payload']['study_checksum'] = '0'
            checked[0]['payload']['objective_available'] = False
            with self.assertRaisesRegex(ValueError,'objective status'):publication.verify_checkpoints(receipt,rows,journal)
            checked[0]['payload']['objective_available'] = True
            checked[-1]['payload']['replayed_failure_stage'] = 'geometry_or_realization'
            with self.assertRaisesRegex(ValueError,'failure replay'):publication.verify_checkpoints(receipt,rows,journal)
            checked[-1]['payload']['replayed_failure_stage'] = 'preparation'
            bad = {**receipt,'successful_final_starts_checked':5750}
            with self.assertRaisesRegex(ValueError,'aggregate'):publication.verify_checkpoints(bad,rows,journal)
            checked[0]['payload']['successful_final_starts'] = 8
            with self.assertRaisesRegex(ValueError,'start count'):publication.verify_checkpoints(receipt,rows,journal)

    def test_fidelity_null_and_failures_preserve_denominators(self):
        keys, records = fixture(); values = index(records)
        key = ('noiseless','g0','matched','0','isolated','600','0','corrected')
        values[key].clear(); values[key].update(status='fit_failed',error='synthetic refusal')
        metrics = summarize_signal_control(records,keys)
        with patch.object(publication.study,'expected_keys',return_value=keys):
            fidelity = publication.validate_metrics(metrics,records)
            self.assertEqual(len(fidelity),8);self.assertTrue(all(g['planned']==16 for g in fidelity))
            failed = next(g for g in fidelity if g['truth']=='matched' and g['scene']=='isolated' and g['arm']=='corrected')
            self.assertEqual((failed['planned'],failed['completed'],failed['joint_passed']),(16,15,15))
            null = publication.null_flux_summaries(metrics)
            self.assertEqual(len(null),8)
            self.assertTrue(all(g['planned']==8 and g['signed_flux_jy']['completed']==8 for g in null))
            self.assertTrue(all('detection' not in g and 'position' not in g for g in null))
            bad = copy.deepcopy(metrics); next(r for r in bad['records'] if r['key'][0]=='null')['values']['position_native_error'] = [0,0]
            with self.assertRaisesRegex(ValueError,'null'):publication.validate_metrics(bad,records)
            bad = copy.deepcopy(metrics); bad['noiseless_clean_gate']['planned'] = 127
            with self.assertRaisesRegex(ValueError,'denominators'):publication.validate_metrics(bad,records)
            bad = copy.deepcopy(metrics); bad['records'].pop()
            with self.assertRaisesRegex(ValueError,'planned keys'):publication.validate_metrics(bad,records)

    def test_pack_and_keep_are_deterministic_immutable_and_checksum_bound(self):
        archive = {'schema':'fixture','records':[{'key':['a'], 'payload':{'status':'fit_failed'}}]}
        packed, descriptor = publication.pack_archive(archive)
        self.assertEqual(publication.pack_archive(archive),(packed,descriptor))
        raw = gzip.decompress(packed)
        self.assertEqual(json.loads(raw),archive)
        self.assertEqual(descriptor['sha256'],sha256(packed).hexdigest())
        self.assertEqual(descriptor['uncompressed_sha256'],sha256(raw).hexdigest())
        self.assertEqual((descriptor['bytes'],descriptor['uncompressed_bytes']),(len(packed),len(raw)))
        with tempfile.TemporaryDirectory(dir=publication.study.ROOT) as temp:
            path = Path(temp)/'records.gz';publication.keep(path,packed);publication.keep(path,packed)
            with self.assertRaisesRegex(ValueError,'overwrite'):publication.keep(path,packed+b'wrong')
            self.assertEqual(path.read_bytes(),packed)

    def test_figure_requirements_remain_the_frozen_original(self):
        self.assertEqual(publication.digest(publication.study.ROOT/'requirements-figures.txt'),
                         '6e73d507401a635ca162ca32987d949faf197fec2c6d23e849f46cea8b15c7d3')

    def test_synthetic_end_to_end_publication_replay_and_source_refusal(self):
        keys, records = fixture()
        for i, row in enumerate(records):
            row['checksum'] = str(i)
            row['payload']['fit'] = {'final_mode_audit':{'starts':[{'success':False} for _ in range(9)]}}
        metrics = summarize_signal_control(records,keys)
        checked = [{'key':r['key'], 'payload':{'status':'verified','study_checksum':r['checksum'],
                    'study_status':'fit_completed', 'study_error':None, 'objective_available':True,
                    'successful_final_starts':0}} for r in records]
        requirements = (publication.study.ROOT/'requirements-figures.txt').read_bytes()
        with tempfile.TemporaryDirectory(dir=publication.study.ROOT) as temp, ExitStack() as stack:
            root = Path(temp); output = root/'study'; output.mkdir(); out = root/'public'
            audit_dir = root/'audit'; audit_dir.mkdir(); (audit_dir/'cells').mkdir(); (output/'cells').mkdir()
            for folder in (audit_dir/'cells',output/'cells'): (folder/'header.json').write_text('{}',encoding='utf-8')
            design = root/'design.json'; design.write_text('{}',encoding='utf-8')
            (root/'requirements-figures.txt').write_bytes(requirements)
            source = root/'audit_source.py'; source.write_bytes(b'synthetic audit')
            publisher_source = root/'publisher_source.py'; publisher_source.write_bytes(b'synthetic publisher')
            metadata = {'fixture':'no real data'}
            summary = {'cell_digest':'cells','protocol_commit':publication.COMMIT,
                       'design_sha256':publication.digest(design), 'assessment_opened':False, 'promotion':False,'metrics':metrics}
            summary_path = output/'summary.json';summary_path.write_text(json.dumps(summary),encoding='utf-8')
            receipt = {'schema':'signal-control-independent-audit-1','status':'passed','planned':640,
                'counts':{'verified':640}, 'failures':[], 'objective_checked':640, 'successful_final_starts_checked':0,
                'metric_checks':{'strata':216,'null_strata':8,'pairs':320,'noiseless_clean':128,'noisy_gates':16,'preservation':64},
                'audit_checkpoint_digest':'audit-digest', 'assessment_opened':False, 'promotion':False,
                'identity':{'protocol_commit':publication.COMMIT, 'study_cell_digest':'cells',
                    'summary_sha256':publication.digest(summary_path), 'source_sha256':{'audit_source.py':publication.digest(source)},
                    'design_sha256':publication.digest(design), 'upstream':metadata}}
            receipt = reseal(receipt)
            (audit_dir/'audit-receipt.json').write_text(json.dumps(receipt),encoding='utf-8')
            journal = type('StudyJournal',(),{'directory':output/'cells', 'records':lambda self,require_complete:records})()
            audit = type('AuditJournal',(),{'directory':audit_dir/'cells', 'records':lambda self,require_complete:checked})()
            stack.enter_context(patch.object(publication.study,'ROOT',root))
            stack.enter_context(patch.object(publication.study,'DESIGN',design))
            stack.enter_context(patch.object(publication.study,'OUTPUT',output))
            stack.enter_context(patch.object(publication,'PUBLIC',out))
            stack.enter_context(patch.object(publication,'AUDIT_DIR',audit_dir))
            stack.enter_context(patch.object(publication,'AUDIT_SOURCES',('audit_source.py',)))
            stack.enter_context(patch.object(publication,'PUBLISHER_SOURCES',('publisher_source.py',)))
            stack.enter_context(patch.object(publication.study,'expected_keys',return_value=keys))
            stack.enter_context(patch.object(publication.study,'open_inputs',return_value=(None,None,metadata)))
            stack.enter_context(patch.object(publication.study,'open_journal',return_value=journal))
            stack.enter_context(patch.object(publication.study.parent,'assert_assessment_unopened'))
            stack.enter_context(patch.object(publication.study.parent.frozen,'verify',return_value={'metadata':metadata}))
            stack.enter_context(patch.object(publication.study.parent.calibration,'record_digest',
                side_effect=lambda obj,rows:'cells' if obj is journal else 'audit-digest'))
            stack.enter_context(patch.object(publication,'Journal',return_value=audit))
            def fake_figure(rows,path):
                publication.keep(path,b'synthetic figure');return {'record_checksums':[rows[0]['checksum'],rows[1]['checksum']]}
            stack.enter_context(patch.object(publication,'example',side_effect=fake_figure))
            stack.enter_context(redirect_stdout(io.StringIO()))
            overview = publication.run(); replayed = publication.run()
            self.assertEqual(overview,replayed);self.assertEqual(overview['planned'],640)
            packed = (out/'records.json.gz').read_bytes(); archive = json.loads(gzip.decompress(packed))
            self.assertEqual(len(archive['records']),640);self.assertEqual(len(archive['audit_records']),640)
            self.assertEqual(sha256(packed).hexdigest(),overview['download']['sha256'])
            self.assertEqual(overview['publisher_source_sha256']['publisher_source.py'],publication.digest(publisher_source))
            source.write_bytes(b'changed after audit')
            with self.assertRaisesRegex(ValueError,'does not bind'):publication.run()

    @unittest.skipUnless((publication.PUBLIC/'overview.json').is_file(),'published product not present yet')
    def test_optional_published_product_source_and_archive_hashes(self):
        overview = json.loads((publication.PUBLIC/'overview.json').read_text(encoding='utf-8'))
        design = json.loads(publication.study.DESIGN.read_text(encoding='utf-8'))
        for path, expected in design['sources'].items():
            self.assertEqual(publication.digest(publication.study.ROOT/path),expected)
        for field in ('publisher_source_sha256','audit_source_sha256'):
            for path, expected in overview[field].items():
                self.assertEqual(publication.digest(publication.study.ROOT/path),expected)
        packed = (publication.PUBLIC/'records.json.gz').read_bytes();raw = gzip.decompress(packed)
        self.assertEqual(sha256(packed).hexdigest(),overview['download']['sha256'])
        self.assertEqual(sha256(raw).hexdigest(),overview['download']['uncompressed_sha256'])
        self.assertEqual(publication.digest(publication.study.ROOT/'requirements-figures.txt'), publication.FIGURE_REQUIREMENTS_SHA256)

    @unittest.skipUnless((publication.PUBLIC/'overview.json').is_file(),'published product not present yet')
    def test_optional_published_archive_all_records_and_figure(self):
        from collections import Counter
        from PIL import Image
        from scripts.science_jobs import encode
        overview = json.loads((publication.PUBLIC/'overview.json').read_text(encoding='utf-8'))
        archive = json.loads(gzip.decompress((publication.PUBLIC/'records.json.gz').read_bytes()))
        expected = [list(k) for k in publication.study.expected_keys()]
        encoded = publication.study.parent.calibration.legacy.encoded
        for header_name, records_name, digest_name in (
                ('journal_header','records','cell_digest'),
                ('audit_journal_header','audit_records','audit_checkpoint_digest')):
            header = archive[header_name]; records = archive[records_name]
            self.assertEqual(header['expected_keys'],expected)
            self.assertEqual([r['key'] for r in records],expected)
            self.assertEqual(sha256(encode({k:v for k,v in header.items() if k!='checksum'})).hexdigest(),header['checksum'])
            self.assertEqual(sha256(encode(header['identity'])).hexdigest(),header['identity_sha256'])
            for record in records:
                self.assertEqual(record['identity_sha256'],header['identity_sha256'])
                self.assertEqual(sha256(encode({k:v for k,v in record.items() if k!='checksum'})).hexdigest(),record['checksum'])
            body = {'header_sha256':sha256(encode(header)).hexdigest(),
                    'records':[{'key':r['key'],'checksum':r['checksum']} for r in records]}
            self.assertEqual(sha256(encoded(body)).hexdigest(),archive[digest_name])
        self.assertEqual(Counter(r['payload']['status'] for r in archive['records']),overview['status_counts'])
        for original, checked in zip(archive['records'],archive['audit_records']):
            self.assertEqual(checked['payload']['study_checksum'],original['checksum'])
            self.assertEqual(checked['payload']['study_status'],original['payload']['status'])
        figure = publication.study.ROOT/'web'/overview['figure']['path']
        self.assertEqual(publication.digest(figure),overview['figure']['sha256'])
        with Image.open(figure) as image:self.assertEqual(image.size,(1560,1014))
        self.assertIs(overview['assessment_opened'],False)
        self.assertIs(overview['promotion'],False)
        self.assertEqual(overview['prospective_fields_opened'],0)
        self.assertFalse((publication.study.ROOT/'data/raw/benchmark/shape-point-check/assessment').exists())


if __name__ == '__main__': unittest.main()

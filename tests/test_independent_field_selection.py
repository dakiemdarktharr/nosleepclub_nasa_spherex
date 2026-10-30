import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from scripts import select_independent_fields as selection


def exclusion(ra,dec):
    return {'path':'data/raw/synthetic/manifest.json','sha256':'1'*64,
            'centers':[{'ra_deg':ra,'dec_deg':dec,'json_pointers':['/field/{ra,dec}']}]}


class FieldSelectionTests(unittest.TestCase):
    def test_deterministic_split_and_first_valid_offset(self):
        manifests=[exclusion(150.,45.),exclusion(269.45207695861876,4.693364966576667)]
        a=selection.select(manifests,'a'*64);b=selection.select(manifests,'a'*64)
        self.assertEqual(a,b);self.assertEqual(a['chosen_ra_offset_deg'],10)
        self.assertEqual([x['offset_deg'] for x in a['rejected_offsets']],list(range(10)))
        self.assertEqual(len(a['fields']),30)
        for dec in [-45,0,45]:
            ring=[v for v in a['fields'] if v['dec_deg']==dec]
            self.assertEqual([v['role'] for v in ring],['calibration']*4+['validation']*4+['final_holdout']*2)
            self.assertEqual([v['split_sha256'] for v in ring],sorted(v['split_sha256'] for v in ring))
            for v in ring:self.assertEqual(v['split_sha256'],hashlib.sha256((selection.SALT+'|'+v['id']).encode()).hexdigest())
        self.assertEqual({role:sum(v['role']==role for v in a['fields']) for role in ['calibration','validation','final_holdout']},
                         {'calibration':12,'validation':12,'final_holdout':6})
        self.assertGreaterEqual(a['nearest_cached_center']['distance_deg'],6.)
        self.assertGreater(a['nearest_new_field_pair']['distance_deg'],6.)

    def test_great_circle_wrap_and_threshold_rules(self):
        self.assertAlmostEqual(selection.separation_deg(359.5,0.,.5,0.),1.,places=10)
        self.assertAlmostEqual(selection.separation_deg(0,90,180,-90),180.,places=10)
        field=[{'id':'r000p00','ra_deg':0,'dec_deg':0}]
        self.assertFalse(selection.separation_conflicts(field,[exclusion(6.,0.)]))
        self.assertTrue(selection.separation_conflicts(field,[exclusion(5.9999,0.)]))
        second={'id':'r006p00','ra_deg':6,'dec_deg':0}
        conflicts=selection.separation_conflicts([field[0],second],[exclusion(100.,0.)])
        self.assertTrue(any(v['kind']=='candidate_pair' for v in conflicts))

    def test_no_valid_offset_fails_without_silent_replacement(self):
        manifest=exclusion(12.,-45.);manifest['centers']=[{'ra_deg':(12+i)%360,'dec_deg':-45.,'json_pointers':['/field/{ra,dec}']} for i in range(36)]
        with self.assertRaisesRegex(ValueError,'No global RA offset'):selection.select([manifest],'a'*64)

    def test_manifest_discovery_and_write_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw=root/'data/raw';p=raw/'science/manifest.json';p.parent.mkdir(parents=True)
            p.write_text(json.dumps({'field':{'ra':150.,'dec':45.},'records':[{'cutout_center_ra':150.,'cutout_center_dec':45.}]}),encoding='utf-8')
            job=raw/'jobs/a/manifest.json';job.parent.mkdir(parents=True);job.write_text(json.dumps({'field':'x'}),encoding='utf-8')
            evidence=selection.discover_manifests(raw,root)
            self.assertEqual(len(evidence),1);self.assertEqual(len(evidence[0]['centers']),1)
            self.assertEqual(len(evidence[0]['centers'][0]['json_pointers']),2)
            self.assertEqual(evidence[0]['sha256'],hashlib.sha256(p.read_bytes()).hexdigest())
            result=selection.select(evidence,'a'*64);out=root/'selection.json'
            self.assertTrue(selection.write_once(out,result));before=out.read_bytes()
            self.assertFalse(selection.write_once(out,result));self.assertEqual(out.read_bytes(),before)
            with self.assertRaises(FileExistsError):selection.write_once(out,{**result,'status':'different'})
            self.assertEqual(out.read_bytes(),before)
            p.write_text(json.dumps({'records':[{'cutout_center_ra':150.}]}),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'partial direction'):selection.discover_manifests(raw,root)

    def test_query_guard_requires_committed_exact_source_and_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);script=root/'scripts/select_independent_fields.py';script.parent.mkdir(parents=True);script.write_bytes(b'sealed source\n')
            out=root/'web/data/independent-fields/selection.json';evidence=[exclusion(150.,45.)]
            product=selection.select(evidence,selection.digest(script));selection.write_once(out,product)
            def git_show(argv,**kwargs):
                name=argv[-1].removeprefix('HEAD:');return (root/name).read_bytes()
            with patch.object(selection,'ROOT',root),patch.object(selection,'SCRIPT',script),patch.object(selection,'discover_manifests',return_value=evidence),patch.object(selection.subprocess,'check_output',side_effect=git_show):
                self.assertTrue(selection.verify_before_metadata_query(out)['verified'])
                with patch.object(selection.subprocess,'check_output',return_value=b'uncommitted'):
                    with self.assertRaisesRegex(ValueError,'Uncommitted changes'):selection.verify_before_metadata_query(out)
                with patch.object(selection.subprocess,'check_output',side_effect=subprocess.CalledProcessError(128,'git')):
                    with self.assertRaisesRegex(ValueError,'not committed'):selection.verify_before_metadata_query(out)
                with patch.object(selection,'discover_manifests',return_value=[exclusion(160.,45.)]):
                    with self.assertRaisesRegex(ValueError,'evidence changed'):selection.verify_before_metadata_query(out)

    def test_product_source_geometry_and_optional_local_evidence(self):
        path=selection.OUT
        if not path.exists():self.skipTest('Selection artifact has not been generated')
        value=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(value['stage'],'field_selection_only')
        self.assertEqual(value['source_sha256'],selection.digest(selection.SCRIPT))
        self.assertEqual(value,selection.select(value['exclusion_manifests'],selection.digest(selection.SCRIPT)))
        self.assertFalse(selection.separation_conflicts(value['fields'],value['exclusion_manifests']))
        for entry in value['exclusion_manifests']:
            p=selection.ROOT/entry['path']
            if p.exists():self.assertEqual(entry['sha256'],selection.digest(p))
        if selection.RAW.is_dir() and all((selection.ROOT/e['path']).exists() for e in value['exclusion_manifests']):
            self.assertEqual(value['exclusion_manifests'],selection.discover_manifests())


if __name__=='__main__':unittest.main()

"""Reject untrusted selectors, stale provenance, and cross-origin writes."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('review_api',Path(__file__).resolve().parents[1]/'web/api/reviews.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)


class ReviewValidation(unittest.TestCase):
    def item(self):
        m=api.manifest()
        return dict(scene_id=m['scenes'][0]['id'],selection='target',status='uncertain',note='QA',analysis_sha256=m['analysis_sha256'])

    def test_payload_cannot_choose_database_fields_or_provenance(self):
        item=self.item();item.update(owner='someone_else',input_sha256=['forged'],target_detection=True)
        validated=api.validate_review(item)
        self.assertNotIn('owner',validated)
        self.assertNotEqual(validated['input_sha256'],['forged'])
        self.assertEqual(validated['target_detection'],api.manifest()['scenes'][0]['target_detection'])

    def test_rejects_operators_stale_hash_unknown_selection_and_oversized_note(self):
        for field,value in [('scene_id',{'$ne':None}),('analysis_sha256','old'),('selection','unknown'),('note','x'*2001),('status',{'$gt':''})]:
            item=self.item();item[field]=value
            with self.assertRaises((ValueError,TypeError)):api.validate_review(item)

    def test_same_origin_requires_https_exact_host(self):
        self.assertTrue(api.same_origin({'Origin':'https://demo.vercel.app','Host':'demo.vercel.app'}))
        for origin in ['https://evil.example','https://demo.vercel.app.evil.example','null','http://demo.vercel.app','']:
            self.assertFalse(api.same_origin({'Origin':origin,'Host':'demo.vercel.app'}))

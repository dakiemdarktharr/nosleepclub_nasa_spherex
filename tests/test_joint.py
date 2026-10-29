"""Numerical deblending controls independent of the real WISE target."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
import numpy as np
from scripts import joint_motion as joint
from tests.test_motion import synthetic_frame


class JointControls(unittest.TestCase):
    def test_joint_recovers_centroid_in_blend_with_free_fluxes_and_plane(self):
        motion=joint.motion;anchor=np.array([31.5,31.5]);truth=anchor+[.2,-.12]
        neighbour=anchor+[1.8,.6];samples=[]
        for i,offset in enumerate([(.2,-.3),(-.35,.15)]):
            f=synthetic_frame(offset);f['record']['obs_id']=str(i)
            yy,xx=np.indices((64,64))
            f['data']=motion.render_source(f,truth,4+i)+motion.render_source(f,neighbour,7-i)+.01*xx-.02*yy+2
            s=motion.native_stamp(f,anchor)
            samples.append(joint.prepare(s,[('neighbour',neighbour)]))
        fitted=joint.fit(samples,anchor)
        self.assertTrue(fitted['success']);self.assertFalse(fitted['at_boundary'])
        np.testing.assert_allclose(fitted['position'],truth,atol=3e-4)
        self.assertGreater(np.linalg.norm(joint.fit([joint.prepare(s) for s in samples],anchor)['position']-truth),.3)

    def test_svd_handles_duplicate_nuisance_columns(self):
        motion=joint.motion;f=synthetic_frame();anchor=np.array([31.5,31.5]);neighbour=anchor+[2,1]
        f['data']=motion.render_source(f,anchor,5)+motion.render_source(f,neighbour,8)
        s=joint.prepare(motion.native_stamp(f,anchor),[('one',neighbour),('duplicate',neighbour)])
        self.assertEqual(s['rank'],4)
        np.testing.assert_allclose(joint.fit([s],anchor)['position'],anchor,atol=3e-4)

    def test_published_protocol_and_source_are_reproducible(self):
        root=Path(__file__).resolve().parents[1]
        for path in [root/'web/data/joint'/f'{name}.json' for name in ['broad','strict']]:
            payload=json.loads(path.read_text())
            self.assertEqual(payload['source_sha256'],sha256(Path(joint.__file__).read_bytes()).hexdigest())
            self.assertEqual(payload['protocol'],joint.CONFIG)
            records=payload['result']['records']
            self.assertEqual(len(records),96)
            for model in ['single','joint']:
                self.assertEqual(sum(r['model']==model for r in records),48)

    def test_paired_summary_hashes_and_denominators_match(self):
        from scripts import summarize_joint
        root=Path(__file__).resolve().parents[1]/'web/data/joint'
        summary=json.loads((root/'summary.json').read_text())
        self.assertEqual(summary['source_sha256'],sha256(Path(summarize_joint.__file__).read_bytes()).hexdigest())
        for name,digest in summary['input_sha256'].items():
            self.assertEqual(digest,sha256((root/name).read_bytes()).hexdigest())
        for config in summary['configurations']:
            self.assertTrue(all(0<g['common_valid_pairs']<=24 for g in config['groups']))


if __name__=='__main__':unittest.main()

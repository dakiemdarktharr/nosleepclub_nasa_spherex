"""Publication refuses mismatched audit/source/journal seals and overwritten bytes."""
import copy
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from scripts import publish_profile_landscape as pub
from scripts.experiment_journal import Journal


def sealed(value):
    value = copy.deepcopy(value);value.pop('receipt_sha256', None)
    return {**value, 'receipt_sha256': sha256(pub.study.calibration.legacy.encoded(value)).hexdigest()}


class LandscapePublicationTests(unittest.TestCase):
    def test_only_exact_passed_audit_can_publish(self):
        meta = {'baseline_journal_digest': 'old', 'point_journal_digest': 'point'}; sources = {'audit.py': 'code'}
        receipt = sealed({'schema': 'profile-landscape-independent-audit-1', 'status': 'passed', 'planned': 112,
            'promotion': False, 'assessment_opened': False, 'new_position_fits': 0, 'new_noise_draws': 0,
            'failures': [], 'counts': {'verified': 96, 'verified_unavailable': 16},
            'identity': {'profile_commit': pub.auditor.COMMIT, 'profile_journal_digest': 'cells',
                'source_sha256': sources, **meta}})
        pub.verify_audit(receipt, 'cells', meta, sources)
        for mutation in ('status', 'source', 'point', 'cells', 'failure', 'count', 'assessment', 'checksum'):
            bad = copy.deepcopy(receipt)
            if mutation == 'status': bad['status'] = 'findings_or_unverified'
            if mutation == 'source': bad['identity']['source_sha256']['audit.py'] = 'changed'
            if mutation == 'point': bad['identity']['point_journal_digest'] = 'changed'
            if mutation == 'cells': bad['identity']['profile_journal_digest'] = 'changed'
            if mutation == 'failure': bad['failures'] = [{'key': ['bad']}]
            if mutation == 'count': bad['counts']['verified'] = 95
            if mutation == 'assessment': bad['assessment_opened'] = True
            if mutation != 'checksum': bad = sealed(bad)
            else: bad['receipt_sha256'] = 'wrong'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): pub.verify_audit(bad, 'cells', meta, sources)

    def test_existing_product_cannot_be_silently_replaced(self):
        with tempfile.TemporaryDirectory(dir=pub.study.ROOT) as temp:
            path = Path(temp)/'product'; pub.keep(path, b'original'); pub.keep(path, b'original')
            with self.assertRaises(ValueError): pub.keep(path, b'changed')
            self.assertEqual(path.read_bytes(), b'original')

    def test_missing_corrupt_or_unbound_audit_checkpoint_refuses_publication(self):
        for corruption in ('none', 'deleted', 'corrupt', 'unbound', 'receipt_summary'):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory(dir=pub.study.ROOT) as temp:
                keys = [('s', 'e', 'baseline', 'baseline')]
                profile = [{'key': list(keys[0]), 'checksum': 'profile-1', 'payload': {'status': 'profile_completed'}}]
                audit = Journal(Path(temp), {'synthetic': 1}, keys, ('verified',))
                audit.write(keys[0], {'status': 'verified', 'profile_checksum': 'profile-1',
                    'profile_status': 'profile_completed', 'checks': {'sampled_grid_nodes': 25},
                    'max_absolute_differences': {'grid_cost': 1e-12}})
                receipt = {'audit_cell_digest': pub.study.calibration.record_digest(audit, audit.records(require_complete=True)),
                    'counts': {'verified': 1}, 'verification_counts': {'sampled_grid_nodes': 25},
                    'max_absolute_differences': {'grid_cost': 1e-12}}
                if corruption == 'deleted': audit._record_path(keys[0]).unlink()
                if corruption == 'corrupt': audit._record_path(keys[0]).write_bytes(b'{"checksum":"bad"}')
                if corruption == 'unbound': profile[0]['checksum'] = 'changed'
                if corruption == 'receipt_summary': receipt['verification_counts']['sampled_grid_nodes'] = 24
                if corruption == 'none': self.assertEqual(len(pub.verify_audit_cells(receipt, profile, audit)), 1)
                else:
                    with self.assertRaises(ValueError): pub.verify_audit_cells(receipt, profile, audit)


if __name__ == '__main__': unittest.main()

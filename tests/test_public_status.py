from unittest import TestCase
from unittest.mock import patch
from web.api import status


class PublicStatusTests(TestCase):
    def setUp(self):
        status._snapshot = None
        status._expires = 0

    def test_probe_is_coalesced_and_limited_to_one_public_asset(self):
        manifest = {'assets': {'data/manifest.json': {'chunks': [{'sha256': 'a'*64, 'bytes': 2}]}}}
        with patch.object(status, 'manifest', return_value=manifest), patch.object(status, 'read_chunk') as read:
            first = status.snapshot()
            second = status.snapshot()
        self.assertEqual(first['public_data'], 'available')
        self.assertEqual(first['irsa'], 'not_checked')
        self.assertEqual(first['reviews'], 'not_checked')
        self.assertIs(first, second)
        self.assertEqual(read.call_count, 1)

    def test_failure_does_not_expose_diagnostics_or_claim_other_services_healthy(self):
        with patch.object(status, 'manifest', side_effect=RuntimeError('mongodb://secret')):
            result = status.snapshot()
        self.assertEqual(result['public_data'], 'unavailable')
        self.assertNotIn('secret', repr(result))
        self.assertEqual(result['reviews'], 'not_checked')

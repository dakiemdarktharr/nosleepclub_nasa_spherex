"""Verify log severity and that diagnostic allowlists cannot copy private input."""
from io import StringIO
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from web.api import _telemetry as telemetry


class TelemetryTests(unittest.TestCase):
    def test_success_and_failures_have_distinct_levels_and_streams(self):
        stdout, stderr = StringIO(), StringIO()
        with patch.object(telemetry.sys, 'stdout', stdout), patch.object(telemetry.sys, 'stderr', stderr):
            logger = telemetry.request_logger('telemetry-test-' + uuid4().hex)
            self.addCleanup(lambda: [logger.removeHandler(h) for h in list(logger.handlers)])
            self.assertIs(telemetry.request_logger(logger.name), logger)
            self.assertEqual(len(logger.handlers), 2)
            for status in (200, 400, 502):
                telemetry.emit_request(logger, {'event': 'frame_request', 'request_id': 'a' * 32,
                                               'category': 'ok', 'status': status, 'latency_ms': 1.25})
        success = [json.loads(line) for line in stdout.getvalue().splitlines()]
        failed = [json.loads(line) for line in stderr.getvalue().splitlines()]
        self.assertEqual([(x['status'], x['level']) for x in success], [(200, 'info')])
        self.assertEqual([(x['status'], x['level']) for x in failed], [(400, 'warning'), (502, 'error')])

    def test_private_and_invalid_diagnostic_fields_are_not_logged(self):
        event = {'event': 'frame_request', 'request_id': 'b' * 32, 'category': 'upstream_or_fits',
                 'status': 502, 'latency_ms': 2, 'error_code': 'upstream_http_error',
                 'upstream_http_status': 503, 'method': ['secret'], 'note': 'private-review',
                 'url': 'https://secret.example', 'cookie': 'private-cookie', 'ip': '127.0.0.1'}
        with patch.object(telemetry, 'logging') as logging:
            logging.ERROR, logging.WARNING, logging.INFO = 40, 30, 20
            logging.getLevelName.return_value = 'ERROR'
            telemetry.emit_request(logging, event)
            logged = json.loads(logging.log.call_args.args[1])
            self.assertEqual(set(logged), {'event', 'request_id', 'category', 'status', 'latency_ms',
                                          'level', 'error_code', 'upstream_http_status'})
            self.assertEqual(logged['upstream_http_status'], 503)
            self.assertNotIn('private', json.dumps(logged))
            logging.reset_mock()
            for bad in (None, {'event': {}}, {**event, 'request_id': 'bad\nsecret'},
                        {**event, 'latency_ms': float('nan')}, {**event, 'status': True}):
                telemetry.emit_request(logging, bad)
            logging.log.assert_not_called()


if __name__ == '__main__':
    unittest.main()

from types import SimpleNamespace
import unittest

import requests
from urllib3.exceptions import ReadTimeoutError
from scripts.verify_public_data import check_headers, get


class Raw:
    def __init__(self, failure=False):
        self.failure = failure

    def read(self, *args, **kwargs):
        if self.failure:
            raise ReadTimeoutError(None, '/public', 'test-only timeout')
        return b'public'


class PublicTransferTest(unittest.TestCase):
    def test_connection_and_partial_body_timeouts_retained_then_retried(self):
        for mode in ('connect', 'read'):
            records = []; closed = []; calls = []
            def request(*args, **kwargs):
                calls.append(1)
                if len(calls) == 1 and mode == 'connect':
                    raise requests.ConnectionError('test-only failure')
                return SimpleNamespace(status_code=200, headers={}, raw=Raw(len(calls) == 1),
                                       close=lambda: closed.append(1))
            _, payload = get(SimpleNamespace(get=request), '/api/data?path=data/control', records)
            self.assertEqual(payload, b'public')
            self.assertEqual(len(calls), 2)
            self.assertIn('transport_error', records[0])
            self.assertEqual(records[1]['attempt'], 2)
            self.assertEqual(len(closed), 1 if mode == 'connect' else 2)

    def test_no_unbounded_retry(self):
        records = []
        def fail(*args, **kwargs):
            raise requests.Timeout('test-only failure')
        with self.assertRaises(RuntimeError):
            get(SimpleNamespace(get=fail), '/api/data', records)
        self.assertEqual([r['attempt'] for r in records], [1, 2])

    def test_browser_encoding_and_type_match_even_when_raw_bytes_match(self):
        entry = {'content_type': 'application/json; charset=utf-8', 'encoding': 'gzip'}
        for headers in ({'Content-Type': 'application/json'},
                        {'Content-Type': 'application/json', 'Content-Encoding': 'br'},
                        {'Content-Type': 'text/html', 'Content-Encoding': 'gzip'}):
            with self.assertRaises(RuntimeError):
                check_headers(SimpleNamespace(headers=headers), entry)
        check_headers(SimpleNamespace(headers={'Content-Type': 'application/json', 'Content-Encoding': 'gzip'}), entry)
        check_headers(SimpleNamespace(headers={'Content-Type': 'application/octet-stream'}), entry, chunk=True)


if __name__ == '__main__':
    unittest.main()

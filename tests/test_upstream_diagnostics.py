"""Offline upstream classification, isolation and response-contract tests."""
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPException, IncompleteRead
from io import BytesIO
import json
import logging
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from web.api import _upstream_diagnostics as diagnostic
from tests import test_frame_api as frame_tests
from tests import test_observations_api as observation_tests


SECRET = 'private-token-do-not-log'
REQUEST_ID = 'a'*32


class UpstreamDiagnosticTests(unittest.TestCase):
    def test_helper_imports_in_isolated_serverless_api_directory(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            shutil.copytree(root/'web/api', directory/'api', ignore=shutil.ignore_patterns('__pycache__'))
            program = '''
import sys
sys.path.insert(0, sys.argv[1])
from api import observations, frame, _upstream_diagnostics
assert observations.describe_upstream is _upstream_diagnostics.describe
assert frame.describe_upstream is _upstream_diagnostics.describe
assert not __import__('pathlib').Path('web').exists()
'''
            subprocess.run([sys.executable, '-I', '-c', program, str(directory)], cwd=directory,
                           check=True, capture_output=True, text=True)

    def test_known_direct_nested_cycle_and_bounded_unknown_classes(self):
        pairs = [(socket.gaierror(SECRET), 'dns_error'),
                 (ssl.SSLCertVerificationError(SECRET), 'tls_certificate_error'),
                 (ssl.SSLError(SECRET), 'tls_error'), (TimeoutError(SECRET), 'timeout'),
                 (ConnectionResetError(SECRET), 'connection_reset'),
                 (ConnectionRefusedError(SECRET), 'connection_refused'),
                 (IncompleteRead(b'x'), 'incomplete_read'), (HTTPException(SECRET), 'http_exception')]
        for exc, kind in pairs:
            with self.subTest(kind=kind):
                self.assertEqual(diagnostic.describe(exc, 'open')['exception_class'], kind)
                nested = diagnostic.describe(URLError(URLError(exc)), 'read')
                self.assertEqual(nested['reason_class'], kind)
                self.assertNotIn(SECRET, json.dumps(nested))
        loop = URLError('x');loop.reason = loop
        self.assertEqual(diagnostic.describe(loop, 'open')['reason_class'], 'cycle')
        deep = URLError(URLError(URLError(URLError(URLError(OSError(SECRET))))))
        self.assertEqual(diagnostic.describe(deep, 'open')['reason_class'], 'depth_limit')
        self.assertEqual(diagnostic.describe(URLError(SECRET), 'open')['reason_class'], 'other')
        nested_http = diagnostic.describe(URLError(HTTPError('https://example.invalid/'+SECRET, 503, SECRET, {}, BytesIO())), 'open')
        self.assertEqual((nested_http['reason_class'], nested_http['upstream_http_status']), ('http_error', 503))
        self.assertNotIn(SECRET, json.dumps(nested_http))

    def test_emit_allowlist_privacy_and_broken_logger(self):
        class CapturingLogger:
            def __init__(self):self.events = []
            def error(self, message):self.events.append(json.loads(message))
        logger = CapturingLogger()
        payload = diagnostic.describe(URLError(ssl.SSLError(SECRET)), 'open')
        payload['message'] = SECRET;payload['extra'] = {'url': SECRET}
        diagnostic.emit(logger, 'frame', REQUEST_ID, payload)
        self.assertEqual(logger.events, [{'schema': 'upstream-diagnostic-1', 'event': 'upstream_diagnostic',
            'endpoint': 'frame', 'request_id': REQUEST_ID, 'stage': 'open',
            'exception_class': 'url_error', 'reason_class': 'tls_error'}])
        self.assertNotIn(SECRET, json.dumps(logger.events))
        diagnostic.emit(logger, SECRET, REQUEST_ID, payload)
        diagnostic.emit(logger, 'frame', SECRET, payload)
        diagnostic.emit(logger, 'frame', REQUEST_ID, {'stage': SECRET, 'exception_class': SECRET})
        self.assertEqual(len(logger.events), 1)
        class Broken:
            def error(self, message):raise RuntimeError(SECRET)
        self.assertIsNone(diagnostic.emit(Broken(), 'frame', REQUEST_ID, payload))

    def test_fetch_classification_stages_and_unmodified_codes(self):
        obs = observation_tests.api;frame = frame_tests.api
        obs_url = obs.upstream_url(obs.parse_params('ra=350&dec=35'))
        frame_url = frame.cutout_url(frame_tests.parameters())
        for api, url, exc, code, kind in (
            (obs, obs_url, URLError(socket.gaierror(SECRET)), 'upstream_unavailable', 'dns_error'),
            (obs, obs_url, URLError(TimeoutError(SECRET)), 'upstream_timeout', 'timeout'),
            (frame, frame_url, URLError(ssl.SSLCertVerificationError(SECRET)), 'upstream_unavailable', 'tls_certificate_error'),
            (frame, frame_url, ConnectionResetError(SECRET), 'upstream_unavailable', None)):
            with self.subTest(code=code, kind=kind), patch.object(api, 'build_opener') as opener:
                opener.return_value.open.side_effect = exc
                with self.assertRaises((obs.UpstreamError, frame.FrameError)) as caught:api.fetch(url)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(caught.exception.diagnostic['stage'], 'open')
                if kind:self.assertEqual(caught.exception.diagnostic['reason_class'], kind)
                else:self.assertEqual(caught.exception.diagnostic['exception_class'], 'connection_reset')
                self.assertEqual(opener.return_value.open.call_count, 1)
        for api, url in ((obs, obs_url), (frame, frame_url)):
            with self.subTest(api=api.__name__), patch.object(api, 'build_opener') as opener:
                opener.return_value.open.side_effect = HTTPError(url, 302, SECRET, {}, BytesIO())
                with self.assertRaises((obs.UpstreamError, frame.FrameError)) as caught:api.fetch(url)
                self.assertEqual(caught.exception.code, 'upstream_http_error')
                self.assertEqual(caught.exception.diagnostic['upstream_http_status'], 302)
                self.assertEqual(caught.exception.diagnostic['exception_class'], 'http_error')
        class Stream:
            headers = {}
            def __enter__(self):return self
            def __exit__(self, *args):pass
            def read1(self, size):raise IncompleteRead(SECRET.encode())
        with patch.object(frame, 'build_opener') as opener:
            opener.return_value.open.return_value = Stream()
            with self.assertRaises(frame.FrameError) as caught:frame.fetch(frame_url)
        self.assertEqual(caught.exception.code, 'upstream_unavailable')
        self.assertEqual(caught.exception.diagnostic['stage'], 'read')
        self.assertEqual(caught.exception.diagnostic['exception_class'], 'incomplete_read')
        class BadHeaders(Stream):
            @property
            def headers(self):raise ConnectionResetError(SECRET)
        with patch.object(frame, 'build_opener') as opener:
            opener.return_value.open.return_value = BadHeaders()
            with self.assertRaises(frame.FrameError) as caught:frame.fetch(frame_url)
        self.assertEqual(caught.exception.diagnostic['stage'], 'headers')

    def test_handlers_emit_redacted_error_and_keep_original_status(self):
        obs = observation_tests.api;frame = frame_tests.api
        with patch.object(obs, 'build_opener') as opener:
            opener.return_value.open.side_effect = URLError(socket.gaierror(SECRET))
            with self.assertLogs(obs.logger, level='ERROR') as logs:
                status, _, body = observation_tests.request('/api/observations?ra=350&dec=35')
        self.assertEqual((status, body['error']), (502, 'upstream_unavailable'))
        events = [json.loads(record.getMessage()) for record in logs.records]
        event = next(x for x in events if x['event'] == 'upstream_diagnostic')
        request = next(x for x in events if x['event'] == 'observations_request')
        self.assertEqual((event['stage'], event['reason_class']), ('open', 'dns_error'))
        self.assertEqual(request['error_code'], 'upstream_unavailable')
        self.assertEqual(event['request_id'], request['request_id'])
        self.assertNotIn(SECRET, json.dumps(events))
        path = '/api/frame?'+urlencode({'url': frame_tests.URL, 'ra': 350, 'dec': 35, 'fov_deg': .005})
        with patch.object(frame, 'fetch', return_value=b'bad FITS'), self.assertLogs(frame.logger, level='ERROR') as logs:
            status, _, body = frame_tests.request(path)
        self.assertEqual((status, json.loads(body)['error']), (502, 'invalid_fits'))
        events = [json.loads(record.getMessage()) for record in logs.records]
        self.assertEqual(next(x for x in events if x['event'] == 'upstream_diagnostic')['stage'], 'parse')
        self.assertNotIn(frame_tests.URL, json.dumps(events))
        with patch.object(obs, 'fetch', return_value=b'not xml'), self.assertLogs(obs.logger, level='ERROR') as logs:
            status, _, body = observation_tests.request('/api/observations?ra=350&dec=35')
        self.assertEqual((status, body['error']), (502, 'upstream_invalid_xml'))
        self.assertEqual(json.loads(logs.records[0].getMessage())['stage'], 'parse')

    def test_body_limit_and_observations_http_exception_preserve_contract(self):
        obs = observation_tests.api;frame = frame_tests.api
        class LargeStream:
            headers = {}
            def __init__(self):self.body = BytesIO(b'123456')
            def __enter__(self):return self
            def __exit__(self, *args):pass
            def read1(self, size):return self.body.read(size)
        for api, url in ((obs, obs.upstream_url(obs.parse_params('ra=350&dec=35'))),
                         (frame, frame.cutout_url(frame_tests.parameters()))):
            with self.subTest(api=api.__name__), patch.object(api, 'build_opener') as opener, patch.object(api, 'MAX_BYTES', 4):
                opener.return_value.open.return_value = LargeStream()
                with self.assertRaises((obs.UpstreamError, frame.FrameError)) as caught:api.fetch(url)
                self.assertEqual(caught.exception.code, 'upstream_too_large')
                self.assertEqual(caught.exception.diagnostic, {'stage': 'read', 'exception_class': 'contract_error'})
        class BrokenStream(LargeStream):
            def read1(self, size):raise IncompleteRead(SECRET.encode())
        with patch.object(obs, 'build_opener') as opener:
            opener.return_value.open.return_value = BrokenStream()
            with self.assertLogs(obs.logger, level='ERROR') as logs:
                status, _, body = observation_tests.request('/api/observations?ra=350&dec=35')
        # The existing observations handler treated HTTPException as internal 500.
        self.assertEqual((status, body['error']), (500, 'internal_error'))
        events = [json.loads(record.getMessage()) for record in logs.records]
        event = next(x for x in events if x['event'] == 'upstream_diagnostic')
        self.assertEqual((event['stage'], event['exception_class']), ('read', 'incomplete_read'))
        self.assertNotIn(SECRET, json.dumps(events))

    def test_diagnostic_state_is_per_exception_across_threads(self):
        errors = [URLError(socket.gaierror(SECRET)), URLError(ssl.SSLError(SECRET))]*100
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda x: diagnostic.describe(x, 'read'), errors))
        self.assertEqual([d['reason_class'] for d in results], ['dns_error', 'tls_error']*100)
        self.assertTrue(all(d['stage'] == 'read' for d in results))
        api = observation_tests.api;local = threading.local()
        class Opener:
            def open(self, request, timeout):raise URLError(local.cause)
        def run_one(i):
            local.cause = socket.gaierror(SECRET) if i % 2 == 0 else ssl.SSLError(SECRET)
            try:api.fetch('https://irsa.ipac.caltech.edu/SIA')
            except api.UpstreamError as exc:return exc.diagnostic['reason_class']
        with patch.object(api, 'build_opener', return_value=Opener()), ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(run_one, range(100)))
        self.assertEqual(results, ['dns_error', 'tls_error']*50)


if __name__ == '__main__':unittest.main()

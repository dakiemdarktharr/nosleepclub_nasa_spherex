"""Exercise batch sequence retries and HTTP behavior without remote dependencies."""
from http.client import HTTPResponse
from io import BytesIO
import json
import unittest
from unittest.mock import patch

from web.api import sequence as api
from web.api.frame import FrameError


class MemorySocket:
    def __init__(self, content):
        self.input, self.output = BytesIO(content), BytesIO()

    def makefile(self, mode, *args, **kwargs):
        return self.input

    def sendall(self, data):
        self.output.write(data)


def post(body):
    content = json.dumps(body).encode()
    request = (b'POST /api/sequence HTTP/1.1\r\nHost: demo.example\r\n'
               b'Content-Type: application/json\r\nContent-Length: ' + str(len(content)).encode()
               + b'\r\n\r\n' + content)
    sock = MemorySocket(request)
    api.handler(sock, ('127.0.0.1', 1), None)
    response = HTTPResponse(MemorySocket(sock.output.getvalue()))
    response.begin()
    return response.status, json.loads(response.read())


class SequenceApiTest(unittest.TestCase):
    def test_retry_after_header_is_bounded_numeric_delay(self):
        self.assertEqual(api.retry_delay('5'), 2)
        self.assertEqual(api.retry_delay('0'), .5)
        self.assertEqual(api.retry_delay('not-a-number'), .7)
        self.assertEqual(api.retry_delay('nan'), .7)
        self.assertEqual(api.MAX_CONCURRENT_FRAMES, 5)

    def test_upstream_retry_after_string_does_not_become_internal_error(self):
        frame = FrameError('upstream_http_error', upstream_http_status=503, retry_after='5')
        params = {'release': 'dr1', 'detector': 6}
        body = {'frames': [{'index': 0, 'url': 'https://irsa.example/frame'}]}
        produced = iter([frame, (b'png bytes', {'X-Frame-Obs-ID': 'obs-1'})])

        def produce(_params):
            result = next(produced)
            if isinstance(result, BaseException):
                raise result
            return result

        with self.assertLogs(api.logger, level='INFO') as logs:
            with (patch.object(api, 'parse_request', return_value=[(0, params)]),
                  patch.object(api, 'identity', return_value=('test', None)),
                  patch.object(api, 'guard'),
                  patch.object(api.response_cache, 'run', side_effect=lambda _key, produce: (produce(), 'miss')),
                  patch.object(api, 'produce_frame', side_effect=produce),
                  patch.object(api.time, 'sleep') as sleep):
                status, result = post(body)

        self.assertEqual(status, 200)
        self.assertEqual(result['errors'], [])
        self.assertEqual(len(result['frames']), 1)
        sleep.assert_called_once_with(2)
        event = json.loads(logs.records[-1].getMessage())
        self.assertEqual(event['event'], 'sequence_request')
        self.assertEqual((event['category'], event['status'], event['frame_count']), ('ok', 200, 1))


if __name__ == '__main__':
    unittest.main()

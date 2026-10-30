"""HTTP contract and real IRSA VOTable schema checks without network or MongoDB."""
from http.client import HTTPResponse
from io import BytesIO
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

spec = importlib.util.spec_from_file_location('observations_api', Path(__file__).resolve().parents[1] / 'web/api/observations.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

# Field names, units and values reproduced from data/raw/quality/w350p35/qr2.xml.
SAMPLE = b'''<?xml version="1.0" encoding="utf-8"?>
<VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE type="results">
<INFO name="QUERY_STATUS" value="OK"/><TABLE>
<FIELD name="t_min" unit="d"/><FIELD name="t_max" unit="d"/>
<FIELD name="em_min" unit="m"/><FIELD name="em_max" unit="m"/>
<FIELD name="obs_id"/><FIELD name="energy_bandpassname"/><FIELD name="s_region"/>
<FIELD name="access_url"/><FIELD name="obs_collection"/>
<DATA><TABLEDATA><TR><TD>61024.093720</TD><TD>61024.095053</TD>
<TD>2.40270e-06</TD><TD>3.84730e-06</TD><TD>2025W51_1A_0021_3</TD><TD>SPHEREx-D4</TD>
<TD>POLYGON ICRS 348.2 34.1 351.8 35.9 353.8 32.9</TD>
<TD>https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/level2/a.fits</TD><TD>spherex_qr2</TD>
</TR></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>'''


class MemorySocket:
    def __init__(self, content):
        self.input, self.output = BytesIO(content), BytesIO()
    def makefile(self, mode, *args, **kwargs):
        return self.input
    def sendall(self, data):
        self.output.write(data)


def request(path, method='GET'):
    sock = MemorySocket(f'{method} {path} HTTP/1.1\r\nHost: demo.example\r\n\r\n'.encode())
    with patch.dict('os.environ', {'SPHEREX_LOCAL_API': '1'}):
        api.handler(sock, ('127.0.0.1', 1), None)
    response = HTTPResponse(MemorySocket(sock.output.getvalue()), method=method)
    response.begin()
    import json
    payload = response.read()
    return response.status, dict(response.getheaders()), json.loads(payload) if payload else None


class ObservationsTest(unittest.TestCase):
    def params(self, extra=''):
        return api.parse_params('ra=350&dec=35&maxrec=500' + extra)

    def test_input_validation_and_exact_sia_query(self):
        p = self.params('&radius=0.16&release=qr3&deep=1&detector=6&time_min_mjd=60000&time_max_mjd=61000&band_min_um=1&band_max_um=2')
        q = parse_qs(urlsplit(api.upstream_url(p)).query)
        self.assertEqual(q['COLLECTION'], ['spherex_qr3_deep'])
        self.assertEqual(q['BAND'], ['1e-06 2e-06'])
        self.assertEqual(q['TIME'], ['60000 61000'])
        self.assertEqual(q['MAXREC'], ['500'])
        for query in ('ra=nan&dec=0', 'ra=360&dec=0', 'ra=0&dec=91', 'ra=0&dec=0&radius=0.161',
                      'ra=0&dec=0&detector=7', 'ra=0&dec=0&maxrec=501', 'ra=0&dec=0&ra=1',
                      'ra=0&dec=0&band_min_um=1', 'ra=0&dec=0&url=https://evil.test', 'ra=12:34:56&dec=0'):
            with self.subTest(query=query), self.assertRaises(ValueError):
                api.parse_params(query)

    def test_parsing_real_fixture_and_sample(self):
        rows, truncated, count = api.parse_votable(SAMPLE, self.params())
        self.assertEqual((count, truncated, rows[0]['detector']), (1, False, 4))
        self.assertAlmostEqual(rows[0]['wavelength_center_um'], 3.125)
        self.assertAlmostEqual(rows[0]['wavelength_width_um'], 1.4446)
        self.assertEqual(rows[0]['t_min_mjd'], 61024.093720)
        self.assertIn('POLYGON ICRS', rows[0]['footprint'])
        fixture = Path(__file__).resolve().parents[1] / 'data/raw/quality/w350p35/qr2.xml'
        if fixture.exists():
            rows, truncated, count = api.parse_votable(fixture.read_bytes(), self.params())
            self.assertEqual(count, 471)
            self.assertEqual(rows[0]['obs_id'], '2025W51_1A_0021_3')
            self.assertFalse(truncated)

    def test_overflow_no_data_and_detector_filter(self):
        overflow = SAMPLE.replace(b'</TABLE></RESOURCE>', b'</TABLE><INFO name="QUERY_STATUS" value="OVERFLOW"/></RESOURCE>')
        with patch.object(api, 'fetch', return_value=overflow):
            status, _, body = request('/api/observations?ra=350&dec=35&detector=6')
        self.assertEqual(status, 200)
        self.assertEqual((body['status'], body['returned_count'], body['upstream_count']), ('truncated', 0, 1))
        self.assertTrue(body['truncated'])
        self.assertEqual(len(body['provenance']['response_sha256']), 64)
        with patch.object(api, 'fetch', return_value=SAMPLE):
            self.assertEqual(request('/api/observations?ra=350&dec=35&detector=6')[2]['status'], 'no_data')

    def test_rejects_unsafe_urls_bad_schema_size_and_errors(self):
        self.assertIsNone(api.safe_access_url('https://evil.example/ibe/data/spherex/qr2/level2/a.fits', 'qr2'))
        self.assertIsNone(api.safe_access_url('https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/a.fits', 'qr2'))
        with self.assertRaises(api.UpstreamError):
            api.fetch('https://evil.example/SIA')
        cases = [SAMPLE.replace(b'value="OK"', b'value="ERROR"'),
                 SAMPLE.replace(b'unit="m"', b'unit="um"', 1),
                 SAMPLE.replace(b'spherex_qr2</TD>', b'spherex_qr3</TD>'),
                 b'<!DOCTYPE x [<!ENTITY y "abc">]><VOTABLE/>', b'x' * (api.MAX_BYTES + 1),
                 SAMPLE.replace(b'<TABLEDATA>', b'<BINARY>').replace(b'</TABLEDATA>', b'</BINARY>')]
        for sample in cases:
            with self.subTest(sample=sample[:80]), self.assertRaises(api.UpstreamError):
                api.parse_votable(sample, self.params())
        with patch.object(api, 'fetch', side_effect=api.UpstreamError('upstream_timeout')):
            status, _, body = request('/api/observations?ra=350&dec=35')
            self.assertEqual((status, body), (504, {'error': 'upstream_timeout'}))

    def test_fetch_limits_and_redirect_policy(self):
        class Response:
            def __init__(self, data):
                self.data = BytesIO(data)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read1(self, size):
                return self.data.read(size)
        class Opener:
            def open(self, request, timeout):
                self.request, self.timeout = request, timeout
                return Response(b'x' * (api.MAX_BYTES + 1))
        opener = Opener()
        with patch.object(api, 'build_opener', return_value=opener):
            with self.assertRaises(api.UpstreamError) as caught:
                api.fetch(api.upstream_url(self.params()))
        self.assertEqual(caught.exception.code, 'upstream_too_large')
        self.assertEqual(opener.timeout, api.TIMEOUT)
        self.assertIsNone(api.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.example'))

    def test_http_validation_and_log_privacy(self):
        with self.assertLogs('observations_api', level='WARNING') as logs:
            self.assertEqual(request('/api/observations?ra=nan&dec=0')[0], 400)
            status, headers, _ = request('/api/observations', 'POST')
            self.assertEqual(status, 405)
            self.assertEqual(headers['Allow'], 'GET')
            self.assertIn('X-Request-ID', headers)
            with patch.object(api, 'fetch', side_effect=RuntimeError('sensitive URL token')):
                self.assertEqual(request('/api/observations?ra=350&dec=35')[0], 500)
        self.assertNotIn('sensitive URL token', str(logs.output))
        self.assertNotIn('ra=350', str(logs.output))


if __name__ == '__main__':
    unittest.main()

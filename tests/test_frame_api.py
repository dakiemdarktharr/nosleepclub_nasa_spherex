"""Exercise FITS/WCS rendering and the HTTP contract without remote dependencies."""
from http.client import HTTPResponse, IncompleteRead
from io import BytesIO
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.error import HTTPError

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, Sip
from PIL import Image

spec = importlib.util.spec_from_file_location('frame_api', Path(__file__).resolve().parents[1] / 'web/api/frame.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
URL = 'https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/level2/2025W51_1A/l2b-v21-2025-354/4/level2_2025W51_1A_0021_3D4_spx_l2b-v21-2025-354.fits'


def parameters(**extra):
    return api.parse_params(urlencode({'url': URL, 'ra': 350, 'dec': 35, 'fov_deg': .005, **extra}))


def synthetic(rotation=0, sip=False, center_flag=0, top_flag=0, bottom_nan=False, zodi=1):
    w = WCS(naxis=2)
    w.wcs.crpix = [3, 3]
    w.wcs.crval = [350, 35]
    w.wcs.cdelt = [-api.SCALE_ARCSEC / 3600, api.SCALE_ARCSEC / 3600]
    theta = np.deg2rad(rotation)
    w.wcs.pc = [[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]]
    w.wcs.ctype = ['RA---TAN-SIP', 'DEC--TAN-SIP'] if sip else ['RA---TAN', 'DEC--TAN']
    if sip:
        a, b = np.zeros((3, 3)), np.zeros((3, 3))
        a[2, 0], b[0, 2] = 1e-4, -1e-4
        w.sip = Sip(a, b, None, None, w.wcs.crpix)
    hdr = w.to_header(relax=True)
    hdr['BUNIT'], hdr['OBSID'], hdr['DETECTOR'], hdr['MJD-OBS'] = 'MJy / sr', '2025W51_1A_0021_3', 4, 61024.09372
    yy, xx = np.indices((5, 5))
    ra, dec = w.pixel_to_world_values(xx, yy)
    # Sky gradient: pixels get brighter toward north and toward the east.
    data = ((dec - 35) * 10000 + (ra - 350) * 5000 + 50).astype(np.float32)
    flags = np.zeros((5, 5), dtype=np.int32)
    flags[2, 2], flags[3, 2] = center_flag, top_flag
    if bottom_nan:
        data[1, 2] = np.nan
    zh = fits.ImageHDU(np.full((5, 5), zodi, dtype=np.float32), name='ZODI')
    zh.header['BUNIT'] = 'MJy / sr'
    output = BytesIO()
    flag_hdu = fits.ImageHDU(flags, name='FLAGS')
    flag_hdu.header['HIERARCH MP_SOURCE'], flag_hdu.header['HIERARCH MP_FULLSAMPLE'] = 21, 12
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data, header=hdr, name='IMAGE'), flag_hdu, zh]).writeto(output)
    return output.getvalue()


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
    return response.status, dict(response.getheaders()), response.read()


class FrameTest(unittest.TestCase):
    def test_upstream_http_failure_logs_only_code_and_status(self):
        with patch.object(api, 'build_opener') as opener:
            opener.return_value.open.side_effect = HTTPError(URL, 503, 'private upstream body', {}, BytesIO())
            with self.assertRaises(api.FrameError) as caught:
                api.fetch(URL)
        self.assertEqual(caught.exception.upstream_http_status, 503)
        path = '/api/frame?' + urlencode({'url': URL, 'ra': 350, 'dec': 35, 'fov_deg': .005})
        with patch.object(api, 'fetch', side_effect=caught.exception), self.assertLogs(api.logger, level='INFO') as logs:
            status, _, body = request(path)
        self.assertEqual(status, 502)
        self.assertEqual(json.loads(body), {'error': 'upstream_http_error'})
        event = json.loads(logs.records[-1].getMessage())
        self.assertEqual(event['error_code'], 'upstream_http_error')
        self.assertEqual(event['upstream_http_status'], 503)
        self.assertEqual(event['level'], 'error')
        self.assertNotIn(URL, logs.records[-1].getMessage())
        self.assertNotIn('private upstream body', logs.records[-1].getMessage())

    def test_input_allowlist_and_limits(self):
        self.assertEqual(parameters()['size_px'], 3)
        self.assertLessEqual(parameters(fov_deg=.12)['size_px'], 192)
        for extra in ({'url': URL.replace('irsa.ipac.caltech.edu', 'evil.example')},
                      {'url': URL + '?x=1'}, {'url': URL.replace('/qr2/', '/qr1/')},
                      {'url': URL.replace('/4/', '/5/')}, {'url': URL.replace('https:', 'http:')},
                      {'url': URL.replace('/level2/', '/level2/../')}, {'ra': 'nan'}, {'dec': 91},
                      {'fov_deg': .121}, {'zodi': 'other'}, {'low': 0}, {'low': 1, 'high': 1}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                parameters(**extra)
        with self.assertRaises(ValueError):
            api.parse_params(urlencode({'url': URL, 'ra': 350, 'dec': 35}) + '&ra=3')

    def test_masks_source_nan_zodi_and_fixed_contrast(self):
        p = parameters(low=0, high=100)
        png, info = api.render(synthetic(center_flag=api.SOURCE, top_flag=1, bottom_nan=True), p)
        rgb = np.array(Image.open(BytesIO(png)))
        self.assertEqual(tuple(rgb[0, 1]), (255, 140, 0))
        self.assertEqual(tuple(rgb[2, 1]), (255, 0, 255))
        self.assertEqual(rgb[1, 1, 0], rgb[1, 1, 1])
        self.assertEqual(info['valid_pixels'], 7)
        p2 = parameters(low=0, high=100, zodi='subtract')
        corrected = np.array(Image.open(BytesIO(api.render(synthetic(zodi=10), p2)[0])))
        raw = np.array(Image.open(BytesIO(api.render(synthetic(zodi=10), p)[0])))
        self.assertLess(corrected[1, 1, 0], raw[1, 1, 0])

    def test_fullsample_is_masked_and_source_alone_remains_visible(self):
        p = parameters(low=0, high=100)
        for flag in [api.FULLSAMPLE, api.FULLSAMPLE | api.SOURCE]:
            png, info = api.render(synthetic(center_flag=flag), p)
            rgb = np.array(Image.open(BytesIO(png)))
            self.assertEqual(tuple(rgb[1, 1]), (255, 140, 0))
            self.assertEqual(info['valid_pixels'] + info['masked_pixels'] + info['missing_pixels'], 9)
            self.assertEqual(info['masked_pixels'], 1)
        png, info = api.render(synthetic(center_flag=api.SOURCE), p)
        rgb = np.array(Image.open(BytesIO(png)))
        self.assertEqual(rgb[1, 1, 0], rgb[1, 1, 1])
        self.assertEqual(info['masked_pixels'], 0)
        with fits.open(BytesIO(synthetic())) as hdus:
            hdus['FLAGS'].header['MP_SOURCE'] = 20
            invalid = BytesIO(); hdus.writeto(invalid)
        with self.assertRaises(api.FrameError) as error:
            api.render(invalid.getvalue(), p)
        self.assertEqual(error.exception.code, 'invalid_flag_layout')

    def test_wcs_rotation_and_sip_keep_north_up_east_left(self):
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                p = parameters(low=0, high=100)
                rgb = np.array(Image.open(BytesIO(api.render(synthetic(rotation=rotation, sip=True), p)[0])))
                self.assertGreater(int(rgb[0, 1, 0]), int(rgb[2, 1, 0]))
                self.assertGreater(int(rgb[1, 0, 0]), int(rgb[1, 2, 0]))

    def test_handler_provenance_and_failure_no_fake_png(self):
        path = '/api/frame?' + urlencode({'url': URL, 'ra': 350, 'dec': 35, 'fov_deg': .005})
        raw = synthetic()
        with patch.object(api, 'fetch', return_value=raw):
            status, headers, body = request(path)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'image/png')
        self.assertEqual(headers['X-Frame-Cutout-SHA256'], api.sha256(raw).hexdigest())
        self.assertEqual(headers['X-Frame-Obs-ID'], '2025W51_1A_0021_3')
        self.assertEqual(headers['X-Frame-Grid-Scale-Arcsec'], '6.15')
        self.assertEqual(headers['X-Frame-Contract'], '1.1')
        self.assertEqual(headers['X-Frame-Mask-Policy'], 'source-only-allowlist-v2')
        self.assertIn('max-age=300', headers['Cache-Control'])
        self.assertEqual(Image.open(BytesIO(body)).size, (3, 3))
        with patch.object(api, 'fetch', side_effect=api.FrameError('upstream_timeout', 504)):
            status, headers, body = request(path)
        self.assertEqual(status, 504)
        self.assertEqual(json.loads(body)['error'], 'upstream_timeout')
        self.assertEqual(headers['Content-Type'], 'application/json')

    def test_invalid_fits_and_no_redirect(self):
        with self.assertRaises(api.FrameError):
            api.render(b'not fits', parameters())
        with self.assertRaises(api.FrameError):
            api.render(b'x' * (api.MAX_BYTES + 1), parameters())
        with fits.open(BytesIO(synthetic()), memmap=False) as hdus:
            hdus['IMAGE'].header['BUNIT'] = 'mJy/sr'
            changed = BytesIO()
            hdus.writeto(changed)
        with self.assertRaises(api.FrameError) as bad_unit:
            api.render(changed.getvalue(), parameters())
        self.assertEqual(bad_unit.exception.code, 'invalid_fits_units')
        with self.assertRaises(api.FrameError):
            api.fetch(URL.replace('irsa.ipac.caltech.edu', 'evil.example'))
        self.assertIsNone(api.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.example'))
        self.assertEqual(request('/api/frame', 'POST')[0], 405)

    def test_existing_irsa_cutout_when_available(self):
        path = Path(__file__).resolve().parents[1] / 'data/raw/benchmark/barnard/images/level2_2025W33_2C_0321_1D6_spx_l2b-v20-2025-266.fits'
        if not path.exists():
            self.skipTest('optional local IRSA cutout is not present')
        with fits.open(path) as hdus:
            image = hdus['IMAGE']
            ra, dec = WCS(image.header).celestial.pixel_to_world_values((image.data.shape[1] - 1) / 2, (image.data.shape[0] - 1) / 2)
        url = 'https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/level2/2025W33_2C/l2b-v20-2025-266/6/' + path.name
        p = api.parse_params(urlencode({'url': url, 'ra': ra, 'dec': dec, 'fov_deg': .05}))
        png, meta = api.render(path.read_bytes(), p)
        self.assertTrue(png.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertGreater(meta['valid_pixels'], 0)
        self.assertEqual(meta['mjd'], 60902.864714549)

    def test_streamed_upstream_size_limit(self):
        class Response:
            def __init__(self):
                self.data = BytesIO(b'SIMPLE  =' + b'x' * api.MAX_BYTES)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read1(self, length):
                return self.data.read(length)
        class Opener:
            def open(self, request, timeout):
                self.timeout = timeout
                return Response()
        opener = Opener()
        with patch.object(api, 'build_opener', return_value=opener):
            with self.assertRaises(api.FrameError) as failure:
                api.fetch(api.cutout_url(parameters()))
        self.assertEqual(failure.exception.code, 'upstream_too_large')
        self.assertEqual(opener.timeout, 20)

    def test_slow_upstream_is_allowed_until_bounded_deadline(self):
        class Response:
            def __init__(self):
                self.data = BytesIO(b'SIMPLE  =test')
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read1(self, length):
                return self.data.read(length)
        class Opener:
            def open(self, request, timeout):
                return Response()
        url = api.cutout_url(parameters())
        with patch.object(api, 'build_opener', return_value=Opener()):
            with patch.object(api.time, 'monotonic', side_effect=[0, 40, 40, 40]):
                self.assertEqual(api.fetch(url), b'SIMPLE  =test')
            with patch.object(api.time, 'monotonic', side_effect=[0, 81]):
                with self.assertRaises(api.FrameError) as failure:
                    api.fetch(url)
        self.assertEqual(failure.exception.code, 'upstream_timeout')
        self.assertEqual(failure.exception.status, 504)

    def test_truncated_chunked_response_is_upstream_error(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read1(self, length):
                raise IncompleteRead(b'partial')
        class Opener:
            def open(self, request, timeout):
                return Response()
        with patch.object(api, 'build_opener', return_value=Opener()):
            with self.assertRaises(api.FrameError) as failure:
                api.fetch(api.cutout_url(parameters()))
        self.assertEqual((failure.exception.code, failure.exception.status), ('upstream_unavailable', 502))

    def test_truncated_content_length_is_not_treated_as_complete_fits(self):
        class Response:
            headers = {'Content-Length': '100'}
            def __init__(self):
                self.data = BytesIO(b'SIMPLE  =partial')
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read1(self, length):
                return self.data.read(length)
        class Opener:
            def open(self, request, timeout):
                return Response()
        with patch.object(api, 'build_opener', return_value=Opener()):
            with self.assertRaises(api.FrameError) as failure:
                api.fetch(api.cutout_url(parameters()))
        self.assertEqual((failure.exception.code, failure.exception.status), ('upstream_incomplete', 502))


if __name__ == '__main__':
    unittest.main()

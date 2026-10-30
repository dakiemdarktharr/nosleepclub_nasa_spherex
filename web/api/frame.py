"""Render an IRSA SPHEREx cutout on a common north-up tangent-plane grid."""
from datetime import datetime, timezone
from hashlib import sha256
from http.client import HTTPException
from http.server import BaseHTTPRequestHandler
from io import BytesIO
import json
import math
import os
import re
import secrets
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image

try:
    from api._access_control import AccessDenied, guard
    from api._telemetry import emit_request, request_logger
except ModuleNotFoundError as exc:
    if exc.name not in ('api', 'api._access_control', 'api._telemetry'):
        raise
    from web.api._access_control import AccessDenied, guard
    from web.api._telemetry import emit_request, request_logger

HOST = 'irsa.ipac.caltech.edu'
SCALE_ARCSEC = 6.15
MAX_BYTES = 12_000_000
SOCKET_TIMEOUT = 20
DEADLINE = 80
SOURCE = 1 << 21
FULLSAMPLE = 1 << 12
FRAME_CONTRACT = '1.1'
MASK_POLICY = 'source-only-allowlist-v2'
logger = request_logger('frame_api')
PATH = re.compile(r'^/ibe/data/spherex/(?P<release>qr[23])/level2/(?P<period>\d{4}W\d{2}_[0-9][A-Z])/(?P<version>l2b-v\d+-\d{4}-\d{3})/(?P<detector>[1-6])/level2_(?P=period)_(?P<exposure>\d{4}_[0-9])D(?P=detector)_spx_(?P=version)\.fits$')


class FrameError(Exception):
    def __init__(self, code, status=502, upstream_http_status=None):
        self.code, self.status = code, status
        self.upstream_http_status = upstream_http_status
        super().__init__(code)


def parse_params(query):
    if len(query) > 2048:
        raise ValueError('query_too_long')
    pairs = parse_qs(query, keep_blank_values=True, strict_parsing=True, max_num_fields=12)
    allowed = {'url', 'ra', 'dec', 'fov_deg', 'zodi', 'low', 'high'}
    if set(pairs) - allowed or any(len(v) != 1 for v in pairs.values()):
        raise ValueError('invalid_parameters')
    p = {k: v[0] for k, v in pairs.items()}
    url = p.get('url', '')
    try:
        parsed = urlsplit(url)
    except ValueError:
        raise ValueError('invalid_url')
    match = PATH.fullmatch(parsed.path)
    if parsed.scheme != 'https' or parsed.netloc != HOST or not match or parsed.query or parsed.fragment:
        raise ValueError('invalid_url')
    def num(key, default=None):
        if key not in p:
            if default is None:
                raise ValueError('missing_parameter')
            return default
        try:
            x = float(p[key])
        except ValueError:
            raise ValueError('invalid_number')
        if not math.isfinite(x):
            raise ValueError('invalid_number')
        return x
    ra, dec, fov = num('ra'), num('dec'), num('fov_deg', 0.05)
    if not (0 <= ra < 360 and -90 <= dec <= 90 and 0 < fov <= 0.12):
        raise ValueError('out_of_range')
    zodi = p.get('zodi', 'raw')
    if zodi not in ('raw', 'subtract'):
        raise ValueError('invalid_zodi')
    if ('low' in p) != ('high' in p):
        raise ValueError('contrast_requires_both_bounds')
    low, high = (num('low'), num('high')) if 'low' in p else (None, None)
    if low is not None and (low >= high or abs(low) > 1e9 or abs(high) > 1e9):
        raise ValueError('invalid_contrast')
    n = max(3, math.ceil(fov * 3600 / SCALE_ARCSEC))
    if n % 2 == 0:
        n += 1
    if n > 192:
        raise ValueError('out_of_range')
    return {'url': url, 'ra': ra, 'dec': dec, 'fov_deg': fov, 'size_px': n, 'zodi': zodi,
            'low': low, 'high': high, 'release': match['release'], 'detector': int(match['detector']),
            'obs_id': match['period'] + '_' + match['exposure']}


def cutout_url(p):
    # Oversize the native cutout for rotated output-grid corners; clip remains visible.
    width = p['size_px'] * SCALE_ARCSEC / 3600 * math.sqrt(2) * 1.15
    return p['url'] + '?' + urlencode({'center': f"{p['ra']:.12g},{p['dec']:.12g}", 'size': f'{width:.8f}'})


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.netloc != HOST or not PATH.fullmatch(p.path):
        raise FrameError('invalid_upstream')
    started = time.monotonic()
    try:
        with build_opener(NoRedirect()).open(Request(url, headers={'User-Agent': 'SPHEREx-frame-demo/1.0', 'Accept': 'application/fits'}), timeout=SOCKET_TIMEOUT) as response:
            declared = getattr(response, 'headers', {}).get('Content-Length')
            if declared is not None:
                if not re.fullmatch(r'[0-9]+', declared):
                    raise FrameError('upstream_invalid_length')
                declared = int(declared)
                if declared > MAX_BYTES:
                    raise FrameError('upstream_too_large')
            chunks, size = [], 0
            while True:
                if time.monotonic() - started > DEADLINE:
                    raise FrameError('upstream_timeout', 504)
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise FrameError('upstream_too_large')
                chunks.append(chunk)
            if time.monotonic() - started > DEADLINE:
                raise FrameError('upstream_timeout', 504)
            if declared is not None and size != declared:
                raise FrameError('upstream_incomplete')
            content = b''.join(chunks)
            if not content.startswith(b'SIMPLE  ='):
                raise FrameError('upstream_not_fits')
            return content
    except (TimeoutError, socket.timeout):
        raise FrameError('upstream_timeout', 504)
    except HTTPError as exc:
        upstream_status = exc.code
        exc.close()
        raise FrameError('upstream_http_error', upstream_http_status=upstream_status) from None
    except URLError as exc:
        raise FrameError('upstream_timeout', 504) if isinstance(exc.reason, (TimeoutError, socket.timeout)) else FrameError('upstream_unavailable')
    except (OSError, HTTPException):
        raise FrameError('upstream_unavailable')


def render(content, p):
    if len(content) > MAX_BYTES:
        raise FrameError('upstream_too_large')
    try:
        with fits.open(BytesIO(content), memmap=False, lazy_load_hdus=True) as hdus:
            image_hdu, flags_hdu = hdus['IMAGE'], hdus['FLAGS']
            layout = {key: [card.value for card in flags_hdu.header.cards if card.keyword == key]
                      for key in ('MP_SOURCE', 'MP_FULLSAMPLE')}
            if layout != {'MP_SOURCE': [21], 'MP_FULLSAMPLE': [12]}:
                raise FrameError('invalid_flag_layout')
            image = np.asarray(image_hdu.data, dtype=float)
            flags = np.asarray(flags_hdu.data)
            if image.ndim != 2 or image.shape != flags.shape or max(image.shape) > 512 or not np.issubdtype(flags.dtype, np.integer):
                raise FrameError('invalid_fits_shape')
            hdr = image_hdu.header
            if str(hdr.get('BUNIT', '')).replace(' ', '') != 'MJy/sr':
                raise FrameError('invalid_fits_units')
            if str(hdr.get('OBSID', '')) != p['obs_id'] or str(hdr.get('DETECTOR', '')) != str(p['detector']):
                raise FrameError('fits_identity_mismatch')
            if p['zodi'] == 'subtract':
                zodi = np.asarray(hdus['ZODI'].data, dtype=float)
                if zodi.shape != image.shape or str(hdus['ZODI'].header.get('BUNIT', '')).replace(' ', '') != 'MJy/sr':
                    raise FrameError('invalid_zodi')
                image = image - zodi
            native = WCS(hdr).celestial
            if native.pixel_n_dim != 2 or native.world_n_dim != 2 or not native.has_celestial or native.wcs.lng != 0 or native.wcs.lat != 1:
                raise FrameError('invalid_wcs')
            mjd = hdr.get('MJD-OBS')
            if mjd is not None:
                mjd = float(mjd)
                if not math.isfinite(mjd):
                    mjd = None
            n = p['size_px']
            grid = WCS(naxis=2)
            grid.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
            grid.wcs.cdelt = np.array([-SCALE_ARCSEC / 3600, SCALE_ARCSEC / 3600])
            grid.wcs.crval = [p['ra'], p['dec']]
            grid.wcs.ctype = ['RA---TAN', 'DEC--TAN']
            yy, xx = np.indices((n, n), dtype=float)
            # PNG row zero is north: reverse the normal FITS y-axis.
            ra, dec = grid.pixel_to_world_values(xx, n - 1 - yy)
            nx, ny = native.world_to_pixel_values(ra, dec)
            finite = np.isfinite(nx) & np.isfinite(ny)
            inside = finite & (nx >= -0.5) & (ny >= -0.5) & (nx < image.shape[1] - 0.5) & (ny < image.shape[0] - 0.5)
            ix = np.clip(np.floor(np.where(finite, nx, 0) + 0.5), 0, image.shape[1] - 1).astype(int)
            iy = np.clip(np.floor(np.where(finite, ny, 0) + 0.5), 0, image.shape[0] - 1).astype(int)
            sampled = image[iy, ix]
            # FULLSAMPLE is the rotating full-history readout region, not a
            # declaration that a pixel has a usable nominal science ramp.
            bad = (flags[iy, ix].astype(np.int64) & ~SOURCE) != 0
            available = inside & np.isfinite(sampled)
            valid = available & ~bad
            low, high = p['low'], p['high']
            mode = 'fixed' if low is not None else 'percentile_1_99'
            if low is None:
                if np.any(valid):
                    low, high = (float(x) for x in np.percentile(sampled[valid], [1, 99]))
                    if high <= low:
                        low, high = low - 0.5, high + 0.5
                else:
                    low, high = 0.0, 1.0
            pixels = np.zeros((n, n, 3), dtype=np.uint8)
            pixels[:] = [255, 0, 255]
            pixels[available & bad] = [255, 140, 0]
            gray = np.zeros((n, n), dtype=np.uint8)
            gray[valid] = np.rint(np.clip((sampled[valid] - low) / (high - low), 0, 1) * 255).astype(np.uint8)
            pixels[valid] = np.repeat(gray[valid, None], 3, axis=1)
            output = BytesIO()
            Image.fromarray(pixels).save(output, format='PNG')
            return output.getvalue(), {'low': low, 'high': high, 'mode': mode, 'mjd': mjd,
                                       'valid_pixels': int(valid.sum()), 'masked_pixels': int((available & bad).sum()),
                                       'missing_pixels': int((~available).sum()), 'fov_deg': n * SCALE_ARCSEC / 3600}
    except FrameError:
        raise
    except Exception:
        raise FrameError('invalid_fits')


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, status, content, content_type, category, headers=None, error_code=None, upstream_http_status=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Request-ID', self.request_id)
        commit = os.environ.get('VERCEL_GIT_COMMIT_SHA', '')
        if re.fullmatch(r'[0-9a-f]{40}', commit): self.send_header('X-App-Commit', commit)
        self.send_header('Cache-Control', 'public, max-age=300, s-maxage=300' if status == 200 else 'no-store')
        if status == 405:
            self.send_header('Allow', 'GET')
        if status == 429:
            self.send_header('Retry-After', str(self.retry_after))
        for k, v in (headers or {}).items():
            self.send_header(k, str(v))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(content)
        emit_request(logger, {'event': 'frame_request', 'request_id': self.request_id, 'status': status,
                             'category': category, 'latency_ms': round((time.monotonic() - self.started) * 1000, 2),
                             'error_code': error_code, 'upstream_http_status': upstream_http_status})

    def dispatch(self, method):
        self.request_id, self.started = secrets.token_hex(16), time.monotonic()
        if method != 'GET':
            return self.respond(405, b'{"error":"method_not_allowed"}', 'application/json', 'method')
        try:
            p = parse_params(urlsplit(self.path).query)
            guard('frame', self.headers, self.client_address)
            url = cutout_url(p)
            content = fetch(url)
            retrieved = datetime.now(timezone.utc).isoformat()
            png, meta = render(content, p)
            h = {'X-Frame-Contract': FRAME_CONTRACT, 'X-Frame-Source-URL': p['url'], 'X-Frame-Cutout-URL': url,
                 'X-Frame-Cutout-SHA256': sha256(content).hexdigest(), 'X-Frame-Retrieved-At': retrieved,
                 'X-Frame-Release': p['release'], 'X-Frame-Obs-ID': p['obs_id'], 'X-Frame-Detector': p['detector'],
                 'X-Frame-Grid-RA-Deg': p['ra'], 'X-Frame-Grid-Dec-Deg': p['dec'],
                 'X-Frame-Grid-Scale-Arcsec': SCALE_ARCSEC, 'X-Frame-Grid-Size-Px': p['size_px'],
                 'X-Frame-Grid-FOV-Deg': meta['fov_deg'], 'X-Frame-Unit': 'MJy/sr', 'X-Frame-Zodi': p['zodi'],
                 'X-Frame-Contrast-Mode': meta['mode'], 'X-Frame-Contrast-Low': meta['low'],
                 'X-Frame-Contrast-High': meta['high'], 'X-Frame-Valid-Pixels': meta['valid_pixels'],
                 'X-Frame-Mask-Policy': MASK_POLICY, 'X-Frame-Masked-Pixels': meta['masked_pixels'],
                 'X-Frame-Missing-Pixels': meta['missing_pixels']}
            if meta['mjd'] is not None:
                h['X-Frame-MJD-Obs'] = meta['mjd']
            return self.respond(200, png, 'image/png', 'ok', h)
        except AccessDenied as exc:
            self.retry_after = exc.retry_after
            return self.respond(exc.status, json.dumps({'error': exc.code}).encode(), 'application/json', 'rate_limit' if exc.status == 429 else 'rate_unavailable')
        except ValueError:
            return self.respond(400, b'{"error":"invalid_parameters"}', 'application/json', 'validation')
        except FrameError as exc:
            return self.respond(exc.status, json.dumps({'error': exc.code}).encode(), 'application/json', 'upstream_or_fits',
                                error_code=exc.code, upstream_http_status=exc.upstream_http_status)
        except Exception:
            return self.respond(500, b'{"error":"internal_error"}', 'application/json', 'internal')

    def do_GET(self):
        self.dispatch('GET')
    def do_HEAD(self):
        self.dispatch('HEAD')
    def do_POST(self):
        self.dispatch('POST')
    def do_PUT(self):
        self.dispatch('PUT')
    def do_PATCH(self):
        self.dispatch('PATCH')
    def do_DELETE(self):
        self.dispatch('DELETE')
    def do_OPTIONS(self):
        self.dispatch('OPTIONS')

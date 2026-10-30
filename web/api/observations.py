"""Bounded, read-only SPHEREx SIA2 metadata discovery via the fixed IRSA endpoint."""
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler
import json
import logging
import math
import re
import secrets
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

try:
    from api._access_control import AccessDenied, guard
except ModuleNotFoundError as exc:
    if exc.name not in ('api', 'api._access_control'):
        raise
    from web.api._access_control import AccessDenied, guard

ENDPOINT = 'https://irsa.ipac.caltech.edu/SIA'
MAX_BYTES = 2_000_000
MAX_ROWS = 500
TIMEOUT = 6
DEADLINE = 8
logger = logging.getLogger('observations_api')


class UpstreamError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def parse_params(query):
    if len(query) > 2048:
        raise ValueError('query_too_long')
    pairs = parse_qs(query, keep_blank_values=True, strict_parsing=True, max_num_fields=20)
    allowed = {'ra', 'dec', 'radius', 'release', 'deep', 'detector', 'time_min_mjd',
               'time_max_mjd', 'band_min_um', 'band_max_um', 'maxrec'}
    if set(pairs) - allowed or any(len(v) != 1 for v in pairs.values()):
        raise ValueError('invalid_parameters')
    p = {k: v[0] for k, v in pairs.items()}
    def number(name, default=None):
        if name not in p:
            if default is None:
                raise ValueError('missing_parameter')
            return default
        try:
            x = float(p[name])
        except (TypeError, ValueError):
            raise ValueError('invalid_number')
        if not math.isfinite(x):
            raise ValueError('invalid_number')
        return x
    ra, dec, radius = number('ra'), number('dec'), number('radius', 0.05)
    if not 0 <= ra < 360 or not -90 <= dec <= 90 or not 0 < radius <= 0.16:
        raise ValueError('out_of_range')
    release, deep = p.get('release', 'qr2'), p.get('deep', '0')
    if release not in ('qr2', 'qr3') or deep not in ('0', '1'):
        raise ValueError('invalid_parameters')
    detector = p.get('detector')
    if detector is not None and detector not in ('1', '2', '3', '4', '5', '6'):
        raise ValueError('invalid_detector')
    maxrec = p.get('maxrec', '300')
    if not re.fullmatch(r'[0-9]{1,3}', maxrec) or not 1 <= int(maxrec) <= MAX_ROWS:
        raise ValueError('invalid_maxrec')
    result = {'ra_deg': ra, 'dec_deg': dec, 'radius_deg': radius, 'release': release,
              'deep': deep == '1', 'detector': int(detector) if detector else None, 'maxrec': int(maxrec)}
    for prefix, lower, upper in [('time', 'time_min_mjd', 'time_max_mjd'), ('band', 'band_min_um', 'band_max_um')]:
        if (lower in p) != (upper in p):
            raise ValueError('interval_requires_both_bounds')
        if lower in p:
            lo, hi = number(lower), number(upper)
            if lo > hi or (prefix == 'time' and not (0 <= lo <= hi <= 100000)) or (prefix == 'band' and not (0.01 <= lo <= hi <= 1000)):
                raise ValueError('invalid_interval')
            result[lower], result[upper] = lo, hi
    return result


def upstream_url(p):
    collection = 'spherex_' + p['release'] + ('_deep' if p['deep'] else '')
    query = [('COLLECTION', collection), ('POS', f"CIRCLE {p['ra_deg']:.12g} {p['dec_deg']:.12g} {p['radius_deg']:.12g}"),
             ('MAXREC', str(p['maxrec'])), ('RESPONSEFORMAT', 'VOTABLE')]
    if 'time_min_mjd' in p:
        query.append(('TIME', f"{p['time_min_mjd']:.12g} {p['time_max_mjd']:.12g}"))
    if 'band_min_um' in p:
        query.append(('BAND', f"{p['band_min_um'] * 1e-6:.12g} {p['band_max_um'] * 1e-6:.12g}"))
    return ENDPOINT + '?' + urlencode(query)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'irsa.ipac.caltech.edu' or parsed.path != '/SIA':
        raise UpstreamError('invalid_upstream')
    start = time.monotonic()
    try:
        with build_opener(NoRedirect()).open(Request(url, headers={'Accept': 'application/x-votable+xml, application/xml, text/xml', 'User-Agent': 'SPHEREx-metadata-demo/1.0'}), timeout=TIMEOUT) as response:
            chunks, size = [], 0
            while True:
                if time.monotonic() - start > DEADLINE:
                    raise UpstreamError('upstream_timeout')
                # read1 returns after at most one buffered network read, so a slow
                # stream cannot bypass the elapsed-time check between chunks.
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise UpstreamError('upstream_too_large')
                chunks.append(chunk)
            if time.monotonic() - start > DEADLINE:
                raise UpstreamError('upstream_timeout')
            return b''.join(chunks)
    except (TimeoutError, socket.timeout):
        raise UpstreamError('upstream_timeout')
    except HTTPError:
        raise UpstreamError('upstream_http_error')
    except URLError as exc:
        raise UpstreamError('upstream_timeout' if isinstance(exc.reason, (TimeoutError, socket.timeout)) else 'upstream_unavailable')
    except OSError:
        raise UpstreamError('upstream_unavailable')


def local(tag):
    return tag.rsplit('}', 1)[-1]


def safe_access_url(value, release):
    try:
        p = urlsplit(value)
        return value if p.scheme == 'https' and p.netloc == 'irsa.ipac.caltech.edu' and p.path.startswith('/ibe/data/spherex/' + release + '/level2/') and not (p.query or p.fragment) else None
    except ValueError:
        return None


def parse_votable(content, p):
    if len(content) > MAX_BYTES:
        raise UpstreamError('upstream_too_large')
    try:
        xml = content.decode('utf-8-sig')
        if '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
            raise UpstreamError('upstream_invalid_xml')
        root = ET.fromstring(xml)
    except (ET.ParseError, UnicodeError):
        raise UpstreamError('upstream_invalid_xml')
    if local(root.tag) != 'VOTABLE':
        raise UpstreamError('upstream_invalid_schema')
    resources = [e for e in root.iter() if local(e.tag) == 'RESOURCE' and e.get('type') == 'results']
    if len(resources) != 1:
        raise UpstreamError('upstream_invalid_schema')
    resource = resources[0]
    statuses = [e.get('value', '').upper() for e in resource if local(e.tag) == 'INFO' and e.get('name', '').upper() == 'QUERY_STATUS']
    if not statuses or any(s not in ('OK', 'OVERFLOW') for s in statuses):
        raise UpstreamError('upstream_query_error')
    tables = [e for e in resource if local(e.tag) == 'TABLE']
    if len(tables) != 1:
        raise UpstreamError('upstream_invalid_schema')
    table = tables[0]
    fields = [e for e in table if local(e.tag) == 'FIELD']
    names = [e.get('name', '') for e in fields]
    required = {'t_min': 'd', 't_max': 'd', 'em_min': 'm', 'em_max': 'm', 'obs_id': None,
                'energy_bandpassname': None, 's_region': None, 'access_url': None, 'obs_collection': None}
    if len(names) != len(set(names)) or not set(required).issubset(names):
        raise UpstreamError('upstream_invalid_schema')
    for field in fields:
        unit = required.get(field.get('name'))
        if unit and field.get('unit') != unit:
            raise UpstreamError('upstream_invalid_units')
    data = next((e for e in table if local(e.tag) == 'DATA'), None)
    tabledata = next((e for e in data if local(e.tag) == 'TABLEDATA'), None) if data is not None else None
    if tabledata is None:
        raise UpstreamError('upstream_unsupported_format')
    trs = [e for e in tabledata if local(e.tag) == 'TR']
    if len(trs) > MAX_ROWS or len(trs) > p['maxrec']:
        raise UpstreamError('upstream_row_limit')
    rows = []
    collection = 'spherex_' + p['release'] + ('_deep' if p['deep'] else '')
    for tr in trs:
        cells = [e.text or '' for e in tr if local(e.tag) == 'TD']
        if len(cells) != len(names):
            raise UpstreamError('upstream_invalid_schema')
        row = dict(zip(names, cells))
        if row['obs_collection'].lower() != collection:
            raise UpstreamError('upstream_collection_mismatch')
        match = re.fullmatch(r'SPHEREx-D([1-6])', row['energy_bandpassname'], re.I)
        detector = int(match.group(1)) if match else None
        if p['detector'] is not None and detector != p['detector']:
            continue
        def num(name):
            if not row[name].strip():
                return None
            try:
                value = float(row[name])
                if math.isfinite(value):
                    return value
            except ValueError:
                pass
            raise UpstreamError('upstream_invalid_value')
        tmin, tmax, emin, emax = (num(k) for k in ('t_min', 't_max', 'em_min', 'em_max'))
        if (tmin is not None and tmax is not None and tmin > tmax) or (emin is not None and emax is not None and (emin < 0 or emin > emax)):
            raise UpstreamError('upstream_invalid_value')
        rows.append({'obs_id': row['obs_id'] or None, 'detector': detector,
                     'bandpass': row['energy_bandpassname'] or None, 't_min_mjd': tmin, 't_max_mjd': tmax,
                     'em_min_m': emin, 'em_max_m': emax,
                     'wavelength_center_um': (emin + emax) * 0.5e6 if emin is not None and emax is not None else None,
                     'wavelength_width_um': (emax - emin) * 1e6 if emin is not None and emax is not None else None,
                     'footprint': row['s_region'] or None, 'access_url': safe_access_url(row['access_url'], p['release']),
                     'release': p['release']})
    truncated = 'OVERFLOW' in statuses
    return rows, truncated, len(trs)


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, category):
        raw = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Request-ID', self.request_id)
        if status == 405:
            self.send_header('Allow', 'GET')
        if status == 429:
            self.send_header('Retry-After', str(self.retry_after))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(raw)
        logger.warning(json.dumps({'event': 'observations_request', 'request_id': self.request_id,
                                   'status': status, 'category': category,
                                   'latency_ms': round((time.monotonic() - self.started) * 1000, 2)}))

    def dispatch(self, method):
        self.request_id, self.started = secrets.token_hex(16), time.monotonic()
        if method != 'GET':
            return self.reply(405, {'error': 'method_not_allowed'}, 'method')
        try:
            params = parse_params(urlsplit(self.path).query)
            guard('observations', self.headers, self.client_address)
            url = upstream_url(params)
            content = fetch(url)
            retrieved = datetime.now(timezone.utc).isoformat()
            rows, truncated, scanned = parse_votable(content, params)
            state = 'truncated' if truncated else ('ok' if rows else 'no_data')
            return self.reply(200, {'contract_version': '1.0', 'status': state, 'query': params,
                                    'observations': rows, 'returned_count': len(rows), 'upstream_count': scanned,
                                    'truncated': truncated, 'provenance': {'endpoint': ENDPOINT, 'query_url': url,
                                    'response_sha256': sha256(content).hexdigest(), 'retrieved_at': retrieved,
                                    'source_format': 'VOTable TABLEDATA', 'collection': 'spherex_' + params['release'] + ('_deep' if params['deep'] else '')}}, 'ok')
        except AccessDenied as exc:
            self.retry_after = exc.retry_after
            return self.reply(exc.status, {'error': exc.code}, 'rate_limit' if exc.status == 429 else 'rate_unavailable')
        except ValueError as exc:
            return self.reply(400, {'error': str(exc)}, 'validation')
        except UpstreamError as exc:
            return self.reply(504 if exc.code == 'upstream_timeout' else 502, {'error': exc.code}, 'upstream')
        except Exception:
            return self.reply(500, {'error': 'internal_error'}, 'internal')

    def do_GET(self):
        self.dispatch('GET')

    def do_POST(self):
        self.dispatch('POST')

    def do_DELETE(self):
        self.dispatch('DELETE')

    def do_PUT(self):
        self.dispatch('PUT')

    def do_PATCH(self):
        self.dispatch('PATCH')

    def do_HEAD(self):
        self.dispatch('HEAD')

    def do_OPTIONS(self):
        self.dispatch('OPTIONS')

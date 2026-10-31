"""Permit-bound import of public, Git-pinned chunks. Normally disabled.

A short-lived random bearer capability is provisioned via the existing Atlas
connector. Only its hash is stored; no Mongo credential ever leaves production.
Deleting/expiring that permit disables this route. No arbitrary writes/updates.
"""
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler
import base64
import hmac
import json
import os
from pathlib import Path
import re

try:
    from api.data import database, manifest
except ModuleNotFoundError as exc:
    if exc.name not in ('api', 'api.data'):
        raise
    from web.api.data import database, manifest

TOKEN = re.compile(r'^Bearer ([a-zA-Z0-9_-]{43})$')


def permit_id():
    return sha256(Path(__file__).with_name('_data_manifest.json').read_bytes()).hexdigest()


def allowed(headers, db, now=None):
    match = TOKEN.fullmatch(headers.get('Authorization', ''))
    if not match:
        return False
    row = db.public_asset_import_permits.find_one({'_id': permit_id()})
    if not row:
        return False
    current = datetime.now(timezone.utc) if now is None else now
    try:
        expiry = datetime.fromisoformat(row['expires_at'])
        issued = datetime.fromisoformat(row['issued_at'])
        if expiry.tzinfo is None or issued.tzinfo is None or not issued <= current < expiry or not 0 < (expiry - issued).total_seconds() <= 45 * 60:
            return False
        return hmac.compare_digest(sha256(match[1].encode('ascii')).hexdigest(), row['token_sha256'])
    except (KeyError, TypeError, ValueError):
        return False


def put_chunk(db, digest, payload):
    expected = {part['sha256']: part['bytes'] for entry in manifest()['assets'].values() for part in entry['chunks']}
    if digest not in expected or len(payload) != expected[digest] or sha256(payload).hexdigest() != digest:
        raise ValueError('invalid_chunk')
    # Insert only. A later request cannot overwrite an existing row or review.
    encoded = base64.b64encode(payload).decode('ascii')
    db.public_asset_chunks.update_one({'_id': digest}, {'$setOnInsert': {'size_bytes': len(payload),
                                     'payload_b64': encoded}}, upsert=True)
    row = db.public_asset_chunks.find_one({'_id': digest})
    if row.get('size_bytes') != len(payload) or row.get('payload_b64') != encoded:
        raise ValueError('existing_chunk_conflict')


class handler(BaseHTTPRequestHandler):
    def reply(self, status, value):
        body = json.dumps(value, separators=(',', ':')).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-App-Commit', os.environ.get('VERCEL_GIT_COMMIT_SHA', 'local'))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.reply(405, {'error': 'method_not_allowed'})

    def do_POST(self):
        if os.environ.get('VERCEL_ENV') != 'production' or not TOKEN.fullmatch(self.headers.get('Authorization', '')):
            return self.reply(403, {'error': 'import_disabled'})
        try:
            db = database()
            if not allowed(self.headers, db):
                return self.reply(403, {'error': 'import_disabled'})
            length = self.headers.get('Content-Length', '')
            if self.headers.get('Transfer-Encoding') or not re.fullmatch(r'[0-9]{1,7}', length) or not 0 < int(length) <= manifest()['chunk_bytes']:
                return self.reply(413, {'error': 'invalid_chunk_length'})
            if self.headers.get('Content-Type') != 'application/octet-stream':
                return self.reply(400, {'error': 'invalid_content_type'})
            payload = self.rfile.read(int(length))
            put_chunk(db, self.headers.get('X-Data-Chunk-SHA256', ''), payload)
            return self.reply(200, {'uploaded': True, 'bytes': len(payload), 'sha256': sha256(payload).hexdigest()})
        except ValueError:
            return self.reply(400, {'error': 'invalid_or_conflicting_chunk'})
        except Exception:
            return self.reply(503, {'error': 'import_unavailable'})

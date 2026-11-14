"""Manual encrypted review snapshot; restore drills can write only to loopback.

Run with ``python -m scripts.backup_reviews_local snapshot`` on Windows.
Credentials are prompted without echo or read from SPHEREX_BACKUP_MONGODB_URI.
No plaintext snapshot, URI, review content or key is printed or written to disk.
"""
import argparse
import ctypes
from datetime import datetime, timezone
from getpass import getpass, GetPassWarning
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4
from urllib.parse import parse_qs, urlsplit
import warnings

from bson import BSON, ObjectId
from cryptography.fernet import Fernet, InvalidToken
from pymongo import MongoClient, timeout
from pymongo.read_concern import ReadConcern

from scripts import review_backup as fixture

BackupError = fixture.BackupError
CODEC = fixture.CODEC
SOURCE = 'nosleepclub_nasa_spherex'
MAX_DOCUMENTS = 20_000
MAX_BYTES = 128 * 1024 * 1024
MAX_CIPHERTEXT = MAX_BYTES * 4 // 3 + 4096


def validate_documents(documents):
    if not isinstance(documents, list) or len(documents) > MAX_DOCUMENTS:
        raise BackupError('invalid_documents')
    ids, keys, total = set(), set(), 0
    for doc in documents:
        if not isinstance(doc, dict) or not isinstance(doc.get('_id'), (str, ObjectId)):
            raise BackupError('invalid_document')
        if isinstance(doc['_id'], str) and not fixture.OWNER.fullmatch(doc['_id']):
            raise BackupError('invalid_document_id')
        owner, key, expiry = doc.get('owner'), doc.get('key'), doc.get('expires_at')
        if (not isinstance(owner, str) or not fixture.OWNER.fullmatch(owner)
                or not isinstance(key, str) or not fixture.REVIEW_KEY.fullmatch(key)):
            raise BackupError('invalid_document')
        if not isinstance(expiry, datetime) or expiry.utcoffset() != timezone.utc.utcoffset(None):
            raise BackupError('invalid_expiry')
        if doc['_id'] in ids or (owner, key) in keys:
            raise BackupError('duplicate_document')
        ids.add(doc['_id']); keys.add((owner, key))
        fixture._bounded_value(doc, [fixture.MAX_DOCUMENT_BYTES])
        total += len(BSON.encode(doc, codec_options=CODEC))
        if total > MAX_BYTES:
            raise BackupError('snapshot_too_large')


def seal(documents, indexes, key):
    validate_documents(documents)
    indexes = fixture.validate_indexes(indexes)
    now = datetime.now(timezone.utc)
    now = now.replace(microsecond=now.microsecond // 1000 * 1000)
    raw = BSON.encode({'version': 2, 'created_at': now, 'source': SOURCE,
                       'indexes': indexes, 'documents': documents}, codec_options=CODEC)
    if len(raw) > MAX_BYTES:
        raise BackupError('snapshot_too_large')
    return fixture._fernet(key).encrypt(raw)


def unseal(ciphertext, key):
    if not isinstance(ciphertext, bytes) or not 0 < len(ciphertext) <= MAX_CIPHERTEXT:
        raise BackupError('invalid_ciphertext')
    try:
        raw = fixture._fernet(key).decrypt(ciphertext)
    except InvalidToken:
        raise BackupError('authentication_failed') from None
    if len(raw) > MAX_BYTES:
        raise BackupError('snapshot_too_large')
    try:
        value = BSON(raw).decode(codec_options=CODEC)
        if BSON.encode(value, codec_options=CODEC) != raw:
            raise ValueError()
    except Exception:
        raise BackupError('invalid_snapshot') from None
    if (set(value) != {'version', 'created_at', 'source', 'indexes', 'documents'}
            or type(value['version']) is not int or value['version'] != 2 or value['source'] != SOURCE
            or not isinstance(value['created_at'], datetime)
            or value['created_at'].utcoffset() != timezone.utc.utcoffset(None)):
        raise BackupError('invalid_snapshot')
    fixture.validate_indexes(value['indexes'])
    validate_documents(value['documents'])
    return value


def snapshot_reviews(uri, key):
    # The production source is the existing Atlas database only. Never infer a DB.
    if not isinstance(uri, str) or not uri.startswith('mongodb+srv://'):
        raise BackupError('atlas_uri_required')
    try:
        options = {name.lower() for name in parse_qs(urlsplit(uri).query)}
    except ValueError:
        raise BackupError('invalid_source_uri') from None
    if options & {'tlsinsecure', 'tlsallowinvalidcertificates', 'tlsallowinvalidhostnames'}:
        raise BackupError('insecure_tls_options')
    client = None
    try:
        client = MongoClient(uri, tls=True, serverSelectionTimeoutMS=5000,
                             connectTimeoutMS=5000, socketTimeoutMS=10000, tz_aware=True)
        db = client.get_default_database()
        if db.name != SOURCE:
            raise BackupError('unexpected_source_database')
        with timeout(45):
            indexes = fixture._read_indexes(db.reviews)
            documents, size = [], 0
            with client.start_session() as session:
                with session.start_transaction(read_concern=ReadConcern('snapshot')):
                    for row in db.reviews.find({}, session=session).limit(MAX_DOCUMENTS + 1).batch_size(100):
                        if len(documents) >= MAX_DOCUMENTS:
                            raise BackupError('document_limit_exceeded')
                        fixture._bounded_value(row, [fixture.MAX_DOCUMENT_BYTES])
                        size += len(BSON.encode(row, codec_options=CODEC))
                        if size > MAX_BYTES:
                            raise BackupError('snapshot_too_large')
                        documents.append(row)
            # Detect an index change during the read instead of exporting a mixed contract.
            if fixture._read_indexes(db.reviews) != indexes:
                raise BackupError('indexes_changed')
            return seal(documents, indexes, key)
    except BackupError:
        raise
    except Exception:
        raise BackupError('snapshot_failed') from None
    finally:
        if client is not None:
            client.close()


def _digest(documents):
    digest = sha256()
    for doc in sorted(documents, key=lambda row: str(row['_id'])):
        digest.update(BSON.encode(doc, codec_options=CODEC))
    return digest.digest()


def restore_drill(uri, ciphertext, key, target_name=None):
    fixture.validate_uri(uri)
    value = unseal(ciphertext, key)  # Authenticate before any connection or write.
    target = target_name or 'review_backup_dst_' + uuid4().hex
    fixture.validate_name(target, source=False)
    client = fixture._fixture_client(uri)
    try:
        with timeout(45):
            if fixture.database_exists(client, target):
                raise BackupError('target_exists')
            db = client[target]
            collection = db.create_collection('reviews')
            collection.create_index([('owner', 1), ('key', 1)], unique=True, name='owner_1_key_1')
            now = datetime.now(timezone.utc)
            live = [doc for doc in value['documents'] if doc['expires_at'] > now]
            if live:
                collection.insert_many(live, ordered=True)
            restored = list(collection.find({}).limit(MAX_DOCUMENTS + 1))
            if len(restored) != len(live) or _digest(restored) != _digest(live):
                raise BackupError('restore_verification_failed')
            # Enable TTL only after comparison so the monitor cannot race the digest.
            collection.create_index('expires_at', expireAfterSeconds=0, name='expires_at_1')
            fixture._read_indexes(collection)
            return {'target_database': target, 'restored_count': len(live),
                    'excluded_expired_count': len(value['documents']) - len(live),
                    'bson_verified': True, 'indexes_verified': True}
    except BackupError:
        raise
    except Exception:
        raise BackupError('restore_failed') from None
    finally:
        client.close()


def dpapi(data, protect):
    if os.name != 'nt':
        raise BackupError('windows_dpapi_required')
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    fn = crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob),
                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    # UI_FORBIDDEN only: do not use LOCAL_MACHINE, which would allow other users.
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise BackupError('dpapi_failed')
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)


def backup_directory():
    base = os.environ.get('LOCALAPPDATA')
    if os.name != 'nt' or not base:
        raise BackupError('windows_localappdata_required')
    folder = (Path(base) / 'SPHEREx' / 'backups').resolve()
    repo = Path(__file__).resolve().parents[1]
    if folder.is_relative_to(repo):
        raise BackupError('backup_directory_in_repository')
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def load_key(folder, create=False):
    path = folder / 'review-key.dpapi'
    if create and not path.exists():
        key = Fernet.generate_key()
        protected = dpapi(key, True)
        try:
            with path.open('xb') as stream:
                stream.write(protected)
        except FileExistsError:
            pass  # Another local invocation won; use its key.
    if not path.exists() or path.stat().st_size > 16384:
        raise BackupError('protected_key_missing')
    key = dpapi(path.read_bytes(), False)
    fixture._fernet(key)
    return key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['snapshot', 'verify', 'restore-drill'])
    parser.add_argument('--file', help='Snapshot filename within the local backup folder')
    parser.add_argument('--local-port', type=int, default=27027, help='Loopback replica set codex-review-test')
    args = parser.parse_args()
    try:
        folder = backup_directory()
        key = load_key(folder, create=args.action == 'snapshot')
        if args.action == 'snapshot':
            uri = os.environ.get('SPHEREX_BACKUP_MONGODB_URI')
            if not uri:
                with warnings.catch_warnings():
                    warnings.simplefilter('error', GetPassWarning)
                    uri = getpass('Existing Atlas URI (hidden): ')
            ciphertext = snapshot_reviews(uri, key)
            name = datetime.now(timezone.utc).strftime('reviews-%Y%m%dT%H%M%SZ-') + uuid4().hex[:8] + '.spherex.enc'
            path = folder / name
            with path.open('xb') as stream:
                stream.write(ciphertext)
        else:
            if not args.file or Path(args.file).name != args.file or not args.file.endswith('.spherex.enc'):
                raise BackupError('invalid_snapshot_filename')
            path = (folder / args.file).resolve()
            if path.parent != folder or path.stat().st_size > MAX_CIPHERTEXT:
                raise BackupError('invalid_snapshot_file')
            ciphertext = path.read_bytes()
        value = unseal(ciphertext, key)
        receipt = {'action': args.action, 'file': path.name, 'ciphertext_sha256': sha256(ciphertext).hexdigest(),
                   'document_count': len(value['documents']), 'created_at_utc': value['created_at'].isoformat()}
        if args.action == 'restore-drill':
            receipt.update(restore_drill(f'mongodb://127.0.0.1:{args.local_port}/?directConnection=true', ciphertext, key))
        print(json.dumps(receipt))
        return 0
    except BackupError as exc:
        print(json.dumps({'error': str(exc)}))
    except (Exception, KeyboardInterrupt):
        print(json.dumps({'error': 'backup_operation_failed'}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())

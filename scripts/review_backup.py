"""Encrypted BSON snapshots for disposable synthetic loopback review databases only.

There is deliberately no CLI, production connector, key storage, or cleanup API.
"""
from datetime import datetime, timezone
import re
from uuid import UUID

from bson import BSON
from bson.binary import Binary
from bson.codec_options import CodecOptions
from bson.decimal128 import Decimal128
from bson.objectid import ObjectId
from bson.timestamp import Timestamp
from cryptography.fernet import Fernet, InvalidToken
from pymongo import MongoClient, timeout
from pymongo.read_concern import ReadConcern

MAX_DOCUMENTS = 500
MAX_DOCUMENT_BYTES = 32_768
MAX_PLAINTEXT_BYTES = 2_000_000
MAX_CIPHERTEXT_BYTES = 3_000_000
SCHEMA_VERSION = 1
CODEC = CodecOptions(tz_aware=True, tzinfo=timezone.utc)
OWNER = re.compile(r'^[a-f0-9]{64}$')
REVIEW_KEY = re.compile(r'^[a-f0-9]{64}:[A-Za-z0-9_.-]{1,128}:[A-Za-z0-9_.-]{1,128}$')
SOURCE_NAME = re.compile(r'^review_backup_src_([a-f0-9]{32})$')
TARGET_NAME = re.compile(r'^review_backup_dst_([a-f0-9]{32})$')
URI = re.compile(r'^mongodb://127\.0\.0\.1:([1-9][0-9]{0,4})/\?directConnection=true$')
REQUIRED_INDEXES = (
    {'name': 'owner_1_key_1', 'key': [['owner', 1], ['key', 1]], 'unique': True},
    {'name': 'expires_at_1', 'key': [['expires_at', 1]], 'expireAfterSeconds': 0},
)


class BackupError(Exception):
    """A sanitized failure code; never embed input, URI, key, or review contents."""


def validate_uri(uri):
    match = URI.fullmatch(uri) if isinstance(uri, str) else None
    if not match or int(match.group(1)) > 65535:
        raise BackupError('invalid_fixture_uri')
    return uri


def validate_name(name, source):
    match = (SOURCE_NAME if source else TARGET_NAME).fullmatch(name) if isinstance(name, str) else None
    if not match or UUID(hex=match.group(1)).version != 4:
        raise BackupError('invalid_fixture_database')
    return name


def validate_indexes(indexes):
    if not isinstance(indexes, list) or len(indexes) != len(REQUIRED_INDEXES):
        raise BackupError('invalid_indexes')
    seen = set()
    for index in indexes:
        if not isinstance(index, dict) or not isinstance(index.get('name'), str) or index['name'] in seen:
            raise BackupError('invalid_indexes')
        seen.add(index['name'])
        expected = next((entry for entry in REQUIRED_INDEXES if entry['name'] == index['name']), None)
        if expected is None or set(index) != set(expected) or index.get('key') != expected['key']:
            raise BackupError('invalid_indexes')
        if any(type(pair[1]) is not int for pair in index['key']):
            raise BackupError('invalid_indexes')
        if 'unique' in expected and index['unique'] is not True:
            raise BackupError('invalid_indexes')
        if 'expireAfterSeconds' in expected and (type(index['expireAfterSeconds']) is not int or index['expireAfterSeconds'] != 0):
            raise BackupError('invalid_indexes')
    return [dict(entry) for entry in REQUIRED_INDEXES]


def _bounded_value(value, budget, depth=0):
    """Reject large/nested input before asking BSON to allocate an encoding."""
    if depth > 30:
        raise BackupError('invalid_document')
    budget[0] -= 16
    if isinstance(value, str):
        if len(value) > MAX_DOCUMENT_BYTES:
            raise BackupError('document_too_large')
        try:
            budget[0] -= len(value.encode('utf-8'))
        except UnicodeError:
            raise BackupError('invalid_document') from None
    elif isinstance(value, (bytes, Binary)):
        budget[0] -= len(value)
    elif isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timedelta_zero() or value.microsecond % 1000:
            raise BackupError('invalid_document')
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise BackupError('invalid_document')
            _bounded_value(key, budget, depth + 1)
            _bounded_value(item, budget, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _bounded_value(item, budget, depth + 1)
    elif value is not None and not isinstance(value, (int, float, bool, ObjectId, Decimal128, Timestamp)):
        raise BackupError('unsupported_bson_type')
    if budget[0] < 0:
        raise BackupError('document_too_large')


def validate_documents(documents):
    if not isinstance(documents, list) or len(documents) > MAX_DOCUMENTS:
        raise BackupError('invalid_documents')
    ids, keys, total = set(), set(), 0
    for doc in documents:
        if not isinstance(doc, dict) or not isinstance(doc.get('_id'), ObjectId):
            raise BackupError('invalid_document')
        owner, key, expires = doc.get('owner'), doc.get('key'), doc.get('expires_at')
        if not isinstance(owner, str) or not OWNER.fullmatch(owner) or not isinstance(key, str) or not REVIEW_KEY.fullmatch(key):
            raise BackupError('invalid_document')
        if not isinstance(expires, datetime) or expires.tzinfo is None or expires.utcoffset() != timedelta_zero():
            raise BackupError('invalid_expiry')
        if expires.microsecond % 1000:
            raise BackupError('invalid_expiry')
        identity = (owner, key)
        if doc['_id'] in ids or identity in keys:
            raise BackupError('duplicate_document')
        ids.add(doc['_id']); keys.add(identity)
        _bounded_value(doc, [MAX_DOCUMENT_BYTES])
        try:
            size = len(BSON.encode(doc, codec_options=CODEC))
        except Exception:
            raise BackupError('invalid_document') from None
        if size > MAX_DOCUMENT_BYTES:
            raise BackupError('document_too_large')
        total += size
        if total > MAX_PLAINTEXT_BYTES:
            raise BackupError('snapshot_too_large')
    return documents


def timedelta_zero():
    # Equality with this UTC offset also accepts a fixed +00:00 tzinfo.
    return timezone.utc.utcoffset(None)


def _fernet(key):
    try:
        if not isinstance(key, bytes):
            raise ValueError('invalid key')
        return Fernet(key)
    except Exception:
        raise BackupError('invalid_key') from None


def seal_snapshot(documents, indexes, key):
    fernet = _fernet(key)
    indexes = validate_indexes(indexes)
    validate_documents(documents)
    created = datetime.now(timezone.utc)
    created = created.replace(microsecond=(created.microsecond // 1000) * 1000)
    try:
        plaintext = BSON.encode({'version': SCHEMA_VERSION, 'created_at': created,
                                 'indexes': indexes, 'documents': documents}, codec_options=CODEC)
    except Exception:
        raise BackupError('invalid_snapshot') from None
    if len(plaintext) > MAX_PLAINTEXT_BYTES:
        raise BackupError('snapshot_too_large')
    ciphertext = fernet.encrypt(plaintext)
    if len(ciphertext) > MAX_CIPHERTEXT_BYTES:
        raise BackupError('snapshot_too_large')
    return ciphertext


def open_snapshot(ciphertext, key):
    if not isinstance(ciphertext, bytes) or not 0 < len(ciphertext) <= MAX_CIPHERTEXT_BYTES:
        raise BackupError('invalid_ciphertext')
    fernet = _fernet(key)
    try:
        plaintext = fernet.decrypt(ciphertext)
    except InvalidToken:
        raise BackupError('authentication_failed') from None
    if len(plaintext) > MAX_PLAINTEXT_BYTES:
        raise BackupError('snapshot_too_large')
    try:
        decoded = BSON(plaintext).decode(codec_options=CODEC)
        # Reject duplicate BSON fields and noncanonical encodings before any writes.
        if BSON.encode(decoded, codec_options=CODEC) != plaintext:
            raise ValueError('noncanonical BSON')
    except Exception:
        raise BackupError('invalid_snapshot') from None
    if set(decoded) != {'version', 'created_at', 'indexes', 'documents'} or type(decoded['version']) is not int or decoded['version'] != SCHEMA_VERSION:
        raise BackupError('invalid_snapshot')
    created = decoded['created_at']
    if not isinstance(created, datetime) or created.tzinfo is None or created.utcoffset() != timedelta_zero():
        raise BackupError('invalid_snapshot')
    validate_indexes(decoded['indexes'])
    validate_documents(decoded['documents'])
    return decoded


def _fixture_client(uri):
    validate_uri(uri)
    client = MongoClient(uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000,
                         socketTimeoutMS=5000, tz_aware=True, tzinfo=timezone.utc)
    try:
        hello = client.admin.command('hello')
        if hello.get('setName') != 'codex-review-test' or not hello.get('isWritablePrimary'):
            raise BackupError('invalid_fixture_server')
        return client
    except Exception:
        client.close()
        raise BackupError('fixture_unavailable') from None


def _read_indexes(collection):
    entries, seen = [], set()
    for index in collection.list_indexes():
        allowed = {'v', 'name', 'key', 'unique', 'expireAfterSeconds', 'ns'}
        if set(index) - allowed:
            raise BackupError('invalid_indexes')
        name, pairs = index.get('name'), [[name, direction] for name, direction in index['key'].items()]
        if not isinstance(name, str) or name in seen:
            raise BackupError('invalid_indexes')
        seen.add(name)
        if name == '_id_':
            if pairs != [['_id', 1]] or type(pairs[0][1]) is not int or type(index.get('unique', False)) is not bool or 'expireAfterSeconds' in index:
                raise BackupError('invalid_indexes')
            continue
        entry = {'name': name, 'key': pairs}
        if 'unique' in index:
            entry['unique'] = index['unique']
        if 'expireAfterSeconds' in index:
            entry['expireAfterSeconds'] = index['expireAfterSeconds']
        entries.append(entry)
    if '_id_' not in seen:
        raise BackupError('invalid_indexes')
    return validate_indexes(entries)


def database_exists(client, name):
    # list_database_names has no filter keyword in the pinned PyMongo driver.
    with client.list_databases(filter={'name': name}, nameOnly=True) as cursor:
        return any(row.get('name') == name for row in cursor)


def snapshot_fixture(uri, source_name, key):
    validate_uri(uri); validate_name(source_name, source=True); _fernet(key)
    client = _fixture_client(uri)
    try:
        with timeout(10):
            if not database_exists(client, source_name):
                raise BackupError('source_missing')
            db = client[source_name]
            if db.list_collection_names() != ['reviews']:
                raise BackupError('unsupported_source')
            indexes = _read_indexes(db.reviews)
            documents, size = [], 0
            with client.start_session() as session:
                with session.start_transaction(read_concern=ReadConcern('snapshot')):
                    for row in db.reviews.find({}, session=session).limit(MAX_DOCUMENTS + 1).batch_size(20):
                        if len(documents) >= MAX_DOCUMENTS:
                            raise BackupError('invalid_documents')
                        _bounded_value(row, [MAX_DOCUMENT_BYTES])
                        raw = BSON.encode(row, codec_options=CODEC)
                        if len(raw) > MAX_DOCUMENT_BYTES:
                            raise BackupError('document_too_large')
                        size += len(raw)
                        if size > MAX_PLAINTEXT_BYTES:
                            raise BackupError('snapshot_too_large')
                        documents.append(row)
            return seal_snapshot(documents, indexes, key)
    except BackupError:
        raise
    except Exception:
        raise BackupError('snapshot_failed') from None
    finally:
        client.close()


def restore_fixture(uri, target_name, ciphertext, key):
    validate_uri(uri); validate_name(target_name, source=False)
    snapshot = open_snapshot(ciphertext, key)  # Authenticate and validate before any DB connection/write.
    client = _fixture_client(uri)
    try:
        with timeout(10):
            if database_exists(client, target_name):
                raise BackupError('target_exists')
            db = client[target_name]
            collection = db.create_collection('reviews')
            if db.list_collection_names() != ['reviews']:
                raise BackupError('target_not_empty')
            if collection.count_documents({}, limit=1) != 0:
                raise BackupError('target_not_empty')
            collection.create_index([('owner', 1), ('key', 1)], unique=True, name='owner_1_key_1')
            collection.create_index('expires_at', expireAfterSeconds=0, name='expires_at_1')
            now = datetime.now(timezone.utc)
            live = [doc for doc in snapshot['documents'] if doc['expires_at'] > now]
            if live:
                with client.start_session() as session:
                    with session.start_transaction():
                        collection.insert_many(live, ordered=True, session=session)
            return {'snapshot_version': SCHEMA_VERSION, 'restored_count': len(live),
                    'excluded_expired_count': len(snapshot['documents']) - len(live)}
    except BackupError:
        raise
    except Exception:
        raise BackupError('restore_failed') from None
    finally:
        client.close()

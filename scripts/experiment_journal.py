"""Immutable, per-record JSON journal for a fixed local experiment.

Each published record is atomic and protected by a per-key OS lock. Checksums
detect accidental changes, not a malicious party able to rewrite checksums.
Directory-wide enumeration is intended after writers are idle; an active
atomic temporary file may cause the conservative unexpected-file check to fail.
"""
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
import re
import time

from . import science_jobs


SCHEMA = 'experiment-journal-1'
RESERVED = frozenset({'schema', 'identity_sha256', 'key', 'payload', 'checksum'})


def _json_copy(value):
    """Validate strict JSON-compatible data and detach caller-owned objects."""
    def check(item):
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise ValueError('JSON object keys must be strings')
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
        elif item is not None and not isinstance(item, (str, bool, int, float)):
            raise ValueError('value is not JSON-compatible')
    check(value)
    try:
        return json.loads(science_jobs.encode(value))
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError('value is not finite JSON-compatible data') from exc


def _digest(value):
    return sha256(science_jobs.encode(value)).hexdigest()


def _seal(value):
    return {**value, 'checksum': _digest(value)}


def _load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON field')
            result[key] = value
        return result
    if path.is_symlink() or not path.is_file():
        raise ValueError('journal file missing or not a regular file')
    try:
        value = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        if not isinstance(value, dict) or not isinstance(value.get('checksum'), str):
            raise ValueError('missing checksum')
        body = {key: item for key, item in value.items() if key != 'checksum'}
        if _digest(body) != value['checksum']:
            raise ValueError('checksum mismatch')
        return value
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValueError(f'corrupt journal file: {path.name}') from exc


def _key(value):
    if not isinstance(value, tuple) or not value or any(not isinstance(part, str) or not part for part in value):
        raise ValueError('key must be a nonempty tuple of nonempty strings')
    return value


def _remove_temps(directory, target_name):
    """Remove only interrupted atomic temporaries while holding the target lock."""
    pattern = re.compile(r'^\.' + re.escape(target_name) + r'\.[0-9a-f]{32}\.tmp$')
    for path in directory.glob('.' + target_name + '.*.tmp'):
        if pattern.fullmatch(path.name):
            if path.is_symlink() or not path.is_file():
                raise ValueError('invalid atomic temporary')
            path.unlink()


@contextmanager
def _retry_lock(directory, name, timeout=5.):
    deadline = time.monotonic() + timeout
    while True:
        manager = science_jobs.locked(directory, name)
        try:
            manager.__enter__()
            break
        except RuntimeError as exc:
            if str(exc) != 'job already claimed' or time.monotonic() >= deadline:
                raise
            time.sleep(.025)
    try:
        yield
    finally:
        manager.__exit__(None, None, None)


class Journal:
    """A fixed set of keys, each accepting exactly one terminal payload."""

    def __init__(self, directory, identity, expected_keys, terminal_statuses):
        if not isinstance(identity, dict) or not identity:
            raise ValueError('identity must be a nonempty JSON object')
        identity = _json_copy(identity)
        keys = tuple(_key(key) for key in expected_keys)
        if not keys or len(set(keys)) != len(keys):
            raise ValueError('expected keys must be nonempty and unique')
        statuses = tuple(terminal_statuses)
        if (not statuses or any(not isinstance(s, str) or not s for s in statuses)
                or len(statuses) != len(set(statuses))):
            raise ValueError('terminal statuses must be nonempty and unique')
        self.directory = Path(directory)
        self._records = self.directory / 'records'
        self._locks = self.directory / 'locks'
        self.directory.mkdir(parents=True, exist_ok=True)
        self._records.mkdir(exist_ok=True)
        self._locks.mkdir(exist_ok=True)
        if self.directory.is_symlink() or self._records.is_symlink() or self._locks.is_symlink():
            raise ValueError('journal directories must not be symlinks')
        self.identity_sha256 = _digest(identity)
        self._keys = keys
        self._key_set = frozenset(keys)
        self._statuses = frozenset(statuses)
        self._filenames = {_digest(list(key)) + '.json': key for key in keys}
        if len(self._filenames) != len(keys):
            raise ValueError('key digest collision')
        header_body = {'schema': SCHEMA, 'identity': identity, 'identity_sha256': self.identity_sha256,
                       'expected_keys': [list(key) for key in keys], 'terminal_statuses': list(statuses)}
        self._header = _seal(header_body)
        header_path = self.directory / 'header.json'
        with _retry_lock(self.directory, '.header.lock'):
            _remove_temps(self.directory, 'header.json')
            if header_path.exists() or header_path.is_symlink():
                if _load(header_path) != self._header:
                    raise ValueError('journal header identity, keys, or statuses differ')
            else:
                if any(self._records.iterdir()) or any(self._locks.iterdir()):
                    raise ValueError('incomplete journal has existing records or locks')
                science_jobs.atomic(header_path, self._header)
        self._header_signature = self._signature()
        # A terminated process may have left an atomic temp before its rename.
        # Scan once on opening, not once per write, to keep work linear.
        pattern = re.compile(r'^\.([0-9a-f]{64})\.json\.[0-9a-f]{32}\.tmp$')
        for path in self._records.iterdir():
            match = pattern.fullmatch(path.name)
            if match and match.group(1) + '.json' in self._filenames:
                with _retry_lock(self._locks, match.group(1) + '.lock'):
                    if path.is_symlink():
                        raise ValueError('invalid atomic temporary')
                    if path.exists():
                        if not path.is_file():
                            raise ValueError('invalid atomic temporary')
                        path.unlink()

    def _signature(self):
        path = self.directory / 'header.json'
        if path.is_symlink():
            raise ValueError('invalid journal header')
        try:
            stat = path.stat()
        except OSError as exc:
            raise ValueError('missing journal header') from exc
        return (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino)

    def _check_header(self):
        signature = self._signature()
        if signature != self._header_signature:
            if _load(self.directory / 'header.json') != self._header:
                raise ValueError('journal header changed')
            self._header_signature = signature

    def _record_path(self, key):
        key = _key(key)
        if key not in self._key_set:
            raise ValueError('unknown journal key')
        return self._records / (_digest(list(key)) + '.json')

    def _validate_payload(self, payload):
        if not isinstance(payload, dict) or RESERVED.intersection(payload):
            raise ValueError('payload must be an object without reserved fields')
        payload = _json_copy(payload)
        status = payload.get('status')
        if not isinstance(status, str) or status not in self._statuses:
            raise ValueError('payload status is not terminal')
        if any(word in status.lower() for word in ('failed', 'failure', 'error')) and (
                not isinstance(payload.get('error'), str) or not payload['error'].strip()):
            raise ValueError('failure requires a nonempty error string')
        return payload

    def read(self, key):
        self._check_header()
        path = self._record_path(key)
        if not path.exists() and not path.is_symlink():
            return None
        value = _load(path)
        if (set(value) != RESERVED or value['schema'] != SCHEMA
                or value['identity_sha256'] != self.identity_sha256 or value['key'] != list(key)):
            raise ValueError('record envelope identity or key mismatch')
        self._validate_payload(value['payload'])
        return value

    def write(self, key, payload):
        self._check_header()
        path = self._record_path(key)
        payload = self._validate_payload(payload)
        envelope = _seal({'schema': SCHEMA, 'identity_sha256': self.identity_sha256,
                          'key': list(key), 'payload': payload})
        with _retry_lock(self._locks, path.stem + '.lock'):
            existing = self.read(key)
            if existing is not None:
                if existing != envelope:
                    raise ValueError('terminal record already exists with different payload')
                return existing
            science_jobs.atomic(path, envelope)
            return self.read(key)

    def records(self, require_complete=False):
        self._check_header()
        allowed_root = {'header.json', '.header.lock', 'records', 'locks'}
        for entry in self.directory.iterdir():
            if entry.is_symlink() or entry.name not in allowed_root:
                raise ValueError('unexpected file in journal directory')
        valid_locks = {name[:-5] + '.lock' for name in self._filenames}
        for entry in self._locks.iterdir():
            if entry.is_symlink() or not entry.is_file() or entry.name not in valid_locks:
                raise ValueError('unexpected file in locks directory')
        for entry in self._records.iterdir():
            if entry.is_symlink() or not entry.is_file() or entry.name not in self._filenames:
                raise ValueError('unexpected file in records directory')
        items = [item for key in self._keys if (item := self.read(key)) is not None]
        if require_complete and len(items) != len(self._keys):
            raise ValueError('journal is incomplete')
        return items

    def counts(self):
        items = self.records()
        counts = {status: 0 for status in sorted(self._statuses)}
        for item in items:
            counts[item['payload']['status']] += 1
        return {'expected': len(self._keys), 'recorded': len(items),
                'missing': len(self._keys) - len(items), 'statuses': counts}

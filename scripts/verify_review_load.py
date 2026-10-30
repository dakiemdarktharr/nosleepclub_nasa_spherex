"""Preregister and run one bounded, disposable-guest review API baseline."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import threading
import time
import uuid

import requests
import truststore

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://nosleepclub-nasa-spherex.vercel.app'
COMMIT = '80324933bfab21a73a0a2e3f05c447b99f2a81d2'
DESIGN = ROOT / 'docs/evidence/0.10/review-load-design.json'
SOURCES = ('scripts/verify_review_load.py', 'tests/test_review_load.py', 'docs/REVIEW_LOAD_PROTOCOL.md')
HEX = re.compile(r'^[a-f0-9]{64}$')
REQUEST_ID = re.compile(r'^[a-f0-9]{32}$')
RULES = {'owners': 12, 'groups': 4, 'group_size': 3, 'waves': 5,
         'wave_spacing_seconds': 6, 'maximum_inflight': 3, 'maximum_posts': 12,
         'request_cap': 84, 'timeout_connect_seconds': 5, 'timeout_read_seconds': 20,
         'p95_get_seconds': 3, 'p95_write_seconds': 5}


def digest(data):
    return sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def source_hashes():
    return {p: digest((ROOT / p).read_bytes()) for p in SOURCES}


def design_value():
    return {'schema_version': 1, 'target': BASE, 'expected_commit': COMMIT,
            'sources_sha256': source_hashes(), 'rules': RULES,
            'qualification': 'Modest baseline; no throughput, availability, failover or recovery claim.'}


def check_committed():
    design_bytes = DESIGN.read_bytes()
    if json.loads(design_bytes) != design_value():
        raise RuntimeError('design_mismatch')
    for path in (*SOURCES, DESIGN.relative_to(ROOT).as_posix()):
        if (ROOT / path).read_bytes() != git('show', 'HEAD:' + path):
            raise RuntimeError('uncommitted_or_changed_design_source')
    return digest(design_bytes)


def percentile(values):
    return sorted(values)[math.ceil(.95 * len(values)) - 1] if values else None


class Runner:
    def __init__(self, manifest, session_factory=requests.Session, clock=time.monotonic, sleep=time.sleep):
        self.clock, self.sleep = clock, sleep
        self.records, self.owners, self.scopes = [], [], {}
        self.lock = threading.Lock()
        self.last_wave = None
        self.errors, self.fatal = 0, False
        scenes = [s for s in manifest['scenes'] if (s.get('motion') or {}).get('spectral_configuration') == 'strict']
        if not scenes or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', scenes[0]['id']) or not HEX.fullmatch(manifest['analysis_sha256']):
            raise ValueError('invalid_manifest')
        self.item = {'scene_id': scenes[0]['id'], 'selection': 'target', 'status': 'uncertain',
                     'analysis_sha256': manifest['analysis_sha256']}
        self.provenance = {'input_sha256': [scenes[0]['before']['sha256'], scenes[0]['after']['sha256']],
                           'target_detection': scenes[0]['target_detection']}
        if not all(isinstance(v, str) and HEX.fullmatch(v) for v in self.provenance['input_sha256']):
            raise ValueError('invalid_manifest')
        for i in range(RULES['owners']):
            session = session_factory()
            session.trust_env = False
            self.owners.append({'number': i, 'session': session, 'note': 'Disposable review load QA ' + uuid.uuid4().hex,
                                'scope': None, 'id': None, 'safe': False, 'touched': False,
                                'active': True, 'clean': False})

    def wave(self, tasks):
        if not tasks:
            return []
        if self.last_wave is not None:
            self.sleep(max(0, RULES['wave_spacing_seconds'] - (self.clock() - self.last_wave)))
        with ThreadPoolExecutor(max_workers=RULES['maximum_inflight']) as pool:
            results = list(pool.map(lambda t: self.request(*t), tasks))
        self.last_wave = self.clock()
        return results

    def request(self, owner, method, stage, payload=None):
        with self.lock:
            if len(self.records) >= RULES['request_cap']:
                self.fatal = True
                return None
            rec = {'owner': owner['number'], 'method': method, 'stage': stage,
                   'phase': 'cleanup' if stage.startswith('cleanup') else 'planned',
                   'status': None, 'request_id': None, 'error': None, 'latency_seconds': None,
                   'started_monotonic_seconds': None}
            self.records.append(rec)
        start = self.clock()
        rec['started_monotonic_seconds'] = start
        try:
            kwargs = {'timeout': (5, 20), 'allow_redirects': False, 'verify': True}
            if payload is not None:
                kwargs.update(json=payload, headers={'Origin': BASE})
            response = owner['session'].request(method, BASE + '/api/reviews', **kwargs)
            rec['status'] = response.status_code
            rid = response.headers.get('X-Request-ID', '')
            if REQUEST_ID.fullmatch(rid):
                rec['request_id'] = rid
            if response.headers.get('X-App-Commit') != COMMIT:
                rec['error'] = 'commit_mismatch'
            elif response.status_code != 200:
                rec['error'] = 'unexpected_status'
            elif rec['request_id'] is None:
                rec['error'] = 'invalid_request_id'
            else:
                try:
                    body = response.json()
                    if not isinstance(body, dict):
                        raise ValueError()
                except (ValueError, TypeError):
                    rec['error'] = 'invalid_json'
                    body = None
                if body is not None:
                    return rec, body, response.headers
        except requests.RequestException:
            rec['error'] = 'transport_error'
        except Exception:
            rec['error'] = 'client_error'
        finally:
            rec['latency_seconds'] = max(0, self.clock() - start)
        return rec, None, {}

    def validate(self, owner, result, stage):
        if result is None:
            return False
        rec, body, headers = result
        if rec['error']:
            if rec['error'] in ('commit_mismatch', 'client_error', 'invalid_request_id', 'invalid_json'):
                self.fatal = True
            else:
                self.errors += 1
            owner['active'] = False
            return False
        try:
            if stage in ('initial', 'readback', 'final', 'cleanup_get', 'cleanup_verify'):
                scope = body.get('session_scope')
                assert body.get('storage') == 'mongodb' and body.get('contract_version') == '1.1'
                assert isinstance(scope, str) and HEX.fullmatch(scope)
                rows = body.get('reviews')
                assert isinstance(rows, list)
                if stage == 'initial':
                    cookie = headers.get('Set-Cookie', '')
                    assert all(x in cookie for x in ('__Host-spherex-review=', 'Secure', 'HttpOnly', 'SameSite=Strict'))
                    assert not rows
                    owner['scope'] = scope
                    owner['safe'] = True
                    if scope in self.scopes:
                        self.scopes[scope]['safe'] = False
                        self.scopes[scope]['active'] = False
                        owner['safe'] = False
                        raise ValueError('owner_collision')
                    self.scopes[scope] = owner
                else:
                    assert scope == owner['scope']
                    if stage in ('final', 'cleanup_verify'):
                        assert not rows
                        owner['clean'] = True
                    elif stage == 'readback':
                        assert len(rows) == 1 and self.valid_row(owner, rows[0]) and rows[0]['review_id'] == owner['id']
            elif stage == 'post':
                assert body.get('saved') is True and body.get('storage') == 'mongodb' and body.get('contract_version') == '1.1'
                assert body.get('session_scope') == owner['scope'] and self.valid_row(owner, body.get('review'))
                owner['id'] = body['review']['review_id']
            else:
                assert body.get('deleted') is True
            return True
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            rec['error'] = 'owner_collision' if isinstance(exc, ValueError) else 'contract_or_scope_violation'
            owner['active'] = False
            self.fatal = True
            return False

    def own_row(self, owner, row):
        return (isinstance(row, dict) and all(row.get(k) == v for k, v in self.item.items())
                and row.get('note') == owner['note'] and isinstance(row.get('review_id'), str)
                and HEX.fullmatch(row['review_id']) is not None)

    def valid_row(self, owner, row):
        if not self.own_row(owner, row) or any(row.get(k) != v for k, v in self.provenance.items()):
            return False
        try:
            expires = datetime.fromisoformat(row['expires_at'].replace('Z', '+00:00'))
            remaining = (expires - datetime.now(timezone.utc)).total_seconds()
            return 0 < remaining <= 181 * 86400
        except (KeyError, ValueError, TypeError, AttributeError):
            return False

    def cleanup(self, group):
        # A timeout can commit: inspect only sessions established empty and touched by us.
        pending = [o for o in group if o['safe'] and o['touched'] and not o['clean']]
        for owner in pending:
            result = self.wave([(owner, 'GET', 'cleanup_get')])[0]
            if not self.validate(owner, result, 'cleanup_get'):
                continue
            rows = result[1]['reviews']
            if not rows:
                owner['clean'] = True
                continue
            # Never delete anything other than the exact disposable row.
            if len(rows) != 1 or not self.own_row(owner, rows[0]):
                result[0]['error'] = 'cleanup_unrecognized_row'
                self.fatal = True
                continue
            result = self.wave([(owner, 'DELETE', 'cleanup_delete', {'review_id': rows[0]['review_id']})])[0]
            self.validate(owner, result, 'cleanup_delete')
            # DELETE itself can time out after committing; independently verify.
            result = self.wave([(owner, 'GET', 'cleanup_verify')])[0]
            self.validate(owner, result, 'cleanup_verify')

    def run(self):
        try:
            for start in range(0, RULES['owners'], RULES['group_size']):
                group = self.owners[start:start + RULES['group_size']]
                try:
                    for stage, method in (('initial', 'GET'), ('post', 'POST'), ('readback', 'GET'),
                                          ('delete', 'DELETE'), ('final', 'GET')):
                        if self.fatal or self.errors >= 2:
                            break
                        eligible = [o for o in group if o['active']]
                        tasks = []
                        for owner in eligible:
                            payload = None
                            if stage == 'post':
                                owner['touched'] = True  # Set before send: commit outcome can be unknown.
                                payload = {**self.item, 'note': owner['note']}
                            elif stage == 'delete':
                                payload = {'review_id': owner['id']}
                            tasks.append((owner, method, stage, payload))
                        for owner, result in zip(eligible, self.wave(tasks)):
                            self.validate(owner, result, stage)
                finally:
                    self.cleanup(group)
                    if any(o['touched'] and not o['clean'] for o in group):
                        # Do not accumulate unresolved rows in later groups.
                        self.fatal = True
                if self.fatal or self.errors >= 2:
                    break
        finally:
            for owner in self.owners:
                owner['session'].close()
        return self.summary()

    def summary(self):
        planned = [r for r in self.records if r['phase'] == 'planned']
        gets = [r['latency_seconds'] for r in planned if r['method'] == 'GET' and r['latency_seconds'] is not None]
        writes = [r['latency_seconds'] for r in planned if r['method'] in ('POST', 'DELETE') and r['latency_seconds'] is not None]
        posts = [r['latency_seconds'] for r in planned if r['method'] == 'POST' and r['latency_seconds'] is not None]
        deletes = [r['latency_seconds'] for r in planned if r['method'] == 'DELETE' and r['latency_seconds'] is not None]
        p_get, p_write = percentile(gets), percentile(writes)
        p_post, p_delete = percentile(posts), percentile(deletes)
        touched = [o for o in self.owners if o['touched']]
        clean = sum(o['clean'] for o in touched)
        passed = (len(planned) == 60 and all(r['status'] == 200 and not r['error'] for r in planned)
                  and len(touched) == 12 and clean == len(touched) and p_get is not None and p_write is not None
                  and p_post is not None and p_delete is not None
                  and p_get <= 3 and p_write <= 5 and p_post <= 5 and p_delete <= 5 and not self.fatal)
        return {'passed': passed, 'planned_attempts': len(planned), 'cleanup_attempts': len(self.records) - len(planned),
                'owners_touched': len(touched), 'owners_cleanup_verified': clean,
                'unexpected_errors': self.errors, 'fatal': self.fatal,
                'p95_get_seconds': p_get, 'p95_write_seconds': p_write,
                'p95_post_seconds': p_post, 'p95_delete_seconds': p_delete, 'records': self.records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--design', action='store_true')
    mode.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.design:
        DESIGN.parent.mkdir(parents=True, exist_ok=True)
        with DESIGN.open('x', encoding='utf-8', newline='\n') as out:
            json.dump(design_value(), out, indent=2)
            out.write('\n')
        print('Design created:', DESIGN)
        return
    design_hash = check_committed()
    truststore.inject_into_ssl()
    directory = ROOT / 'data/raw/benchmark'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ('review-load-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex + '.json')
    report = {'schema_version': 1, 'target': BASE, 'expected_commit': COMMIT, 'design_sha256': design_hash,
              'sources_sha256': source_hashes(), 'runtime': {'python': platform.python_version(),
              'requests': requests.__version__, 'truststore': truststore.__version__,
              'local_commit': git('rev-parse', 'HEAD').decode().strip()},
              'started_at_utc': datetime.now(timezone.utc).isoformat(), 'passed': False}
    runner = None
    try:
        with requests.Session() as session:
            session.trust_env = False
            manifest_start = time.monotonic()
            report['manifest'] = {'status': None, 'latency_seconds': None, 'error': None}
            try:
                response = session.get(BASE + '/data/manifest.json', timeout=(5, 20), allow_redirects=False, verify=True)
                report['manifest']['status'] = response.status_code
            except requests.RequestException:
                report['manifest']['error'] = 'transport_error'
                raise
            finally:
                report['manifest']['latency_seconds'] = max(0, time.monotonic() - manifest_start)
            expected = git('show', COMMIT + ':web/data/manifest.json')
            if response.status_code != 200 or digest(response.content) != digest(expected):
                report['manifest']['error'] = 'status_or_hash_mismatch'
                raise ValueError('manifest_mismatch')
            report['manifest_sha256'] = digest(response.content)
            manifest = response.json()
        runner = Runner(manifest)
        report.update(runner.run())
    except BaseException as exc:
        # Exception strings can contain URLs or sensitive input; retain only a generic category.
        if runner is not None:
            report.update(runner.summary())
        report['passed'] = False
        report['failure'] = 'setup_or_runner_error'
        report['failure_type'] = type(exc).__name__
    report['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
    with path.open('x', encoding='utf-8', newline='\n') as out:
        json.dump(report, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps({'passed': report['passed'], 'receipt': str(path)}))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

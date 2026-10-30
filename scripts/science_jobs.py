"""Local, single-host science job supervisor. No network or arbitrary command API."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import os
import platform
from pathlib import Path
import re
import subprocess
import sys
import sysconfig
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
JOB_ROOT = ROOT / 'data/raw/jobs'
FIELDS = ('w350p35', 'w090p10')
SOURCES = ('scripts/science_jobs.py', 'scripts/science_job_worker.py',
           'scripts/benchmark_accuracy.py', 'scripts/gaia_motion.py',
           'scripts/motion_analysis.py', 'scripts/build_demo.py')
VERSION = 'local-spectral-audit-1'
MAX_TIMEOUT = 600


def digest(path):
    h = sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def atomic(path, obj):
    tmp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with tmp.open('xb') as f:
            f.write(encode(obj)); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def safe_input(relative):
    if not isinstance(relative, str):
        raise ValueError('invalid input path')
    path = (ROOT / relative).resolve()
    raw = (ROOT / 'data/raw').resolve()
    if not path.is_relative_to(raw) or not path.is_file():
        raise ValueError('input must be an existing file under data/raw')
    return path


def job_path(job_id):
    if not isinstance(job_id, str) or not re.fullmatch(r'[0-9a-f]{64}', job_id):
        raise ValueError('invalid job id')
    root = JOB_ROOT.resolve()
    path = (root / job_id).resolve()
    if path.parent != root:
        raise ValueError('invalid job path')
    return path


def verify_input(entry):
    path = safe_input(entry['path'])
    if digest(path) != entry['sha256']:
        raise ValueError('input checksum mismatch: ' + entry['path'])


def identity(field):
    if field not in FIELDS:
        raise ValueError('unsupported field')
    path = ROOT / 'data/raw/quality' / field / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if manifest['field']['id'] != field:
        raise ValueError('field mismatch')
    records = []
    for epoch in ('before', 'after'):
        selected = [r for r in manifest['records'] if r['status'] == 'downloaded' and r['epoch'] == epoch][:3]
        if len(selected) != 3:
            raise ValueError('insufficient cached frames')
        records.extend(selected)
    entries = [manifest['gaia'], manifest['calibrations']['spectral_wcs'], *records]
    for entry in entries:
        verify_input(entry)
    return {'version': VERSION, 'kind': 'spectral-audit', 'field': field,
            'manifest_path': path.relative_to(ROOT).as_posix(), 'manifest_sha256': digest(path),
            'source_sha256': {s: digest(ROOT / s) for s in SOURCES},
            'runtime': {'python': sys.version.split()[0], 'python_implementation': platform.python_implementation(),
                        'system': platform.system(), 'machine': platform.machine(),
                        'packages': {name: version(name) for name in ('numpy', 'scipy', 'astropy', 'pillow')}},
            'input_sha256': {e['path']: e['sha256'] for e in entries},
            'selected_obs_ids': [r['obs_id'] for r in records],
            'config': {'frames_per_epoch': 3, 'controls': 5, 'control_selection': 'first Gaia source_id within 0.05 deg of field center',
                       'position': 'fixed Gaia DR3 reference-epoch coordinates; no propagation', 'stamp_radius_native_px': 5}}


def verify_identity(spec):
    if identity(spec['field']) != spec:
        raise ValueError('job identity or input changed')



def validate_result(path, job_id, spec):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('job_id') != job_id or data.get('identity') != spec:
            raise ValueError('result identity mismatch')
        if spec.get('kind') != 'spectral-audit' or not isinstance(spec.get('config'), dict):
            raise ValueError('invalid result kind or configuration')
        expected = spec.get('selected_obs_ids')
        if not isinstance(expected, list) or not expected or len(set(expected)) != len(expected):
            raise ValueError('invalid selected observation IDs')
        frames = data.get('frames')
        if not isinstance(frames, list) or [frame['record']['obs_id'] for frame in frames] != expected:
            raise ValueError('result frame IDs mismatch')
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError('corrupt result') from exc


def submit(field):
    spec = identity(field)
    job_id = sha256(encode(spec)).hexdigest()
    root = JOB_ROOT.resolve(); root.mkdir(parents=True, exist_ok=True)
    path = job_path(job_id)
    try:
        path.mkdir()
    except FileExistsError:
        # A simultaneous submitter can still be writing its manifest.
        for _ in range(200):
            if (path / 'manifest.json').exists(): break
            time.sleep(.05)
        if not (path / 'manifest.json').exists():
            raise RuntimeError('incomplete submit; inspect job directory')
        if json.loads((path / 'manifest.json').read_text(encoding='utf-8')) != spec:
            raise RuntimeError('identity collision or corrupt manifest')
        return job_id
    atomic(path / 'state.json', {'state': 'queued', 'updated_at': now(), 'attempt': 0})
    atomic(path / 'manifest.json', spec)
    return job_id


@contextmanager
def locked(path, name='lock'):
    # A byte-range/flock lock is released by the OS on supervisor crash.
    f = (path / name).open('a+b')
    try:
        if f.seek(0, 2) == 0: f.write(b'0'); f.flush()
        f.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('job already claimed') from exc
        yield
    finally:
        f.close()


def state(path, state_name, attempt, reason=None, **extra):
    item = {'state': state_name, 'attempt': attempt, 'updated_at': now(), **extra}
    if reason: item['reason'] = reason
    atomic(path / 'state.json', item)
    return item


def cancel(job_id):
    path = job_path(job_id)
    if not path.is_dir(): raise ValueError('unknown job')
    # No lock: the supervisor holds it while executing. Marker applies only to the current attempt.
    current = json.loads((path / 'state.json').read_text(encoding='utf-8'))
    if current['state'] != 'running': raise ValueError('job is not running')
    atomic(path / 'cancel.json', {'attempt': current['attempt'], 'requested_at': now()})


def run(job_id, timeout=300, resume=False, *, _command=None):
    if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not 0 < timeout <= MAX_TIMEOUT:
        raise ValueError('timeout must be in (0, 600] seconds')
    path = job_path(job_id)
    if not path.is_dir(): raise ValueError('unknown job')
    with locked(path):
        spec = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
        if sha256(encode(spec)).hexdigest() != job_id: raise ValueError('manifest identity mismatch')
        current = json.loads((path / 'state.json').read_text(encoding='utf-8'))
        result = path / 'result.json'
        if result.exists():
            # Publication can precede a crash before the last state write.
            if current['state'] == 'succeeded' and current.get('result_sha256') != digest(result):
                raise RuntimeError('published result changed')
            validate_result(result, job_id, spec)
            if current['state'] != 'succeeded':
                return state(path, 'succeeded', current['attempt'], 'recovered published artifact', result_sha256=digest(result))
            return current
        if current['state'] == 'running':
            state(path, 'failed', current['attempt'], 'stale supervisor/crash; explicit resume required')
            if not resume: raise RuntimeError('stale job marked failed; use resume')
        elif current['state'] in ('failed', 'cancelled') and not resume:
            raise RuntimeError('explicit resume required')
        elif current['state'] not in ('queued', 'failed', 'cancelled'):
            raise RuntimeError('invalid state or missing result')
        verify_identity(spec)
        attempt = current['attempt'] + 1
        temp = path / ('attempt-' + str(attempt) + '-' + uuid.uuid4().hex + '.json')
        # Windows venv python.exe is a launcher that can leave its child alive on terminate.
        # Run the base interpreter directly, adding the active venv's package directory.
        bootstrap = ('import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); '
                     'runpy.run_module(\"scripts.science_job_worker\",run_name=\"__main__\")')
        command = _command(temp) if _command else [getattr(sys, '_base_executable', sys.executable), '-c', bootstrap, sysconfig.get_path('purelib'), job_id, str(temp.name)]
        state(path, 'running', attempt, timeout_seconds=timeout)
        error_path = temp.with_suffix('.stderr')
        proc = None
        error_file = error_path.open('xb')
        try:
            proc = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=error_file, close_fds=True)
            start = time.monotonic()
            while proc.poll() is None:
                marker = path / 'cancel.json'
                cancelled = marker.exists() and json.loads(marker.read_text(encoding='utf-8')).get('attempt') == attempt
                expired = time.monotonic() - start >= timeout
                if cancelled or expired:
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
                    return state(path, 'cancelled' if cancelled else 'failed', attempt, 'cancelled by user' if cancelled else 'timeout')
                time.sleep(.1)
            error_file.flush()
            with error_path.open('rb') as f: error = f.read(4096).decode('utf-8', errors='replace')
            if proc.returncode != 0:
                return state(path, 'failed', attempt, 'worker crash/exit ' + str(proc.returncode), diagnostic=error[-2000:])
            if not temp.is_file(): return state(path, 'failed', attempt, 'worker returned without artifact')
            validate_result(temp, job_id, spec)
            marker = path / 'cancel.json'
            if marker.exists() and json.loads(marker.read_text(encoding='utf-8')).get('attempt') == attempt:
                return state(path, 'cancelled', attempt, 'cancelled by user')
            # Windows rename refuses an existing destination; POSIX link is exclusive.
            if os.name == 'nt': os.rename(temp, result)
            else: os.link(temp, result)
            return state(path, 'succeeded', attempt, result_sha256=digest(result))
        except Exception as exc:
            state(path, 'failed', attempt, 'supervisor error', diagnostic=str(exc)[:1000])
            raise
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
            if proc is not None and proc.stdin is not None: proc.stdin.close()
            error_file.close()
            error_path.unlink(missing_ok=True)
            temp.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('submit'); s.add_argument('field', choices=FIELDS)
    r = sub.add_parser('run'); r.add_argument('job_id'); r.add_argument('--timeout', type=float, default=300); r.add_argument('--resume', action='store_true')
    c = sub.add_parser('cancel'); c.add_argument('job_id')
    q = sub.add_parser('status'); q.add_argument('job_id')
    args = p.parse_args()
    if args.command == 'submit': print(submit(args.field))
    elif args.command == 'run':
        result = run(args.job_id, args.timeout, args.resume)
        print(json.dumps(result, indent=2))
        if result['state'] != 'succeeded': sys.exit(1)
    elif args.command == 'cancel': cancel(args.job_id)
    else: print((job_path(args.job_id) / 'state.json').read_text(encoding='utf-8'))

if __name__ == '__main__': main()

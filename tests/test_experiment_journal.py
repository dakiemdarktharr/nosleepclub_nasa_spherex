import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts import experiment_journal as journal
from scripts import science_jobs


ROOT = Path(__file__).resolve().parents[1]
IDENTITY = {'protocol_commit': 'abc', 'design': {'sha256': 'def'}, 'runtime': {'python': 'test'}}
KEYS = (('fit', 'a'), ('fit', 'b'), ('../../outside', 'unsafe/name'))
STATUSES = ('fit_completed', 'fit_failed', 'preparation_failed')


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'journal'

    def make(self, identity=IDENTITY, keys=KEYS, statuses=STATUSES):
        return journal.Journal(self.path, identity, keys, statuses)

    def test_partial_resume_counts_and_completion(self):
        j = self.make()
        self.assertIsNone(j.read(KEYS[0]))
        first = j.write(KEYS[0], {'status': 'fit_completed', 'value': [1, 2]})
        self.assertEqual(first['payload']['value'], [1, 2])
        self.assertEqual(j.counts(), {'expected': 3, 'recorded': 1, 'missing': 2,
                                     'statuses': {'fit_completed': 1, 'fit_failed': 0, 'preparation_failed': 0}})
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            j.records(require_complete=True)
        resumed = self.make()
        self.assertEqual(resumed.read(KEYS[0]), first)
        resumed.write(KEYS[1], {'status': 'fit_failed', 'error': 'synthetic failure'})
        resumed.write(KEYS[2], {'status': 'preparation_failed', 'error': 'synthetic mask'})
        records = resumed.records(require_complete=True)
        self.assertEqual([tuple(item['key']) for item in records], list(KEYS))
        self.assertEqual(resumed.counts()['missing'], 0)
        self.assertFalse((self.path.parent / 'outside').exists())

    def test_idempotent_and_contradictory_writes(self):
        j = self.make()
        payload = {'status': 'fit_completed', 'value': {'x': 2}}
        one = j.write(KEYS[0], payload)
        self.assertEqual(one, j.write(KEYS[0], {'value': {'x': 2}, 'status': 'fit_completed'}))
        payload['value']['x'] = 3
        with self.assertRaisesRegex(ValueError, 'different payload'):
            j.write(KEYS[0], payload)
        self.assertEqual(j.read(KEYS[0]), one)

    def test_reject_bad_header_or_payload(self):
        for identity, keys, statuses in [({}, KEYS, STATUSES),
                ({'x': float('nan')}, KEYS, STATUSES), (IDENTITY, (KEYS[0], KEYS[0]), STATUSES),
                (IDENTITY, (('x', 3),), STATUSES), (IDENTITY, KEYS, ('ok', 'ok'))]:
            with self.subTest(identity=identity, keys=keys), self.assertRaises(ValueError):
                self.make(identity, keys, statuses)
        j = self.make()
        for payload in ({'status': 'running'}, {'status': 'fit_failed'},
                        {'status': 'preparation_failed', 'error': ''},
                        {'status': 'fit_completed', 'value': float('inf')},
                        {'status': 'fit_completed', 'checksum': 'forged'},
                        {'status': 'fit_completed', 'identity_sha256': 'forged'},
                        {'status': 'fit_completed', 'key': ['fit', 'b']},
                        {'status': 'fit_completed', 'bad': {1: 'numeric key'}}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                j.write(KEYS[0], payload)
        with self.assertRaises(ValueError):
            j.read(('not-expected',))
        with self.assertRaises(ValueError):
            j.write(['fit', 'a'], {'status': 'fit_completed'})
        self.assertEqual(j.counts()['recorded'], 0)

    def test_mismatched_or_changed_header_rejected(self):
        j = self.make()
        for identity, keys, statuses in [({'protocol_commit': 'other'}, KEYS, STATUSES),
                                         (IDENTITY, KEYS[::-1], STATUSES),
                                         (IDENTITY, KEYS, ('fit_completed',))]:
            with self.assertRaises(ValueError):
                self.make(identity, keys, statuses)
        header = self.path / 'header.json'
        value = json.loads(header.read_text(encoding='utf8'))
        value['identity']['protocol_commit'] = 'tampered'
        header.write_text(json.dumps(value), encoding='utf8')
        with self.assertRaises(ValueError):
            j.read(KEYS[0])
        with self.assertRaises(ValueError):
            self.make()

    def test_corrupt_checksum_envelope_and_unexpected_files(self):
        j = self.make(); j.write(KEYS[0], {'status': 'fit_completed', 'value': 1})
        path = j._record_path(KEYS[0]); initial = path.read_text(encoding='utf8')
        value = json.loads(initial); value['payload']['value'] = 2
        path.write_text(json.dumps(value), encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'corrupt'):
            j.read(KEYS[0])
        value['checksum'] = journal._digest({k: v for k, v in value.items() if k != 'checksum'})
        value['key'] = list(KEYS[1])
        value['checksum'] = journal._digest({k: v for k, v in value.items() if k != 'checksum'})
        path.write_text(json.dumps(value), encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'identity or key'):
            j.read(KEYS[0])
        path.write_text(initial, encoding='utf8')
        for directory in (self.path, self.path / 'records', self.path / 'locks'):
            extra = directory / 'unplanned.txt'; extra.write_text('extra', encoding='utf8')
            with self.subTest(directory=directory), self.assertRaisesRegex(ValueError, 'unexpected'):
                j.records()
            extra.unlink()

    def test_concurrent_initialization_and_different_key_writes(self):
        barrier = threading.Barrier(3)
        def worker(key):
            barrier.wait()
            j = self.make()
            return j.write(key, {'status': 'fit_completed', 'key_index': KEYS.index(key)})
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            outputs = list(pool.map(worker, KEYS))
        self.assertEqual(len(outputs), 3)
        self.assertEqual(self.make().counts()['recorded'], 3)
        self.assertEqual(len(self.make().records(require_complete=True)), 3)

    def test_same_key_race_idempotent_and_conflicting(self):
        self.make()
        barrier = threading.Barrier(2)
        def worker(value):
            barrier.wait()
            try:
                return self.make().write(KEYS[0], {'status': 'fit_completed', 'value': value})
            except ValueError as exc:
                return str(exc)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(worker, [7, 7]))
        self.assertEqual(result[0], result[1])
        barrier = threading.Barrier(2)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(worker, [7, 8]))
        self.assertEqual(sum(isinstance(x, dict) for x in result), 1)
        self.assertEqual(sum(isinstance(x, str) and 'different payload' in x for x in result), 1)
        self.assertEqual(self.make().read(KEYS[0])['payload']['value'], 7)

    def test_failed_atomic_write_can_resume(self):
        j = self.make()
        with patch.object(science_jobs, 'atomic', side_effect=OSError('simulated interrupted write')):
            with self.assertRaises(OSError):
                j.write(KEYS[0], {'status': 'fit_completed'})
        self.assertIsNone(j.read(KEYS[0]))
        self.assertEqual(self.make().write(KEYS[0], {'status': 'fit_completed'})['payload']['status'], 'fit_completed')

    def test_restart_cleans_only_recognized_interrupted_temporary(self):
        j = self.make()
        target = j._record_path(KEYS[0])
        stale = target.with_name('.' + target.name + '.' + 'a' * 32 + '.tmp')
        stale.write_text('incomplete', encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            j.records()
        resumed = self.make()
        self.assertFalse(stale.exists())
        self.assertIsNone(resumed.read(KEYS[0]))
        resumed.write(KEYS[0], {'status': 'fit_completed'})
        strange = target.with_name('.' + target.name + '.not-a-uuid.tmp')
        strange.write_text('unknown', encoding='utf8')
        reopened = self.make()
        self.assertTrue(strange.exists())
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            reopened.records()

    def test_process_exit_releases_os_lock(self):
        self.make()
        code = ('import sys; from pathlib import Path; from scripts.science_jobs import locked; '
                'p=Path(sys.argv[1]); m=locked(p,"process.lock"); m.__enter__(); '
                'print("locked",flush=True); sys.stdin.read()')
        executable = getattr(sys, '_base_executable', sys.executable)
        proc = subprocess.Popen([executable, '-c', code, str(self.path)], cwd=ROOT,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), 'locked')
            with self.assertRaises(RuntimeError):
                with science_jobs.locked(self.path, 'process.lock'):
                    pass
            proc.kill(); proc.wait(timeout=10)
            with science_jobs.locked(self.path, 'process.lock'):
                pass
        finally:
            if proc.poll() is None:
                proc.kill(); proc.wait(timeout=10)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                stream.close()


if __name__ == '__main__':
    unittest.main()

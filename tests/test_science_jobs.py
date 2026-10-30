"""Meaningful supervisor race and recovery tests; dummy commands are internal only."""
import json
from pathlib import Path
import sys
import sysconfig
import subprocess
import uuid
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from scripts import science_jobs as jobs


def sleeping(_): return [getattr(sys, '_base_executable', sys.executable), '-c', 'import time; time.sleep(10)']
def crashing(_): return [getattr(sys, '_base_executable', sys.executable), '-c', 'raise RuntimeError("simulated crash")']
def success(p):
    code = ('import json,pathlib,sys; p=pathlib.Path(sys.argv[1]); '
            'spec=json.loads((p.parent/"manifest.json").read_text()); '
            'data={"job_id":p.parent.name,"identity":spec,"frames":[{"record":{"obs_id":v}} for v in spec["selected_obs_ids"]]}; '
            'p.write_text(json.dumps(data))')
    return [getattr(sys, '_base_executable', sys.executable), '-c', code, str(p)]



class SupervisorTest(unittest.TestCase):
    def setUp(self):
        jobs.JOB_ROOT.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=jobs.JOB_ROOT)
        self.p = patch.object(jobs, 'JOB_ROOT', Path(self.tmp.name)); self.p.start()
        self.i = patch.object(jobs, 'identity', side_effect=lambda field: {'field':field, 'version':'test', 'kind':'spectral-audit', 'config':{'frames_per_epoch':3}, 'selected_obs_ids':['test-obs']}); self.i.start()
        self.v = patch.object(jobs, 'verify_identity'); self.v.start()
        self.job = jobs.submit('a')
    def tearDown(self):
        self.v.stop(); self.i.stop(); self.p.stop(); self.tmp.cleanup()
    def wait_running(self):
        for _ in range(100):
            if json.loads((jobs.job_path(self.job)/'state.json').read_text())['state']=='running': return
            time.sleep(.02)
        self.fail('worker did not start')
    def test_idempotence_and_immutable_result(self):
        self.assertEqual(self.job, jobs.submit('a'))
        self.assertNotEqual(self.job, jobs.submit('b'))
        result = jobs.run(self.job, _command=success)
        self.assertEqual(result['state'], 'succeeded')
        artifact = jobs.job_path(self.job)/'result.json'; before = artifact.read_bytes()
        self.assertEqual(jobs.run(self.job, resume=True, _command=crashing), result)
        self.assertEqual(artifact.read_bytes(), before)
        artifact.write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'changed'): jobs.run(self.job)
    def test_claim_cancel_and_resume(self):
        out=[]
        t=threading.Thread(target=lambda: out.append(jobs.run(self.job, timeout=5, _command=sleeping)))
        t.start(); self.wait_running()
        with self.assertRaisesRegex(RuntimeError, 'already claimed'): jobs.run(self.job, _command=sleeping)
        jobs.cancel(self.job); t.join(10)
        self.assertFalse(t.is_alive()); self.assertEqual(out[0]['state'], 'cancelled')
        with self.assertRaisesRegex(RuntimeError, 'resume'): jobs.run(self.job, _command=success)
        self.assertEqual(jobs.run(self.job, resume=True, _command=success)['state'], 'succeeded')
    def test_timeout_crash_and_stale(self):
        marker=Path(self.tmp.name)/'late-write'
        def late_write(_):
            return [getattr(sys, '_base_executable', sys.executable), '-c', 'import time,pathlib,sys; time.sleep(1); pathlib.Path(sys.argv[1]).write_text(\"alive\")', str(marker)]
        self.assertEqual(jobs.run(self.job, timeout=.2, _command=late_write)['reason'], 'timeout')
        time.sleep(1.1)
        self.assertFalse(marker.exists(), 'timed-out worker continued running')
        self.assertIn('worker crash', jobs.run(self.job, resume=True, _command=crashing)['reason'])
        path=jobs.job_path(self.job); jobs.state(path, 'running', 2)
        with self.assertRaisesRegex(RuntimeError, 'stale'): jobs.run(self.job, _command=success)
        self.assertIn('stale', json.loads((path/'state.json').read_text())['reason'])
        self.assertEqual(jobs.run(self.job, resume=True, _command=success)['state'], 'succeeded')

    def test_supervisor_death_stops_worker_before_resume(self):
        import os
        base = getattr(sys, '_base_executable', sys.executable)
        root = Path(self.tmp.name); path = jobs.job_path(self.job)
        pidfile = root / 'worker-pid'; ticks = root / 'ticks'; resumed = root / 'resumed'
        worker_code = (
            'import os,pathlib,sys,time\n'
            'from scripts.science_job_worker import start_parent_watchdog,hold_worker_lock\n'
            'start_parent_watchdog()\n'
            'with hold_worker_lock(pathlib.Path(sys.argv[1])):\n'
            ' pathlib.Path(sys.argv[2]).write_text(str(os.getpid()))\n'
            ' while True:\n'
            '  with open(sys.argv[3],"a") as f: f.write(str(time.time_ns())+"\\n")\n'
            '  time.sleep(.02)\n')
        supervisor_code = (
            'import pathlib,sys\n'
            'from scripts import science_jobs as j\n'
            'j.JOB_ROOT=pathlib.Path(sys.argv[1]); j.verify_identity=lambda spec: None\n'
            'def cmd(_): return [sys.argv[2],"-c",sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6]]\n'
            'j.run(sys.argv[7],timeout=30,_command=cmd)\n')
        supervisor = subprocess.Popen([base, '-c', supervisor_code, str(root), base, worker_code, str(path),
                                       str(pidfile), str(ticks), self.job], cwd=jobs.ROOT,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, close_fds=True)
        thread = None
        try:
            deadline=time.monotonic()+10
            while not pidfile.exists() and supervisor.poll() is None and time.monotonic()<deadline: time.sleep(.02)
            self.assertTrue(pidfile.exists(), 'worker did not start')
            pid=int(pidfile.read_text())
            if os.name == 'nt':
                import ctypes
                from ctypes import wintypes
                kernel=ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
                kernel.OpenProcess.restype=wintypes.HANDLE
                kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
                kernel.WaitForSingleObject.restype=wintypes.DWORD
                kernel.CloseHandle.argtypes=[wintypes.HANDLE]
                handle=kernel.OpenProcess(0x00100000,False,pid)
                self.assertTrue(handle, 'cannot observe worker')
            supervisor.kill(); supervisor.wait(timeout=5)
            started=time.monotonic()
            resume_code=(
                'import pathlib,sys,time\n'
                'from scripts.science_job_worker import start_parent_watchdog,hold_worker_lock\n'
                'start_parent_watchdog()\n'
                'with hold_worker_lock(pathlib.Path(sys.argv[1])):\n'
                ' pathlib.Path(sys.argv[2]).write_text(str(time.time_ns()))\n'
                ' import json\n'
                ' p=pathlib.Path(sys.argv[3]); spec=json.loads((p.parent/\"manifest.json\").read_text())\n'
                ' p.write_text(json.dumps({\"job_id\":p.parent.name,\"identity\":spec,\"frames\":[{\"record\":{\"obs_id\":x}} for x in spec[\"selected_obs_ids\"]]}))\n')
            result=[]
            def resume():
                result.append(jobs.run(self.job, timeout=10, resume=True, _command=lambda temp: [base, '-c', resume_code, str(path), str(resumed), str(temp)]))
            thread=threading.Thread(target=resume); thread.start()
            if os.name == 'nt':
                try: self.assertEqual(kernel.WaitForSingleObject(handle,2000),0, 'worker survived 2 seconds')
                finally: kernel.CloseHandle(handle)
            else:
                while time.monotonic()-started < 2:
                    try:
                        os.kill(pid,0)
                        stat=Path(f'/proc/{pid}/stat')
                        if stat.read_text().split()[2]=='Z': break
                    except (ProcessLookupError, FileNotFoundError): break
                    time.sleep(.02)
                else: self.fail('worker survived 2 seconds')
            thread.join(10); self.assertFalse(thread.is_alive())
            self.assertEqual(result[0]['state'],'succeeded')
            before=ticks.read_text(); self.assertTrue(before)
            self.assertLessEqual(int(before.splitlines()[-1]),int(resumed.read_text()))
            time.sleep(.15); self.assertEqual(ticks.read_text(), before)
        finally:
            if supervisor.poll() is None: supervisor.kill(); supervisor.wait()
            if thread is not None: thread.join(12)
            supervisor.stderr.close()


    def test_parent_dies_before_watchdog_starts(self):
        base=getattr(sys, '_base_executable', sys.executable)
        root=Path(self.tmp.name); launched=root/'pre-watchdog'; escaped=root/'escaped'
        worker=(
            'import pathlib,sys,time\n'
            'pathlib.Path(sys.argv[1]).write_text("started")\n'
            'time.sleep(.5)\n'
            'from scripts.science_job_worker import start_parent_watchdog\n'
            'start_parent_watchdog()\n'
            'pathlib.Path(sys.argv[2]).write_text("escaped")\n')
        supervisor=(
            'import subprocess,sys\n'
            'p=subprocess.Popen([sys.argv[1],"-c",sys.argv[2],sys.argv[3],sys.argv[4]],stdin=subprocess.PIPE,close_fds=True)\n'
            'p.wait()\n')
        process=subprocess.Popen([base,'-c',supervisor,base,worker,str(launched),str(escaped)],cwd=jobs.ROOT,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True)
        try:
            deadline=time.monotonic()+5
            while not launched.exists() and process.poll() is None and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue(launched.exists())
            process.kill();process.wait(timeout=5)
            time.sleep(1.0)
            self.assertFalse(escaped.exists(), 'worker started work after parent death')
        finally:
            if process.poll() is None: process.kill();process.wait()


    def test_invalid_result_cannot_publish_or_recover(self):
        path=jobs.job_path(self.job); spec=json.loads((path/'manifest.json').read_text())
        bad={'job_id':'wrong','identity':spec,'frames':[{'record':{'obs_id':'test-obs'}}]}
        def invalid(temp):
            return [getattr(sys, '_base_executable', sys.executable), '-c',
                    'import pathlib,sys;pathlib.Path(sys.argv[1]).write_text(sys.argv[2])',str(temp),json.dumps(bad)]
        with self.assertRaisesRegex(ValueError,'identity mismatch'): jobs.run(self.job,_command=invalid)
        self.assertFalse((path/'result.json').exists())
        self.assertEqual(json.loads((path/'state.json').read_text())['state'],'failed')
        (path/'result.json').write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError,'identity mismatch'): jobs.run(self.job,resume=True)
        self.assertEqual(json.loads((path/'state.json').read_text())['state'],'failed')
        bad['job_id']=self.job; bad['frames'][0]['record']['obs_id']='different'
        (path/'result.json').write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError,'frame IDs mismatch'): jobs.run(self.job,resume=True)
        (path/'result.json').write_text('{broken')
        with self.assertRaisesRegex(ValueError,'corrupt result'): jobs.run(self.job,resume=True)
        good={'job_id':self.job,'identity':spec,'frames':[{'record':{'obs_id':'test-obs'}}]}
        (path/'result.json').write_text(json.dumps(good))
        self.assertEqual(jobs.run(self.job,resume=True)['state'],'succeeded')

    def test_invalid_paths_and_config(self):
        for invalid in ('../x', 'a'*63, 'a'*64+'/x'):
            with self.assertRaises(ValueError): jobs.job_path(invalid)
        with self.assertRaises(ValueError): jobs.safe_input('../outside')
        sample=Path(self.tmp.name)/'input.bin'; sample.write_bytes(b'original')
        entry={'path':sample.relative_to(jobs.ROOT).as_posix(), 'sha256':jobs.digest(sample)}
        jobs.verify_input(entry); sample.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'): jobs.verify_input(entry)
        for invalid in (0, 601, True):
            with self.assertRaises(ValueError): jobs.run(self.job, timeout=invalid)
        self.i.stop()
        with self.assertRaises(ValueError): jobs.identity('../bad')
        self.i.start()


class RealIsolationTest(unittest.TestCase):
    @unittest.skipUnless(all((jobs.ROOT / 'data/raw/quality' / f / 'manifest.json').is_file() for f in jobs.FIELDS), 'two opened cached fields unavailable')
    def test_real_workers_concurrent_match_serial(self):
        ids = {f: jobs.submit(f) for f in jobs.FIELDS}
        original = json.loads((jobs.job_path(ids[jobs.FIELDS[0]])/'manifest.json').read_text())
        with patch.object(jobs.platform, 'machine', return_value='test-architecture'):
            other = jobs.identity(jobs.FIELDS[0])
        self.assertNotEqual(jobs.sha256(jobs.encode(original)).hexdigest(), jobs.sha256(jobs.encode(other)).hexdigest())
        outputs = {}
        def launch(field):
            ident = ids[field]; name = 'attempt-999-' + uuid.uuid4().hex + '.json'
            bootstrap = 'import sys,runpy;sys.path.insert(0,sys.argv.pop(1));runpy.run_module(\"scripts.science_job_worker\",run_name=\"__main__\")'
            p = subprocess.Popen([getattr(sys, '_base_executable', sys.executable), '-c', bootstrap, sysconfig.get_path('purelib'), ident, name], cwd=jobs.ROOT, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, close_fds=True)
            return p, jobs.job_path(ident) / name
        pending = {f: launch(f) for f in jobs.FIELDS}
        paths = [v[1] for v in pending.values()]
        processes = [v[0] for v in pending.values()]
        try:
            for field, (proc, path) in pending.items():
                proc.wait(timeout=120); err = proc.stderr.read(); proc.stdin.close(); proc.stderr.close()
                self.assertEqual(proc.returncode, 0, err.decode(errors='replace'))
                outputs[field] = path.read_bytes()
            for field in jobs.FIELDS:
                proc, path = launch(field); paths.append(path); processes.append(proc)
                proc.wait(timeout=120); err = proc.stderr.read(); proc.stdin.close(); proc.stderr.close()
                self.assertEqual(proc.returncode, 0, err.decode(errors='replace'))
                self.assertEqual(outputs[field], path.read_bytes())
                data = json.loads(outputs[field])
                self.assertEqual(data['field']['id'], field)
                self.assertEqual(len(data['frames']), 6)
                self.assertEqual(len(data['frames'][0]['controls']), 5)
            a,b = (json.loads(outputs[f]) for f in jobs.FIELDS)
            self.assertNotEqual(a['field']['ra'], b['field']['ra'])
            self.assertNotEqual(a['frames'][0]['controls'][0]['source_id'], b['frames'][0]['controls'][0]['source_id'])
        finally:
            for proc in processes:
                if proc.poll() is None: proc.kill(); proc.wait()
                if not proc.stdin.closed: proc.stdin.close()
                if not proc.stderr.closed: proc.stderr.close()
            for path in paths: path.unlink(missing_ok=True)

if __name__ == '__main__': unittest.main()

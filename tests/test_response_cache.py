"""Classroom requests share public work without relaxing unique-query budgets."""
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPResponse
import json
import os
import threading
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from web.api import _access_control as control
from web.api._response_cache import ResponseCache, cache_key
from tests import test_observations_api as observations
from tests import test_frame_api as frame


class ResponseCacheTest(unittest.TestCase):
    def setUp(self):
        for api in (observations.api, frame.api):
            api.response_cache.clear()
        with control._lock:
            control._counts.clear()
            control._bursts.clear()

    def test_thirty_same_wifi_readers_share_one_upstream_and_one_admission(self):
        cases=[(observations.api, '/api/observations?ra=350&dec=35', observations.SAMPLE),
               (frame.api, '/api/frame?'+urlencode({'url':frame.URL,'ra':350,'dec':35,'fov_deg':.005}), frame.synthetic())]
        for api, path, payload in cases:
            with self.subTest(endpoint=api.__name__):
                gate=threading.Event()
                def upstream(url):
                    if not gate.wait(5):
                        raise RuntimeError('test gate timed out')
                    return payload
                def request(_):
                    sock=observations.MemorySocket(f'GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n'.encode())
                    api.handler(sock, ('127.0.0.1', 1), None)
                    result=HTTPResponse(observations.MemorySocket(sock.output.getvalue()))
                    result.begin()
                    return result.status, dict(result.getheaders()), result.read()
                with patch.dict(os.environ, {'SPHEREX_LOCAL_API':'1'}, clear=True), patch.object(api,'fetch',side_effect=upstream) as fetched, patch.object(api,'emit_request'):
                    with ThreadPoolExecutor(max_workers=30) as pool:
                        futures=[pool.submit(request,n) for n in range(30)]
                        until=time.monotonic()+4
                        while time.monotonic()<until:
                            with api.response_cache.lock:
                                waiting=sum(f['waiters'] for f in api.response_cache.flights.values())
                            if waiting==29:
                                break
                            time.sleep(.005)
                        gate.set()
                        results=[f.result(timeout=5) for f in futures]
                    self.assertEqual(waiting,29)
                    self.assertEqual([r[0] for r in results],[200]*30)
                    self.assertEqual(fetched.call_count,1)
                    self.assertEqual(sum(r[1]['X-Response-Cache']=='miss' for r in results),1)
                    self.assertEqual(sum(r[1]['X-Response-Cache']=='shared' for r in results),29)
                    self.assertEqual(len({r[2] for r in results}),1)
                    self.assertEqual(len({r[1]['X-Request-ID'] for r in results}),30)
                    warm=request(31)
                    self.assertEqual(warm[1]['X-Response-Cache'],'hit')
                    self.assertEqual(fetched.call_count,1)
                endpoint='frame' if api is frame.api else 'observations'
                counts=[v for k,v in control._counts.items() if k[1]==endpoint]
                self.assertEqual(counts,[1,1], 'one global and one IP admission, despite 31 readers')

    def test_success_canonicalization_provenance_and_cache_identity_gate(self):
        api=observations.api
        with patch.dict(os.environ,{'SPHEREX_LOCAL_API':'1'},clear=True), patch.object(api,'fetch',return_value=observations.SAMPLE) as fetched:
            first=observations.request('/api/observations?ra=350&dec=35')
            second=observations.request('/api/observations?dec=35.0&ra=350.000')
            self.assertEqual(second[1]['X-Response-Cache'],'hit')
            self.assertEqual(first[2]['provenance'],second[2]['provenance'])
            self.assertEqual(fetched.call_count,1)
            self.assertEqual(observations.request('/api/observations?ra=350&dec=35&release=qr3')[0],502)
            self.assertEqual(fetched.call_count,2,'release is part of the key')
        # Even deliberately prefilled production bytes cannot skip caller validation.
        p=api.parse_params('ra=350&dec=35')
        api.response_cache.run(cache_key('production','observations/1.0',p),lambda:(b'{}',{}))
        with patch.dict(os.environ,{'VERCEL_ENV':'production','MONGODB_URI':'secret'},clear=True), patch.object(api,'fetch') as fetched:
            self.assertEqual(observations.request('/api/observations?ra=350&dec=35')[0],503)
            fetched.assert_not_called()

    def test_expiry_failure_and_byte_entry_limits(self):
        now=[0]
        cache=ResponseCache(ttl=10,max_bytes=12,max_entries=2,clock=lambda:now[0])
        result=(b'1234',{})
        self.assertEqual(cache.run('a',lambda:result)[1],'miss')
        self.assertEqual(cache.run('a',lambda:None)[1],'hit')
        now[0]=11
        self.assertEqual(cache.run('a',lambda:result)[1],'miss')
        for key in ['b','c']:
            cache.run(key,lambda:result)
        self.assertEqual(list(cache.entries),['b','c'])
        self.assertLessEqual(cache.size,12)
        cache.run('large',lambda:(b'x'*13,{}))
        self.assertNotIn('large',cache.entries)
        with self.assertRaises(ValueError):
            cache.run('bad',lambda:(_ for _ in ()).throw(ValueError('not retained')))
        self.assertNotIn('bad',cache.entries)
        self.assertNotIn('bad',cache.flights)
        self.assertEqual(cache.run('bad',lambda:result)[1],'miss')

    def test_inflight_waiters_and_wait_time_are_bounded(self):
        cache=ResponseCache(10,max_inflight=1,max_waiters=1,wait_seconds=.05)
        entered=threading.Event();release=threading.Event()
        def work():
            entered.set();release.wait(2);return b'ok',{}
        with ThreadPoolExecutor(max_workers=3) as pool:
            leader=pool.submit(cache.run,'a',work)
            self.assertTrue(entered.wait(1))
            with self.assertRaises(control.AccessDenied) as busy:
                cache.run('different',work)
            self.assertEqual(busy.exception.code,'service_busy')
            with self.assertRaises(control.AccessDenied) as waiting:
                cache.run('a',work)
            self.assertEqual(waiting.exception.code,'shared_request_timeout')
            with cache.lock:
                cache.flights['a']['waiters']=1
            with self.assertRaises(control.AccessDenied):
                cache.run('a',work)
            release.set();leader.result(timeout=1)
        self.assertEqual(cache.flights,{})


if __name__=='__main__':
    unittest.main()

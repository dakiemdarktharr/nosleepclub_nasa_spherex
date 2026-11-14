"""Opt-in atomic quota verification against a disposable loopback MongoDB only."""
from concurrent.futures import ThreadPoolExecutor
import os
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
from uuid import uuid4
from pymongo import MongoClient
from web.api import _access_control as control

URI=os.environ.get('REVIEW_TEST_MONGODB_URI')

@unittest.skipUnless(URI,'Set REVIEW_TEST_MONGODB_URI to a disposable loopback replica set')
class MongoAdmissionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=urlsplit(URI)
        if (p.scheme!='mongodb' or p.hostname!='127.0.0.1' or p.username or p.password or
            p.path not in ('','/') or p.fragment or ',' in p.netloc or parse_qs(p.query)!={'directConnection':['true']}):
            raise RuntimeError('Refusing non-loopback quota test URI')
        cls.client=MongoClient(URI,serverSelectionTimeoutMS=3000,connectTimeoutMS=3000,socketTimeoutMS=5000,maxPoolSize=32)
        hello=cls.client.admin.command('hello')
        if hello.get('setName')!='codex-review-test' or not hello.get('isWritablePrimary'):
            cls.client.close()
            raise RuntimeError('Expected disposable replica set codex-review-test')
        cls.name='codex_quota_test_'+uuid4().hex
        cls.db=cls.client[cls.name]

    @classmethod
    def tearDownClass(cls):
        if getattr(cls,'name','').startswith('codex_quota_test_'):
            cls.client.drop_database(cls.name)
        cls.client.close()

    def test_concurrent_admission_and_rejected_requests_preserve_capacity(self):
        def attempt(ip):
            try:
                control._mongo('frame','test',100,control.hashed(ip),8,24,60)
                return 200
            except control.AccessDenied as exc:
                return exc.status
        with patch.object(control,'database',return_value=self.db):
            with ThreadPoolExecutor(max_workers=30) as pool:
                same=list(pool.map(lambda _:attempt('same'),range(30)))
                others=list(pool.map(lambda n:attempt(str(n)),range(30)))
        self.assertEqual(same.count(200),8)
        self.assertEqual(same.count(429),22)
        self.assertEqual(others.count(200),16)
        self.assertEqual(others.count(429),14)
        rows=list(self.db.api_limits.find({}))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['count'],24)
        self.assertEqual(sum(rows[0]['ips'].values()),24)
        self.assertEqual(len(rows[0]['ips']),17)

if __name__=='__main__':
    unittest.main()

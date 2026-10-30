"""Release identifiers are consistent and cannot inject response headers."""
from http.client import HTTPResponse
from io import BytesIO
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


class MemorySocket:
    def __init__(self,data):self.input=BytesIO(data);self.output=BytesIO()
    def makefile(self,*args,**kwargs):return self.input
    def sendall(self,data):self.output.write(data)


def response_headers(name,env):
    spec=importlib.util.spec_from_file_location('deployment_'+name,ROOT/'web/api'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    sock=MemorySocket(b'PUT /api/check HTTP/1.1\r\nHost: demo.example\r\n\r\n')
    with patch.dict('os.environ',env,clear=True):module.handler(sock,('127.0.0.1',1),None)
    response=HTTPResponse(MemorySocket(sock.output.getvalue()));response.begin()
    return response.status,dict(response.getheaders())


class DeploymentMetadata(unittest.TestCase):
    def test_same_valid_git_commit_is_exposed_by_every_api(self):
        for name in ('reviews','observations','frame'):
            with self.subTest(name=name):
                status,headers=response_headers(name,{'VERCEL_GIT_COMMIT_SHA':'a'*40})
                self.assertEqual(status,405);self.assertEqual(headers['X-App-Commit'],'a'*40)

    def test_untrusted_or_missing_commit_cannot_inject_headers(self):
        for name in ('reviews','observations','frame'):
            for value in ('','not-a-commit','a'*40+'\r\nInjected: yes'):
                with self.subTest(name=name,value=value):
                    status,headers=response_headers(name,{'VERCEL_GIT_COMMIT_SHA':value})
                    self.assertEqual(status,405);self.assertNotIn('X-App-Commit',headers)
                    self.assertNotIn('Injected',headers)


if __name__=='__main__':unittest.main()

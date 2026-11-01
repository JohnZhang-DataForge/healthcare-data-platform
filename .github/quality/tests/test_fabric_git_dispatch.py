"""No-network proof: public Healthcare main dispatches only private trusted Runner."""
from __future__ import annotations

import json
import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "scripts"))
import fabric_git_dispatch as dispatch

SHA="a"*40
TOKEN="NEVER_PRINT_THIS_TEST_TOKEN"
SOURCE={
    "GITHUB_REPOSITORY":"JohnZhang-DataForge/healthcare-data-platform",
    "GITHUB_REF":"refs/heads/main",
    "GITHUB_EVENT_NAME":"push",
    "GITHUB_WORKFLOW":"Healthcare Fabric Git Deploy",
    "GITHUB_SHA":SHA,
}


class StubResponse:
    status=200
    def __init__(self, status=200, raw=None):
        self.status=status
        self.raw=raw if raw is not None else json.dumps({
            "html_url":dispatch.RUN_PREFIX+"12345678"}).encode()
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,limit):return self.raw[:limit]


class StubOpener:
    def __init__(self,response=None,exception=None):
        self.response=response or StubResponse()
        self.exception=exception
        self.calls=0
        self.request=None
    def open(self,request,timeout):
        self.calls+=1
        self.request=request
        if self.exception:raise self.exception
        return self.response


class DispatchTests(unittest.TestCase):
    def test_main_push_only_and_explicit_manual_main(self):
        self.assertEqual(dispatch.validate_main_event(SOURCE),SHA)
        self.assertEqual(dispatch.validate_main_event(
            {**SOURCE,"GITHUB_EVENT_NAME":"workflow_dispatch"}),SHA)
        for key,value in [
            ("GITHUB_REPOSITORY","other/healthcare-data-platform"),
            ("GITHUB_REF","refs/heads/feature"),
            ("GITHUB_EVENT_NAME","pull_request"),
            ("GITHUB_WORKFLOW","Fake Dispatcher"),
            ("GITHUB_SHA","not-a-sha"),
        ]:
            with self.subTest(key=key),self.assertRaises(dispatch.DispatchHold):
                dispatch.validate_main_event({**SOURCE,key:value})

    def test_only_exact_single_private_workflow_dispatch_and_commit(self):
        opener=StubOpener()
        report=dispatch.dispatch(opener,TOKEN,SHA)
        self.assertEqual(report["outcome"],"DISPATCH_ACCEPTED")
        self.assertEqual(report["run_url"],dispatch.RUN_PREFIX+"12345678")
        self.assertEqual(opener.calls,1)
        self.assertEqual(opener.request.get_method(),"POST")
        self.assertEqual(opener.request.full_url,dispatch.URL)
        self.assertTrue(dispatch.URL.startswith("https://api.github.com/repos/JohnZhang-DataForge/Self-Runner/"))
        self.assertEqual(json.loads(opener.request.data),{
            "ref":"main","inputs":{"expected_healthcare_sha":SHA}})
        self.assertNotIn(TOKEN,json.dumps(report))
        self.assertNotIn(TOKEN,opener.request.data.decode())

    def test_missing_secret_blocks_without_http_request(self):
        opener=StubOpener()
        with self.assertRaises(dispatch.DispatchHold) as result:
            dispatch.dispatch(opener,"",SHA)
        self.assertEqual(str(result.exception),"DISPATCH_TOKEN_NOT_CONFIGURED")
        self.assertEqual(opener.calls,0)

    def test_http_denial_is_error_code_only_no_body_or_secrets(self):
        opener=StubOpener(exception=urllib.error.HTTPError(
            dispatch.URL,403,"Forbidden",{},None))
        with self.assertRaises(dispatch.DispatchHold) as result:
            dispatch.dispatch(opener,TOKEN,SHA)
        self.assertEqual(str(result.exception),"DISPATCH_HTTP_403")
        self.assertNotIn(TOKEN,str(result.exception))
        self.assertEqual(opener.calls,1)

    def test_204_success_and_no_fake_run_url(self):
        response=StubResponse(status=204,raw=b"")
        report=dispatch.dispatch(StubOpener(response),TOKEN,SHA)
        self.assertEqual(report["outcome"],"DISPATCH_ACCEPTED")
        self.assertFalse(report["run_url"])

    def test_untrusted_run_url_is_never_rendered(self):
        response=StubResponse(status=200,raw=json.dumps(
            {"html_url":"https://evil.example/phishing"}).encode())
        report=dispatch.dispatch(StubOpener(response),TOKEN,SHA)
        self.assertEqual(report["run_url"],"")

    def test_invalid_json_fails_closed(self):
        response=StubResponse(status=200,raw=b"{broken")
        with self.assertRaises(dispatch.DispatchHold):
            dispatch.dispatch(StubOpener(response),TOKEN,SHA)


if __name__=="__main__":
    unittest.main()

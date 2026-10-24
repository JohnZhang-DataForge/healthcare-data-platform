"""Pinned release policy for real deployed v2 Consumer and immutable new requests."""
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"apps/synthea/new_only"),str(ROOT/"apps/task004")]
from generate_new_only import new_params,freeze_params,GateError
from publish_v2_verified import (
    require_live_consumer_release,V2PublishBlocked,
    APPROVED_V2_CONSUMER_IMAGE,APPROVED_CONTRACT_SHA256,APPROVED_DAGRUN
)
from validate_new_only_v2_manifest import source_contract

CONTRACT=ROOT/"contracts/synthea/new-only/csv-contract-v2.json"
POLICY=ROOT/"contracts/synthea/new-only/ready-publication-policy-v1.json"


class ActualV2ReleaseGateTests(unittest.TestCase):
    def test_release_policy_exact_contract_and_deployed_dagrun(self):
        doc,sha=source_contract(CONTRACT)
        self.assertEqual(sha,APPROVED_CONTRACT_SHA256)
        self.assertEqual(doc["consumer_compatibility"],"NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY")
        self.assertEqual(require_live_consumer_release(CONTRACT,POLICY),sha)
        p=json.loads(POLICY.read_text())
        self.assertEqual(p["consumer"]["image"],APPROVED_V2_CONSUMER_IMAGE)
        self.assertEqual(p["consumer"]["evidence_workflow"],APPROVED_DAGRUN)
        self.assertEqual(p["scope"]["airflow_claim"],"NO")
        self.assertEqual(p["scope"]["postgresql_mutation"],"NO")
        docker=(ROOT/"images/synthea-new-only/Dockerfile").read_text()
        self.assertIn("ready-publication-policy-v1.json",docker)

    def test_missing_or_forged_release_policy_cannot_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"release.json"
            with self.assertRaisesRegex(V2PublishBlocked,"POLICY_MISSING"):
                require_live_consumer_release(CONTRACT,path)
            original=json.loads(POLICY.read_text())
            for key,value in [
                ("release_decision","NOT_YET_DEPLOYED"),
                ("image","ghcr.io/someone/forged@sha256:"+"0"*64),
                ("airflow_claim","YES"),
                ("sha256","0"*64),
            ]:
                fake=json.loads(json.dumps(original))
                if key=="image": fake["consumer"]["image"]=value
                elif key=="airflow_claim":fake["scope"]["airflow_claim"]=value
                elif key=="sha256":fake["immutable_contract"]["sha256"]=value
                else:fake[key]=value
                path.write_text(json.dumps(fake))
                with self.subTest(key=key):
                    with self.assertRaisesRegex(V2PublishBlocked,"RELEASE_POLICY_INVALID"):
                        require_live_consumer_release(CONTRACT,path)

    def test_population_one_frozen_and_invalid_values_rejected(self):
        now=dt.datetime(2026,10,14,tzinfo=dt.timezone.utc)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.dict(os.environ,{"NEW_ONLY_TARGET_POPULATION":"1"}):
                a=freeze_params(root,"gh-lowpop-test-001",now)
                b=freeze_params(root,"gh-lowpop-test-001",now)
            self.assertEqual(a,b)
            self.assertEqual(a["target_population"],1)
            self.assertEqual(a["reference_date"],"20261014")
            with patch.dict(os.environ,{"NEW_ONLY_TARGET_POPULATION":"2"}):
                with self.assertRaisesRegex(GateError,"immutable target population"):
                    freeze_params(root,"gh-lowpop-test-001",now)
            for invalid in ("0","101","-1","1;rm","NaN","01",""):
                with patch.dict(os.environ,{"NEW_ONLY_TARGET_POPULATION":invalid}):
                    with self.subTest(invalid=invalid):
                        with self.assertRaises(GateError):
                            new_params("gh-new-lowpop-002",now)


if __name__=="__main__":
    unittest.main()

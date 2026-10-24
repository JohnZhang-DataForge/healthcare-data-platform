"""Additive NEW_ONLY v2 bridge packaging / legacy compatibility tests."""
from pathlib import Path
import ast
import hashlib
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"apps"/"task004"))
from validate_new_only_v2_manifest import source_contract,V2ContractError
from resolve_verified_landing_file import validate_manifest,ResolverError

class ProcessingV2PackageTests(unittest.TestCase):
    def test_canonical_pinned_v2_contract_sha_and_18_files(self):
        source=ROOT/"contracts/synthea/new-only/csv-contract-v2.json"
        contract,sha=source_contract()
        self.assertEqual(sha,hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(sha,"d7118f4bc3306d74911e609b4f0a41b9340ba9a60acaa69174063d5025ad1249")
        self.assertEqual(len(contract["files"]),18)
        self.assertEqual(contract["required_nonempty_datasets"],["patients","encounters"])
    def test_layer_uses_release_parent_and_preserves_entrypoint(self):
        docker=(ROOT/"images/landing-processing-runtime/Dockerfile").read_text()
        self.assertIn("ARG BASE_IMAGE=ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-runtime:latest",docker)
        self.assertIn("FROM ${BASE_IMAGE}",docker)
        self.assertNotIn("@sha256:",docker)
        for file in ("resolve_verified_landing_file.py","validate_new_only_v2_manifest.py","csv-contract-v2.json"):
            self.assertIn(file,docker)
        self.assertNotIn("ENTRYPOINT",docker.split("# Inherit the proven")[0])
    def test_legacy_v1_fail_closed_for_empty_auxiliary(self):
        batch="task004-airflow-test-123"
        doc=dict(manifest_version="1.0",status="INTAKE_VERIFIED",batch_id=batch)
        with self.assertRaises(ResolverError):
            validate_manifest(doc,batch,"s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-12/batch_id="+batch+"/manifest.json")
    def test_v2_rejects_partial_fake_manifest(self):
        batch="synthea-new-only-gh-38497355290"
        uri="s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id="+batch+"/manifest.json"
        with self.assertRaises(ResolverError):
            validate_manifest(dict(manifest_version="2.0",status="INTAKE_VERIFIED"),
                              batch,uri)
    def test_v2_source_identity_is_pinned_to_new_only(self):
        batch="synthea-new-only-gh-38497355290"
        with self.assertRaises(ResolverError):
            validate_manifest(dict(manifest_version="2.0",batch_id=batch),
                 "synthea-update-only-gh-38497355290",
                 "s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-update-only-gh-38497355290/manifest.json")

if __name__=="__main__":
    unittest.main()

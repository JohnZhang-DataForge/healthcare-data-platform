"""NEW_ONLY Writer versioned-identity regression (all fixtures, no DML)."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"airflow"/"dags"))
sys.path.insert(0,str(ROOT/"apps"/"omop_writer"))

from build_s3_rollback_plan import build
from task004_cdm_materialization_plan import plan,same_plan
from task004_cdm_dynamic_adapters import digest,transform
from task004_cdm_dynamic_pg_writer import render
from precommit_gate import validate_input

VERSION="synthea-new-only-v1"
BATCH="synthea-new-only-gh-38497355290"
MANIFEST_SHA="dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80"
DATE="2026-10-14"

def sample(batch=BATCH,version=VERSION,people=1,visits=812):
    root="source=synthea/source_version=v3.3.0/ingest_date="+DATE+"/batch_id="+batch+"/"
    kw=dict(batch_id=batch,manifest_sha256=MANIFEST_SHA,
            manifest_uri="s3://health-landing/"+root+"manifest.json",
            person_processing_uri="s3a://health-processing/"+root+"entity=patient/run_id=test-fixture/work/normalized/data/",
            visit_processing_uri="s3a://health-processing/"+root+"entity=encounter/run_id=test-fixture/work/normalized/data/",
            person_rows=people,visit_rows=visits)
    if version is not None:kw["writer_identity_version"]=version
    return kw

def legacy():
    return sample(batch="task004-airflow-legacy-fixture",version=None,people=23,visits=3588)

def prepared(key,entity,parent=None):
    payload={"gender_concept_id":8507} if entity=="person" else {"visit_concept_id":9202}
    row={"source_key":key,"canonical_payload":payload}
    if entity=="visit":row["source_person_key"]=parent
    row["row_fingerprint"]=digest({"source_person_key":parent,"payload":payload})
    return row

class NewOnlyWriterIdentity(unittest.TestCase):
    def test_real_v2_ready_identity_produces_immutable_rollback_only_plan(self):
        c=build(**sample())
        self.assertEqual(c["writer_identity_version"],VERSION)
        self.assertEqual(c["batch_id"],BATCH)
        self.assertEqual(c["manifest_sha256"],MANIFEST_SHA)
        self.assertEqual(c["person_rows"],1)
        self.assertEqual(c["visit_rows"],812)
        self.assertIs(c["database_mutation_authorized"],False)
        self.assertTrue(same_plan(dict(sample(),state="HANDOFF_VERIFIED_NOT_LOADED",cdm_write_permitted=False),
                                  dict(sample(),state="HANDOFF_VERIFIED_NOT_LOADED",cdm_write_permitted=False)))
    def test_legacy_implicit_contract_stays_bitwise_stable(self):
        a=build(**legacy())
        self.assertNotIn("writer_identity_version",a)
        b=plan(dict(legacy(),state="HANDOFF_VERIFIED_NOT_LOADED",cdm_write_permitted=False,source_version="v3.3.0"))
        self.assertEqual(a["plan_sha256"],b["plan_sha256"])
        self.assertIs(a["database_mutation_authorized"],False)
    def test_new_requires_explicit_version_and_old_cannot_impersonate_new(self):
        for kw in (sample(version=None),sample(batch="task004-airflow-false-new"),
                   sample(version="synthea-new-only-v9"),
                   sample(version="legacy-task004-v1"),
                   sample(batch="synthea-update-only-test"),
                   sample(batch="synthea-mix-data-test")):
            with self.subTest(kw=kw["batch_id"],version=kw.get("writer_identity_version")):
                with self.assertRaises(ValueError):build(**kw)
        with self.assertRaises(ValueError):build(**sample(batch="synthea-new-only-valid",version=None))
    def test_path_binding_and_version_mismatch_fail_closed(self):
        for key,value in (
            ("manifest_uri","s3://other-bucket/path/manifest.json"),
            ("manifest_sha256","f"*64),
            ("person_processing_uri","s3a://health-processing/foreign/entity=patient/data/"),
            ("visit_rows",0),("person_rows",101),("visit_rows",100001)):
            kw=sample()
            if key=="manifest_sha256":
                # Immutable, approved SHA changes are allowed to create a *new*
                # plan, but MUST change its digest. A tampered plan is rejected.
                before=build(**kw);kw[key]=value
                self.assertNotEqual(before["plan_sha256"],build(**kw)["plan_sha256"])
                continue
            kw[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):build(**kw)
    def test_new_only_adapter_and_precommit_shape(self):
        c=build(**sample(visits=1))
        row=dict(source_system="synthea",source_version="v3.3.0",
                 source_batch_id=BATCH,source_ingest_date=DATE,
                 source_record_id="unique-person-1",
                 gender_code="M",race_code="white",ethnicity_code="nonhispanic",
                 birth_date="1980-01-01")
        out=transform([row],c,"person")
        self.assertEqual(len(out),1)
        p=[prepared("person-1","person")]
        v=[prepared("visit-1","visit","person-1")]
        validate_input(c,p,v)
        changed=dict(c);changed["writer_identity_version"]="synthea-new-only-v9"
        with self.assertRaises(ValueError):transform([row],changed,"person")
    def test_existing_target_drift_stays_and_new_commit_is_blocked(self):
        c=build(**sample(visits=1))
        p=[prepared("person-1","person")]
        script=render(c,p,"person",allow_commit=False)
        self.assertTrue(script.endswith("ROLLBACK;\n"))
        for clause in ("BLOCKED:EXISTING_TARGET_DRIFT","BLOCKED:STAGE_DRIFT",
                       "BLOCKED:TARGET_RECONCILIATION","INSERT INTO cdm.person"):
            self.assertIn(clause,script)
        with self.assertRaisesRegex(ValueError,"new_only_commit_requires_fenced_writer"):
            render(c,p,"person",allow_commit=True)
    def test_contract_document_pins_versions(self):
        j=json.loads((ROOT/"contracts/omop-writer/writer-batch-identity-v1.json").read_text())
        self.assertEqual(j["new_only"]["writer_identity_version"],VERSION)
        self.assertTrue(j["legacy"]["legacy_plan_sha_unchanged"])
        self.assertEqual(j["invariants"]["claim_enable"],"NO")

if __name__=="__main__":unittest.main()

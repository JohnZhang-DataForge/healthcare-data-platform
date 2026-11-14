"""G4 Silver staged Delta orchestration tests; fake Delta IO, real Shared Engine contracts.

All remote storage is mocked. These tests are NOT Fabric cloud acceptance.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from healthcare_data_engine import SourceObject

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "azure-fabric/notebook-development"))
import fhir_ingest_notebook as nb

PATIENT = (ROOT / "local-data-platform/spark/contracts/canonical/patient-v1.json").read_text()
ENCOUNTER = (ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json").read_text()
REQUEST = "atlanta-fhir-gh-41552666929"


class Row:
    def __init__(self, fields):
        self.fields = fields

    def asDict(self, recursive=False):
        return dict(self.fields)

    def __getattr__(self, key):
        return self.fields[key]


class Frame:
    def __init__(self, rows, columns=None):
        self.rows = [dict(r) for r in rows]
        self.columns = list(columns if columns is not None else
                            (self.rows[0].keys() if self.rows else []))

    def collect(self):
        return [Row(r) for r in self.rows]

    def count(self):
        return len(self.rows)

    def limit(self, n):
        return Frame(self.rows[:n], self.columns)

    def select(self, *columns):
        return Frame([{c: r[c] for c in columns} for r in self.rows], columns)

    def exceptAll(self, other):
        def hashable(r):
            return tuple(json.dumps(r[c], sort_keys=True, default=str) for c in self.columns)
        left = Counter(hashable(r) for r in self.rows)
        right = Counter(hashable(r) for r in other.rows)
        remain = left - right
        return Frame(
            [dict(zip(self.columns, values)) for values, n in remain.items()
             for _ in range(n)], self.columns)


class Spark:
    def __init__(self, manifest):
        self.manifest = manifest
        self.delta = {}
        self.mode = None

    @property
    def read(self):
        return self

    def format(self, value):
        self.mode = value
        return self

    def load(self, path):
        if self.mode == "binaryFile":
            assert path.endswith("/landing-manifest.json"), path
            return Frame([{"content": self.manifest}])
        if self.mode != "delta":
            raise AssertionError("unexpected Spark source format")
        return self.delta[path]

    def createDataFrame(self, values, schema):
        fields = [p.split()[0] for p in schema.split(", ")]
        return Frame([dict(zip(fields, r)) for r in values], fields)


def source_fixture(tag="original"):
    objects, manifest_entries = [], []
    for i in range(100):
        name = (
            "clinical/v1/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/"
            + REQUEST + f"/FHIR_R4/fhir/patient-{i:03d}.json")
        content = json.dumps({"resourceType": "Patient", "id": f"synthetic-{i}",
                              "marker": tag}, sort_keys=True).encode()
        source = SourceObject.from_bytes(
            name, content, hospital_id="atlanta-hospital-a",
            feed_id="atlanta-hospital-a-fhir-r4", source_system="synthea-fhir")
        objects.append(source)
        manifest_entries.append({
            "blob_key": name, "sha256": source.sha256,
            "size_bytes": source.size_bytes, "source_event_id": None,
            "etag": f'"etag-{i}"', "version_id": None})
    manifest = {
        "schema_version": "healthcare-azure-blob-landing-manifest-v1",
        "hospital_id": "atlanta-hospital-a",
        "feed_id": "atlanta-hospital-a-fhir-r4",
        "request_id": REQUEST,
        "source_manifest_sha256": "a" * 64, "target_format": "FHIR_R4",
        "skipped_non_admissions": 0,
        "objects": manifest_entries}
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return raw, hashlib.sha256(raw).hexdigest(), tuple(objects)


class G4Offline(unittest.TestCase):
    def setUp(self):
        self.raw, self.sha, self.sources = source_fixture()
        self.spark = Spark(self.raw)
        self.params = dict(
            request=REQUEST, manifest_sha=self.sha, mode="SILVER_WRITE",
            allow_write=True, retention_ok=True,
            strategy="DELTA_RAW_SNAPSHOT_V1", manifest_override="",
            source_override="", target_override="",
            patient_contract_json=PATIENT, encounter_contract_json=ENCOUNTER)
        self.calls = 0
        self.findings = ()

    def prepared(self, spark, *, context, manifest_bytes, source_objects,
                 patient_contract_bytes, encounter_contract_bytes):
        self.calls += 1
        self.assertEqual(len(source_objects), 100)
        self.assertEqual(hashlib.sha256(manifest_bytes).hexdigest(), self.sha)
        self.assertEqual(patient_contract_bytes, PATIENT.encode())
        self.assertEqual(encounter_contract_bytes, ENCOUNTER.encode())
        rows_p = [{"source_record_id": f"patient-{i:03d}",
                   "source_batch_id": context.source_batch_id,
                   "processing_run_id": context.processing_run_id,
                   "processed_at": str(context.processed_at)} for i in range(100)]
        rows_e = [{"source_encounter_id": f"encounter-{i:03d}",
                   "source_batch_id": context.source_batch_id,
                   "processing_run_id": context.processing_run_id,
                   "processed_at": str(context.processed_at)} for i in range(121)]
        return nb.PreparedBatch(
            patient_df=Frame(rows_p), encounter_df=Frame(rows_e),
            patient_count=100, encounter_count=121, findings=self.findings,
            source_batch_id=context.source_batch_id,
            processing_version=context.processing_version,
            publication_id="a" * 64, manifest_sha256=context.manifest_sha256,
            source_receipts=nb.verify_source_objects(manifest_bytes, source_objects, context))

    def execute(self, **kwargs):
        params = {**self.params, **kwargs}
        g = nb.verify_fhir_g4_silver.__globals__
        def write(df, path):
            if path in self.spark.delta:
                raise FileExistsError("errorifexists")
            self.spark.delta[path] = df
        with patch.dict(g, {
            "read_source_objects_native": lambda *_args, **_kw: self.sources,
            "prepare_batch": self.prepared,
            "validate_silver_readback": lambda *_args, **_kw: None,
            "_delta_snapshot_exists": lambda spark, path: path in spark.delta,
            "_write_delta": write,
        }):
            return nb.verify_fhir_g4_silver(self.spark, **params)

    def test_physical_paths_stable_and_path_traversal_rejected(self):
        paths = nb._silver_publication_paths(REQUEST)
        self.assertEqual(paths["bronze"], nb._bronze_source_receipt_path(REQUEST))
        self.assertTrue(paths["patient"].endswith("/canonical_patient"))
        self.assertTrue(paths["encounter"].endswith("/canonical_encounter"))
        self.assertTrue(paths["approval"].endswith("/silver_approval"))
        self.assertTrue(paths["quarantine"].endswith("/quarantine"))
        self.assertIn("/" + REQUEST + "/processing=", paths["patient"])
        for bad in ("../sibling", "atlanta-fhir-gh-123/evil", ""):
            with self.subTest(bad=bad), self.assertRaisesRegex(
                    RuntimeError, "HOLD_G3_UNAPPROVED_REQUEST_NAMESPACE"):
                nb._silver_publication_paths(bad)

    def test_fail_closed_parameter_and_contract_checks_before_source_read(self):
        cases = (
            ("mode", "CANONICAL_READONLY"),
            ("strategy", "HALT"),
            ("manifest_override", "{}"),
            ("source_override", "Files/somewhere-else"),
            ("target_override", "Tables/other"),
            ("allow_write", False),
            ("allow_write", "true"),
            ("retention_ok", False),
            ("manifest_sha", "bad"),
            ("patient_contract_json", "{}"),
            ("encounter_contract_json", "{}"),
        )
        for key, value in cases:
            with self.subTest(key=key), self.assertRaises(Exception):
                self.execute(**{key: value})
            self.assertFalse(self.spark.delta)
            self.assertEqual(self.calls, 0)

    def test_first_write_separate_readback_and_same_request_replay(self):
        a = self.execute()
        self.assertEqual(a.status, "SILVER_APPROVED")
        self.assertEqual((a.metrics["patient"], a.metrics["encounter"],
                          a.metrics["quarantine_or_reject"]), (100, 121, 0))
        paths = nb._silver_publication_paths(REQUEST)
        self.assertEqual(set(self.spark.delta), {
            paths[k] for k in ("bronze", "patient", "encounter", "approval")})
        self.assertEqual(self.spark.delta[paths["bronze"]].count(), 100)
        self.assertTrue(all(len(r["source_payload"]) == r["source_size_bytes"]
                            for r in self.spark.delta[paths["bronze"]].rows))
        self.assertEqual(self.spark.delta[paths["approval"]].rows[0]["status"],
                         "SILVER_APPROVED")
        sizes = {k: id(self.spark.delta[v]) for k, v in paths.items()
                 if v in self.spark.delta}
        b = self.execute(mode="SILVER_READBACK_ONLY",
                         allow_write=False, retention_ok=False)
        self.assertEqual(b.status, "SILVER_SKIP_VERIFIED")
        c = self.execute()
        self.assertEqual(c.status, "SILVER_SKIP_VERIFIED")
        self.assertEqual(sizes, {k: id(self.spark.delta[v]) for k, v in paths.items()
                                 if v in self.spark.delta})

    def test_g4_delegates_to_the_one_canonical_approval_last_writer(self):
        # The historical FHIR route must use the shared physical publisher,
        # not keep a second inline Patient/Encounter/Approval writer.
        shared = nb._write_verified_canonical_silver
        recorded = []

        def guarded_writer(*args, **kwargs):
            self.assertEqual(kwargs["source_preservation_strategy"],
                             "DELTA_RAW_SNAPSHOT_V1")
            self.assertEqual(kwargs["paths"], nb._silver_publication_paths(REQUEST))
            recorded.append("shared-writer-called")
            return shared(*args, **kwargs)

        with patch.dict(nb.verify_fhir_g4_silver.__globals__, {
                "_write_verified_canonical_silver": guarded_writer}):
            result = self.execute()
        self.assertEqual(result.status, "SILVER_APPROVED")
        self.assertEqual(recorded, ["shared-writer-called"])
        paths = nb._silver_publication_paths(REQUEST)
        self.assertEqual(self.spark.delta[paths["approval"]].rows[0]["status"],
                         "SILVER_APPROVED")

    def test_same_request_manifest_drift_holds_without_new_path(self):
        self.assertEqual(self.execute().status, "SILVER_APPROVED")
        self.raw, self.sha, self.sources = source_fixture(tag="drift")
        self.spark.manifest = self.raw
        result = self.execute(manifest_sha=self.sha)
        self.assertEqual(result.status, "HOLD_REQUEST_DRIFT")
        self.assertEqual(len(self.spark.delta), 4)

    def test_readback_only_missing_target_holds_and_never_writes(self):
        result = self.execute(mode="SILVER_READBACK_ONLY",
                              allow_write=False, retention_ok=False)
        self.assertEqual(result.status, "HOLD_SILVER_NOT_FOUND")
        self.assertFalse(self.spark.delta)

    def test_partial_unknown_ack_approval_missing_stays_readonly(self):
        paths = nb._silver_publication_paths(REQUEST)
        self.spark.delta[paths["bronze"]] = Frame([{"source_path": "corrupt"}])
        outcome = self.execute()
        self.assertEqual(outcome.status, "HOLD_REQUEST_DRIFT")
        self.assertEqual(set(self.spark.delta), {paths["bronze"]})

    def test_corrupt_saved_bytes_and_approval_rejected(self):
        self.assertEqual(self.execute().status, "SILVER_APPROVED")
        paths = nb._silver_publication_paths(REQUEST)
        self.spark.delta[paths["bronze"]].rows[0]["source_payload"] = b"tampered"
        self.assertEqual(self.execute(mode="SILVER_READBACK_ONLY",
                                      allow_write=False, retention_ok=False).status,
                         "HOLD_REQUEST_DRIFT")

    def test_missing_approval_fence_never_resumes_partial_writes(self):
        self.assertEqual(self.execute().status, "SILVER_APPROVED")
        paths = nb._silver_publication_paths(REQUEST)
        del self.spark.delta[paths["approval"]]
        self.assertEqual(self.execute().status, "VERIFY_READONLY")
        self.assertNotIn(paths["approval"], self.spark.delta)

    def test_dq_quarantine_written_but_approval_denied(self):
        from types import SimpleNamespace
        self.findings = (SimpleNamespace(classification="QUARANTINE",
                                         reason="FHIR_MISSING_DOB", detail="source missing",
                                         resource_type="Patient", resource_id="p1",
                                         source_file="example.json"),)
        outcome = self.execute()
        self.assertEqual(outcome.status, "HOLD_DQ")
        paths = nb._silver_publication_paths(REQUEST)
        self.assertEqual(set(self.spark.delta), {paths["quarantine"]})
        self.assertEqual(self.spark.delta[paths["quarantine"]].count(), 1)
        self.assertNotIn(paths["approval"], self.spark.delta)

    def test_corrupt_approval_count_never_skips(self):
        self.assertEqual(self.execute().status, "SILVER_APPROVED")
        paths = nb._silver_publication_paths(REQUEST)
        self.spark.delta[paths["approval"]].rows[0]["patient_count"] = 9
        self.assertEqual(self.execute(mode="SILVER_READBACK_ONLY",
                                      allow_write=False, retention_ok=False).status,
                         "VERIFY_READONLY")



class G5CandidateNativeDeltaStagedOffline(unittest.TestCase):
    """Fake native Delta and frozen F2 handoff; zero cloud access."""

    @classmethod
    def setUpClass(cls):
        # GA 0.1.7 already has the P3 planner. Never load a different
        # uninstalled source file into sys.modules for Notebook acceptance.
        from healthcare_data_engine.mapping.omop import candidate_publication
        from healthcare_data_engine.identity.candidate_handoff import (
            CandidatePersonId, CandidateVisitId, PersonVisitCandidateHandoff)
        cls.module = candidate_publication
        cls.handoff_type = PersonVisitCandidateHandoff
        cls.person_type = CandidatePersonId
        cls.visit_type = CandidateVisitId

    def setUp(self):
        hospital = "atlanta-hospital-a"
        feed = "atlanta-hospital-a-fhir-r4"
        source = "synthea-fhir:" + hospital + ":" + feed
        self.persons = tuple(self.person_type(
            hospital, source, "p%03d" % i, i+1, "PROVISIONAL")
            for i in range(100))
        self.visits = tuple(self.visit_type(
            hospital, source, "e%05d" % i, "p%03d" % (i % 100),
            i+1, i%100+1, "PROVISIONAL", "PROVISIONAL")
            for i in range(5918))
        self.scope = self.module.FrozenCandidateScope(
            hospital_id=hospital, feed_id=feed, source_system=source,
            request_id="atlanta-fhir-gh-41552666929",
            source_batch_id="a"*64,
            manifest_sha256=nb._G5_APPROVED_MANIFEST_SHA,
            silver_processing_version=nb._G4_PROCESSING,
            silver_publication_id="synthetic-silver-approval",
            mapping_sha256="c"*64,
            identity_snapshot_fingerprint="b"*64,
            patient_count=100, encounter_count=5918,
            provisional_person_count=100, provisional_visit_count=5918)
        self.handoff = self.handoff_type(
            person_lookup=self.persons,
            batch_persons=self.persons, batch_visits=self.visits,
            hospital_id=hospital, source_system=source,
            source_batch_id=self.scope.source_batch_id,
            manifest_sha256=self.scope.manifest_sha256,
            processing_version=self.scope.silver_processing_version,
            silver_publication_id=self.scope.silver_publication_id,
            snapshot_fingerprint=self.scope.identity_snapshot_fingerprint)
        self.patient = Frame([
            {"person_id":p.person_id, "person_source_value":p.source_business_key,
             "identity_state":p.state, "gender_concept_id":1}
            for p in self.persons])
        self.visit = Frame([
            {"visit_occurrence_id":e.visit_occurrence_id,
             "person_id":e.person_id,
             "source_encounter_id":e.source_encounter_id,
             "source_person_id":e.source_person_id,
             "identity_state":e.state, "parent_identity_state":e.parent_state,
             "visit_concept_id":1}
            for e in self.visits])
        from healthcare_data_engine.mapping.omop.candidates import OmopCandidates
        self.mapper_result = OmopCandidates(
            Frame([{k:v for k,v in row.items()
                    if k != "identity_state"} for row in self.patient.rows]),
            Frame([{k:v for k,v in row.items()
                    if k not in {"visit_occurrence_id", "identity_state",
                                 "parent_identity_state"}}
                    for row in self.visit.rows]),
            self.scope.mapping_sha256, 100, 5918)
        self.spark = Spark(b"")
        self.rechecked_source = []
        self.writes = []
        self.fail_after_first = False

    def fake_source_fence(self, spark, **kw):
        self.rechecked_source.append(kw)
        self.assertIs(spark, self.spark)
        self.assertIs(kw["allow_write"], False)
        self.assertIs(kw["retention_ok"], False)
        self.assertEqual(kw["request"], self.scope.request_id)
        return ("FHIR_G5_CANDIDATE_SOURCE_READONLY_P100_E5918_Q0_"
                "APPROVAL_DELTA_PASS_20261104")

    def write(self, frame, path):
        if path in self.spark.delta:
            raise FileExistsError("errorifexists simulated")
        # Persist an independent snapshot, not the caller's in-memory Frame.
        # Otherwise a simulated Delta corruption also mutates the expected
        # Mapper source and never reaches independent persisted readback.
        self.spark.delta[path] = Frame(
            [dict(record) for record in frame.rows], frame.columns)
        self.writes.append(path)
        if self.fail_after_first and len(self.writes) == 1:
            raise OSError("synthetic unknown storage acknowledgement")

    def invoke(self, *, mode="G5_CANDIDATE_WRITE", **overrides):
        args = dict(
            scope=self.scope, handoff=self.handoff,
            mapper_result=self.mapper_result,
            person_candidate=self.patient, visit_candidate=self.visit,
            mode=mode, write_authorized=True,
            clinically_reviewed=True, license_reviewed=True,
            warehouse_snapshot_verified=True,
            clinical_review_sha256="d"*64,
            license_review_sha256="e"*64,
            warehouse_snapshot_sha256=self.scope.identity_snapshot_fingerprint,
            patient_contract_json="synthetic-contract-for-offline-only",
            encounter_contract_json="synthetic-contract-for-offline-only",
        )
        args.update(overrides)
        with patch.dict(nb.plan_and_write_g5_candidate_delta.__globals__, {
            "_write_delta": self.write,
            "_delta_snapshot_exists": lambda spark, path: path in self.spark.delta,
            "verify_fhir_g5_candidate_source_readonly": self.fake_source_fence,
        }):
            return nb.plan_and_write_g5_candidate_delta(self.spark, **args)

    def test_p3_first_write_approval_last_then_replay_skip(self):
        self.assertEqual(self.invoke(), "G5_CANDIDATE_APPROVED_DELTA_ONLY_NOT_GOLD")
        paths = nb._frozen_fhir_candidate_paths(self.scope)
        self.assertEqual(self.writes, [paths["person"], paths["visit"],
                                       paths["approval"]])
        approval = self.spark.delta[paths["approval"]].rows
        self.assertEqual(len(approval), 1)
        self.assertEqual(approval[0]["status"], "CANDIDATE_APPROVED")
        self.assertEqual(approval[0]["scope_receipt_key"], self.scope.receipt_key)
        self.assertEqual(self.invoke(), "G5_CANDIDATE_SKIP_VERIFIED_NOT_GOLD")
        self.assertEqual(len(self.writes), 3)
        self.assertEqual(len(self.rechecked_source), 2)

    @staticmethod
    def technical_kwargs():
        return {
            "clinically_reviewed": False,
            "license_reviewed": False,
            "clinical_review_sha256": None,
            "license_review_sha256": None,
            "technical_evidence_sha256": "f" * 64,
            # SOURCE-ONLY synthetic protected Stage callback. This fixture
            # cannot onboard a real trusted controller or publish to Fabric.
            "trusted_technical_release_gate": lambda _scope, _digest: True,
        }

    def test_p3_technical_only_approval_last_and_replay_without_humans(self):
        args = self.technical_kwargs()
        self.assertEqual(
            self.invoke(**args), "G5_CANDIDATE_APPROVED_DELTA_ONLY_NOT_GOLD")
        paths = nb._frozen_fhir_candidate_paths(self.scope)
        self.assertEqual(self.writes, [
            paths["person"], paths["visit"], paths["approval"]])
        receipt = self.spark.delta[paths["approval"]].rows[0]
        self.assertEqual(
            receipt["evidence_contract"], "G5_TECHNICAL_F1F2_V1")
        self.assertEqual(
            receipt["technical_evidence_sha256"], "f" * 64)
        self.assertNotIn("clinical_review_sha256", receipt)
        self.assertNotIn("license_review_sha256", receipt)
        self.assertEqual(
            self.invoke(**args), "G5_CANDIDATE_SKIP_VERIFIED_NOT_GOLD")
        self.assertEqual(len(self.writes), 3)
        # Historical signed-v1 cannot mistake a v2 technical receipt for
        # an old two-human approved Candidate or silently overwrite it.
        self.assertEqual(
            self.invoke(), "G5_CANDIDATE_HOLD_READBACK_OR_APPROVAL_CONFLICT")
        self.assertEqual(len(self.writes), 3)
        self.assertEqual(
            self.invoke(
                mode="G5_CANDIDATE_READBACK_ONLY", write_authorized=False,
                **{**args, "trusted_technical_release_gate": None}),
            "G5_CANDIDATE_SKIP_VERIFIED_NOT_GOLD")
        self.assertEqual(len(self.writes), 3)

    def test_p3_technical_only_no_stage_owner_does_not_write(self):
        args = self.technical_kwargs()
        args["trusted_technical_release_gate"] = None
        with self.assertRaisesRegex(RuntimeError, "STAGE_RELEASE_UNTRUSTED"):
            self.invoke(**args)
        self.assertFalse(self.rechecked_source)
        self.assertFalse(self.writes)
        args["technical_evidence_sha256"] = "bad SHA"
        with self.assertRaisesRegex(RuntimeError, "EVIDENCE_SHA_NOT_PINNED"):
            self.invoke(**args)
        self.assertFalse(self.writes)
        args["technical_evidence_sha256"] = "f" * 64
        args["clinical_review_sha256"] = "d" * 64
        with self.assertRaisesRegex(RuntimeError, "CANNOT_FORGE_REVIEWS"):
            self.invoke(**args)
        self.assertFalse(self.writes)

    def test_p3_partial_write_or_unknown_ack_requires_readback_not_retry(self):
        self.fail_after_first = True
        self.assertEqual(self.invoke(), "G5_CANDIDATE_VERIFY_READONLY_UNKNOWN_ACK")
        self.assertEqual(len(self.writes), 1)
        self.assertEqual(self.invoke(), "G5_CANDIDATE_VERIFY_READONLY_PARTIAL_OUTPUT")
        self.assertEqual(len(self.writes), 1)

    def test_p3_bad_flags_and_missing_review_rejected_before_any_io(self):
        cases = (
            {"mode": "HALT"}, {"write_authorized": False},
            {"clinically_reviewed": False}, {"license_reviewed": False},
            {"warehouse_snapshot_verified": False},
            {"clinical_review_sha256": "no-evidence"},
            {"warehouse_snapshot_sha256": "f" * 64},
        )
        for mutation in cases:
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                self.invoke(**mutation)
            self.assertFalse(self.rechecked_source)
            self.assertFalse(self.writes)

    def test_p3_readback_mode_never_writes(self):
        self.assertEqual(self.invoke(
            mode="G5_CANDIDATE_READBACK_ONLY", write_authorized=False,
            clinically_reviewed=False, license_reviewed=False),
            "G5_CANDIDATE_HOLD_NOT_FOUND_READONLY")
        self.assertFalse(self.writes)
        self.assertEqual(len(self.rechecked_source), 1)

    def test_p3_wrong_identity_or_wrong_concept_payload_holds(self):
        broken = Frame([{**r, "person_id":9999} if idx == 0 else r
                         for idx, r in enumerate(self.patient.rows)])
        with self.assertRaisesRegex(RuntimeError,
                                    "HOLD_G5_CANDIDATE_IDENTITY_OR_FK_DRIFT"):
            self.invoke(person_candidate=broken)
        self.assertEqual(self.writes, [])

    def test_p3_mapped_concepts_cannot_be_replaced_after_strict_mapper(self):
        bad_person = Frame([
            {**r, "gender_concept_id":999999} if i == 0 else r
            for i, r in enumerate(self.patient.rows)])
        with self.assertRaisesRegex(
                RuntimeError, "HOLD_G5_MAPPER_CANDIDATE_PAYLOAD_CHANGED"):
            self.invoke(person_candidate=bad_person)
        self.assertFalse(self.writes)

        bad_visit = Frame([
            {**r, "visit_concept_id":999999} if i == 0 else r
            for i, r in enumerate(self.visit.rows)])
        with self.assertRaisesRegex(
                RuntimeError, "HOLD_G5_MAPPER_CANDIDATE_PAYLOAD_CHANGED"):
            self.invoke(visit_candidate=bad_visit)
        self.assertFalse(self.writes)

    def test_p3_unapproved_extra_payload_columns_fail_before_writes(self):
        extra = Frame([{**r, "fabric_invented_concept":123}
                       for r in self.patient.rows])
        with self.assertRaisesRegex(
                RuntimeError, "HOLD_G5_MAPPER_CANDIDATE_SCHEMA_OR_COUNT"):
            self.invoke(person_candidate=extra)
        self.assertFalse(self.writes)

    def test_p3_readback_tamper_refuses_skip(self):
        self.assertEqual(self.invoke(), "G5_CANDIDATE_APPROVED_DELTA_ONLY_NOT_GOLD")
        paths = nb._frozen_fhir_candidate_paths(self.scope)
        self.spark.delta[paths["visit"]].rows[0]["visit_concept_id"] = 99999
        self.assertEqual(self.invoke(), "G5_CANDIDATE_HOLD_READBACK_OR_APPROVAL_CONFLICT")
        self.assertEqual(len(self.writes), 3)

    def test_p3_bad_approval_refuses_skip(self):
        self.assertEqual(self.invoke(), "G5_CANDIDATE_APPROVED_DELTA_ONLY_NOT_GOLD")
        paths = nb._frozen_fhir_candidate_paths(self.scope)
        self.spark.delta[paths["approval"]].rows[0]["status"] = "GOLD_COMMITTED"
        self.assertEqual(self.invoke(), "G5_CANDIDATE_HOLD_READBACK_OR_APPROVAL_CONFLICT")
        self.assertEqual(len(self.writes), 3)

    def test_p3_missing_approval_requires_readback_before_any_retry(self):
        self.assertEqual(self.invoke(), "G5_CANDIDATE_APPROVED_DELTA_ONLY_NOT_GOLD")
        paths = nb._frozen_fhir_candidate_paths(self.scope)
        del self.spark.delta[paths["approval"]]
        self.assertEqual(self.invoke(), "G5_CANDIDATE_VERIFY_READONLY_PARTIAL_OUTPUT")
        self.assertEqual(len(self.writes), 3)

    def test_p3_scope_drift_blocks_before_any_source_read(self):
        for mutation in (
            {"manifest_sha256": "f" * 64}, {"mapping_sha256": "f" * 64},
            {"request_id": "atlanta-fhir-gh-41552666928"},
            {"provisional_person_count": 0},
            {"provisional_visit_count": 0},
        ):
            with self.subTest(mutation=mutation):
                other = self.module.FrozenCandidateScope(
                    **{**self.scope.__dict__, **mutation})
                with self.assertRaises(RuntimeError):
                    self.invoke(scope=other)
            self.assertFalse(self.rechecked_source)
            self.assertFalse(self.writes)

    def test_real_business_entry_fails_on_missing_technical_release_before_spark(self):
        with self.assertRaisesRegex(RuntimeError,
                                    "HOLD_G5_BUSINESS_TECHNICAL_STAGE_RELEASE_MISSING"):
            nb.execute_g5_person_visit_business(
                self.spark, scope=self.scope, handoff=self.handoff,
                concepts_from_verified_warehouse=None,
                mapping_profile_bytes=b"{}",
                raw_publish_run_id="source-real",
                patient_contract_json=PATIENT,
                encounter_contract_json=ENCOUNTER,
                mode="G5_CANDIDATE_WRITE", write_authorized=True,
                warehouse_snapshot_verified=False,
                technical_evidence_sha256="d"*64,
                warehouse_snapshot_sha256=self.scope.identity_snapshot_fingerprint)
        self.assertFalse(self.writes)
        self.assertFalse(self.spark.delta)

    def test_real_business_entry_rejects_unpinned_mapping_before_spark(self):
        with self.assertRaisesRegex(RuntimeError,
                                    "HOLD_G5_BUSINESS_MAPPING_PROFILE_BYTES"):
            nb.execute_g5_person_visit_business(
                self.spark, scope=self.scope, handoff=self.handoff,
                concepts_from_verified_warehouse=None,
                mapping_profile_bytes=b'{"unapproved": true}',
                raw_publish_run_id="source-real",
                patient_contract_json=PATIENT,
                encounter_contract_json=ENCOUNTER,
                mode="G5_CANDIDATE_WRITE", write_authorized=True,
                clinically_reviewed=True, license_reviewed=True,
                warehouse_snapshot_verified=True,
                clinical_review_sha256="d"*64,
                license_review_sha256="e"*64,
                warehouse_snapshot_sha256=self.scope.identity_snapshot_fingerprint)
        self.assertFalse(self.writes)
        self.assertFalse(self.spark.delta)

    def test_p3_notebook_has_no_write_runmode_dispatch(self):
        import inspect
        src = inspect.getsource(nb.plan_and_write_g5_candidate_delta)
        self.assertIn("G5_CANDIDATE_WRITE", src)
        self.assertTrue(callable(nb.execute_g5_person_visit_business))
        self.assertIn("_write_delta(person_candidate", src)
        self.assertIn("_write_delta(approval, paths", src)
        native = (ROOT / "azure-fabric/workspaces/healthcare-omop/"
                  "nb_fhir_ingest.Notebook/notebook-content.py").read_text()
        main = native.split('if __name__ == "__main__":')[-1]
        self.assertNotIn('run_mode == "G5_CANDIDATE_WRITE"', main)
        self.assertIn('run_mode = "HALT"', native)




class G5TrustedControllerOffline(unittest.TestCase):
    """P3.20 negative guard: even forged approved provider dictionaries MUST HOLD."""

    def setUp(self):
        # Share only the fixture, not its inherited test methods: otherwise
        # mutating the mapping SHA would rerun unrelated existing P3 tests.
        G5CandidateNativeDeltaStagedOffline.setUpClass()
        fixture = G5CandidateNativeDeltaStagedOffline(
            "test_p3_notebook_has_no_write_runmode_dispatch")
        fixture.setUp()
        self.module = fixture.module
        self.handoff = fixture.handoff
        self.scope = fixture.scope
        self.spark = fixture.spark
        self.profile = b"synthetic-only-profile-not-authorized"
        self.scope = self.module.FrozenCandidateScope(
            **{**self.scope.__dict__,
               "mapping_sha256": hashlib.sha256(self.profile).hexdigest()})
        self.business_calls = []

    def provider(self):
        owner = self
        class FakeProvider:
            snapshot_number = 0
            def load_pinned_inputs(self):
                return {
                    "scope": owner.scope, "handoff": owner.handoff,
                    "mapping_profile_bytes": owner.profile,
                    "raw_publish_run_id": "synthetic-publication",
                    "patient_contract_json": PATIENT,
                    "encounter_contract_json": ENCOUNTER}
            def verify_signed_clinical_review(self, scope, profile):
                return {
                    "status": "SIGNED_CLINICAL_APPROVED",
                    "source_batch_id": scope.source_batch_id,
                    "mapping_sha256": scope.mapping_sha256,
                    "reviewer": "synthetic-only-not-a-real-reviewer",
                    "review_sha256": "d"*64}
            def verify_license_rights(self, scope, profile):
                return {
                    "status": "LICENSE_USE_APPROVED",
                    "source_batch_id": scope.source_batch_id,
                    "mapping_sha256": scope.mapping_sha256,
                    "reviewer": "synthetic-only-not-a-real-license",
                    "license_sha256": "e"*64}
            def capture_full_warehouse_snapshot(self, scope):
                self.snapshot_number += 1
                return {
                    "status": "INDEPENDENT_SIX_TABLE_SQL_PASS",
                    "warehouse_id": "7a6d08da-278d-4603-8a3b-28640110984c",
                    "fingerprint": scope.identity_snapshot_fingerprint,
                    "connection_id": f"synthetic-connection-{self.snapshot_number}"}
            def read_verified_warehouse_concepts(self, scope):
                return Frame([{"concept_id": 1}])
        return FakeProvider()

    def controlled(self, provider=None, mode="G5_CANDIDATE_WRITE"):
        def business(spark, **kwargs):
            self.assertIs(spark, self.spark)
            self.business_calls.append(kwargs)
            return "SYNTHETIC_P3_BUSINESS_ENTRY_CALLED_NOT_CLOUD"
        with patch.dict(
            nb.execute_g5_candidate_from_trusted_controller.__globals__,
            {"execute_g5_person_visit_business": business},
        ):
            return nb.execute_g5_candidate_from_trusted_controller(
                self.spark, provider=provider, mode=mode)

    def test_g5_controller_missing_provider_holds_before_spark(self):
        with self.assertRaisesRegex(RuntimeError, "HOLD_G5_NATIVE_CANDIDATE_WRITE_OR_MODE_DISABLED"):
            self.controlled()
        self.assertEqual(self.business_calls, [])
        self.assertFalse(self.spark.delta)

    def test_g5_controller_rejects_profile_sha_drift_before_external_queries(self):
        p = self.provider()
        original = p.load_pinned_inputs
        p.load_pinned_inputs = lambda: {**original(),
                                      "mapping_profile_bytes": b"unreviewed"}
        with self.assertRaisesRegex(RuntimeError, "HOLD_G5_NATIVE_CANDIDATE_WRITE_OR_MODE_DISABLED"):
            self.controlled(p)
        self.assertEqual(p.snapshot_number, 0)
        self.assertEqual(self.business_calls, [])

    def test_g5_controller_clinical_denial_never_reads_sql(self):
        p = self.provider()
        p.verify_signed_clinical_review = lambda scope, profile: {
            "status": "PENDING_REVIEW"}
        with self.assertRaisesRegex(RuntimeError, "HOLD_G5_NATIVE_CANDIDATE_WRITE_OR_MODE_DISABLED"):
            self.controlled(p)
        self.assertEqual(p.snapshot_number, 0)
        self.assertFalse(self.business_calls)

    def test_g5_controller_license_denial_never_reads_sql(self):
        p = self.provider()
        p.verify_license_rights = lambda scope, profile: {"status": "PENDING"}
        with self.assertRaisesRegex(RuntimeError, "HOLD_G5_NATIVE_CANDIDATE_WRITE_OR_MODE_DISABLED"):
            self.controlled(p)
        self.assertEqual(p.snapshot_number, 0)

    def test_g5_controller_rejects_nonindependent_sql_connections(self):
        p = self.provider()
        original = p.capture_full_warehouse_snapshot
        p.capture_full_warehouse_snapshot = lambda scope: {
            **original(scope), "connection_id": "same-connection"}
        with self.assertRaisesRegex(RuntimeError, "HOLD_G5_NATIVE_CANDIDATE_WRITE_OR_MODE_DISABLED"):
            self.controlled(p)
        self.assertEqual(p.snapshot_number, 0)
        self.assertFalse(self.business_calls)

    def test_g5_controller_rejects_sql_identity_or_fingerprint_drift(self):
        for changed in ({"fingerprint": "0"*64},
                        {"warehouse_id": "other-warehouse"},
                        {"status": "PREVIEW_ONLY"}):
            p = self.provider()
            original = p.capture_full_warehouse_snapshot
            p.capture_full_warehouse_snapshot = (
                lambda scope, fn=original, mutation=changed:
                {**fn(scope), **mutation})
            with self.subTest(changed=changed):
                with self.assertRaisesRegex(RuntimeError, "HOLD_G5_NATIVE_CANDIDATE_WRITE_OR_MODE_DISABLED"):
                    self.controlled(p)
                self.assertFalse(self.business_calls)

    def test_g5_controller_rejects_missing_f1_concept_evidence(self):
        p = self.provider()
        p.read_verified_warehouse_concepts = lambda scope: None
        with self.assertRaisesRegex(RuntimeError, "HOLD_G5_NATIVE_CANDIDATE_WRITE_OR_MODE_DISABLED"):
            self.controlled(p)
        self.assertFalse(self.business_calls)

    def test_g5_controller_forged_complete_provider_cannot_write(self):
        p = self.provider()
        # This provider claims all approved receipts, two independent SQL
        # connections and real F1 concepts. All claims are self-authored.
        with self.assertRaisesRegex(
                RuntimeError, "HOLD_G5_NATIVE_CANDIDATE_WRITE_OR_MODE_DISABLED"):
            self.controlled(p)
        self.assertEqual(p.snapshot_number, 0)
        self.assertEqual(self.business_calls, [])
        self.assertFalse(self.spark.delta)

    def test_g5_controller_readback_rejects_provider_and_spark(self):
        p = self.provider()
        with self.assertRaisesRegex(
                RuntimeError, "HOLD_G5_NATIVE_CALLER_PROVIDER_OR_SPARK_UNTRUSTED"):
            self.controlled(p, mode="G5_CANDIDATE_READBACK_ONLY")
        self.assertEqual(p.snapshot_number, 0)
        self.assertEqual(self.business_calls, [])
        self.assertFalse(self.spark.delta)

    def test_g5_controller_not_exposed_as_public_notebook_write_runmode(self):
        native = (ROOT / "azure-fabric/workspaces/healthcare-omop/"
                  "nb_fhir_ingest.Notebook/notebook-content.py").read_text()
        main = native.split('if __name__ == "__main__":')[-1]
        self.assertNotIn("execute_g5_candidate_from_trusted_controller(", main)
        self.assertNotIn('run_mode == "G5_CANDIDATE_WRITE"', main)
        self.assertIn('run_mode = "HALT"', native)


if __name__ == "__main__":
    unittest.main()

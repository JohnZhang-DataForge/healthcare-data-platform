"""Pure offline negative tests for v1 Fabric FHIR -> OMOP interface.

All names and counts are G4 *metadata fixtures*, not a physical Delta readback.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

SHARED = Path(__file__).resolve().parents[1]
ROOT = SHARED.parent
sys.path.insert(0, str(SHARED / "src"))

from healthcare_data_engine.models.batch_context import BatchContext
from healthcare_data_engine.models.fabric_omop_handoff import (
    HandoffHold, STRUCTURAL_ONLY, PINNED_CANONICAL_SHA,
    load_handoff_contract, calculate_source_batch_id,
    validate_handoff_envelope, classify_source_replay,
    source_replay_identity,
)

CONTRACT_PATH = SHARED / "contracts" / "fabric-fhir-omop-handoff-v1.json"


def valid_envelope(contract):
    hospital = "atlanta-hospital-a"
    feed = "atlanta-hospital-a-fhir-r4"
    raw_source = "synthea-fhir"
    request = "atlanta-fhir-gh-41552666929"
    manifest_sha = contract["reference_approved_batch"]["delivered_manifest_sha256"]
    processing = contract["silver"]["processing_version"]
    batch_id = calculate_source_batch_id(
        hospital, feed, raw_source, request, manifest_sha)
    digest = hashlib.sha256(processing.encode()).hexdigest()
    prefix = (contract["silver"]["root"] + "/" + hospital + "/" + feed + "/" +
              request + "/processing=" + digest)
    return {
        "contract_id": contract["contract_id"],
        "contract_version": contract["contract_version"],
        "producer": {
            "hospital_id": hospital, "feed_id": feed,
            "raw_source_system": raw_source,
            "canonical_source_system": ":".join((raw_source, hospital, feed)),
            "request_id": request,
            "source_batch_id": batch_id,
            "manifest_sha256": manifest_sha,
            "processing_version": processing,
        },
        "paths": {
            "patient": prefix + "/canonical_patient",
            "encounter": prefix + "/canonical_encounter",
            "approval": prefix + "/silver_approval",
        },
        "approval": {
            "status": "SILVER_APPROVED", "source_batch_id": batch_id,
            "manifest_sha256": manifest_sha,
            "processing_version": processing,
            "publication_id": "fixed-fixture-publication-v1",
            "patient_count": 100, "encounter_count": 5918,
            "quarantine_count": 0,
            "patient_contract_sha256": PINNED_CANONICAL_SHA["patient"],
            "encounter_contract_sha256": PINNED_CANONICAL_SHA["encounter"],
            "source_preservation_strategy": "DELTA_RAW_SNAPSHOT_V1",
        },
        "consumer": dict(contract["fabric"]),
    }


class HandoffV1Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = CONTRACT_PATH.read_bytes()
        cls.sha = hashlib.sha256(cls.raw).hexdigest()
        cls.contract = load_handoff_contract(cls.raw, cls.sha)

    def setUp(self):
        self.e = valid_envelope(self.contract)

    def assert_hold(self, mutation):
        envelope = copy.deepcopy(self.e)
        mutation(envelope)
        with self.assertRaises(HandoffHold):
            validate_handoff_envelope(self.contract, envelope)

    def test_version_pins_and_canonical_source_authorities(self):
        self.assertEqual(self.contract["contract_version"], "1.0.0")
        self.assertEqual(self.contract["status"], "CONTRACT_ONLY_NO_WRITE")
        self.assertEqual(self.contract["identity"]["current_f1_status"],
                         "PENDING_REAL_VALIDATION")
        self.assertEqual(self.contract["vocabulary"]["current_f1_status"],
                         "PENDING_REAL_VALIDATION")
        for entity in ("patient", "encounter"):
            ref = self.contract["canonical_contracts"][entity]
            raw = (ROOT / ref["source_path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), ref["raw_sha256"])
            schema = json.loads(raw)
            self.assertEqual(
                set(ref["required_fields"]),
                {field["name"] for field in schema["fields"]})
            self.assertEqual(ref["source_primary_key"], schema["primary_key"])
            self.assertEqual(schema["canonical_version"], "v1")
        self.assertEqual(self.contract["canonical_contracts"]["encounter"][
            "person_fk_field"], "source_person_id")

    def test_load_rejects_wrong_sha_duplicate_keys_unapproved_rules(self):
        with self.assertRaisesRegex(HandoffHold, "CONTRACT_SHA_MISMATCH"):
            load_handoff_contract(self.raw + b" ", self.sha)
        with self.assertRaises(HandoffHold):
            load_handoff_contract(self.raw, "0" * 64)
        with self.assertRaisesRegex(HandoffHold, "DUPLICATE_JSON_KEY"):
            bad = b'{"a":1,"a":2}'
            load_handoff_contract(bad, hashlib.sha256(bad).hexdigest())
        for mutate in (
            lambda c: c.update(status="GOLD_COMMITTED"),
            lambda c: c["fabric"].update(warehouse_item_id="a" * 36),
            lambda c: c["identity"].update(person_source_scope=[
                "source_record_id"]),
            lambda c: c["silver"].update(approved_status="ANY"),
            lambda c: c["evidence"].update(stage1_performs_writes=True),
            lambda c: c["canonical_contracts"]["patient"].update(
                raw_sha256="f" * 64),
        ):
            c = copy.deepcopy(self.contract)
            mutate(c)
            raw = (json.dumps(c, sort_keys=True) + "\n").encode()
            with self.subTest(mutate=mutate), self.assertRaises(HandoffHold):
                load_handoff_contract(raw, hashlib.sha256(raw).hexdigest())

    def test_exact_stable_batch_id_matches_batch_context(self):
        e = self.e["producer"]
        from datetime import date, datetime, timezone
        ctx = BatchContext(
            hospital_id=e["hospital_id"], feed_id=e["feed_id"],
            source_system=e["raw_source_system"], request_id=e["request_id"],
            manifest_sha256=e["manifest_sha256"],
            processing_version=e["processing_version"],
            processing_run_id="g4:" + e["request_id"],
            source_version="FHIR_R4", source_ingest_date=date(2026,11,2),
            processed_at=datetime.now(timezone.utc))
        self.assertEqual(ctx.source_batch_id, e["source_batch_id"])
        self.assertEqual(ctx.namespaced_source_system,
                         e["canonical_source_system"])

    def test_valid_metadata_never_claims_physical_gold(self):
        self.assertEqual(
            validate_handoff_envelope(self.contract, self.e), STRUCTURAL_ONLY)
        self.assertNotIn("GOLD", STRUCTURAL_ONLY)
        self.assertNotIn("APPROVED", STRUCTURAL_ONLY)
        self.assertEqual(self.contract["output"]["gold_state"],
                         "NOT_AUTHORIZED_BY_HANDOFF")

    def test_unapproved_quarantine_and_zero_count_hold(self):
        for key, value in (
            ("status", "HOLD_DQ"),
            ("status", "APPROVAL_DENIED"),
            ("status", "SILVER_PENDING"),
            ("quarantine_count", 26),
            ("quarantine_count", True),
            ("patient_count", 0),
            ("encounter_count", -1),
            ("patient_count", True),
            ("publication_id", ""),
            ("source_preservation_strategy", "RAW_BLOB_UNVERIFIED"),
        ):
            with self.subTest(key=key, value=value):
                self.assert_hold(
                    lambda e, k=key, v=value: e["approval"].__setitem__(k, v))

    def test_tampered_identity_namespace_manifest_and_source_batch_hold(self):
        for key, value in (
            ("hospital_id", "../wrong-hospital"),
            ("feed_id", "other-feed"),
            ("raw_source_system", "other"),
            ("canonical_source_system", "synthea-fhir"),
            ("request_id", "../../malicious"),
            ("manifest_sha256", "f" * 64),
            ("source_batch_id", "f" * 64),
            ("processing_version", "other-engine"),
        ):
            with self.subTest(key=key, value=value):
                self.assert_hold(
                    lambda e, k=key, v=value: e["producer"].__setitem__(k, v))

    def test_bad_fabric_ids_and_untrusted_delta_paths_hold(self):
        for key in ("workspace_id", "lakehouse_id", "warehouse_item_id",
                    "warehouse_name"):
            with self.subTest(key=key):
                self.assert_hold(
                    lambda e, k=key: e["consumer"].__setitem__(k, "different"))
        for key in ("patient", "encounter", "approval"):
            with self.subTest(key=key):
                self.assert_hold(
                    lambda e, k=key: e["paths"].__setitem__(
                        k, "Files/omop_candidate/another/hospital"))
        self.assert_hold(
            lambda e: e["approval"].__setitem__(
                "manifest_sha256", "f"*64))
        self.assert_hold(
            lambda e: e["approval"].__setitem__(
                "patient_contract_sha256", "f"*64))
        self.assert_hold(
            lambda e: e["approval"].__setitem__(
                "encounter_contract_sha256", "f"*64))
        self.assert_hold(
            lambda e: e["approval"].__setitem__(
                "source_batch_id", "f"*64))

    def test_unknown_or_missing_fields_never_silently_accepted(self):
        for key in ("producer", "paths", "approval", "consumer"):
            with self.subTest(key=key):
                self.assert_hold(lambda e,k=key:e.pop(k))
        self.assert_hold(lambda e: e.__setitem__("write_authorized", True))
        self.assert_hold(lambda e: e["approval"].__setitem__(
            "additional_approval", "SILVER_APPROVED"))
        self.assert_hold(lambda e: e["approval"].pop("publication_id"))
        self.assert_hold(lambda e: e["producer"].__setitem__(
            "omop_person_id", 1))

    def test_source_replay_contract_is_not_omop_id(self):
        self.assertEqual(
            classify_source_replay(self.e, self.e),
            "SAME_SOURCE_ENVELOPE_STRUCTURAL_ONLY")
        self.assertEqual(len(source_replay_identity(self.e)), 4)
        modified = copy.deepcopy(self.e)
        modified["producer"]["hospital_id"] = "another-hospital"
        self.assertEqual(classify_source_replay(self.e, modified),
                         "DIFFERENT_SOURCE_REQUEST")
        modified = copy.deepcopy(self.e)
        modified["producer"]["manifest_sha256"] = "f" * 64
        self.assertEqual(classify_source_replay(self.e, modified),
                         "HOLD_SOURCE_MANIFEST_CONFLICT")
        modified = copy.deepcopy(self.e)
        modified["producer"]["processing_version"] = "new-processor"
        self.assertEqual(classify_source_replay(self.e, modified),
                         "HOLD_SOURCE_PROCESSING_VERSION")
        modified = copy.deepcopy(self.e)
        modified["approval"]["publication_id"] = "different"
        self.assertEqual(classify_source_replay(self.e, modified),
                         "HOLD_APPROVAL_FENCE_DRIFT")


if __name__ == "__main__":
    unittest.main()

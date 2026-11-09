"""SOURCE-ONLY tests: approved G4 has TWO different immutable manifest digests.

The Shared G4 source_batch_id uses delivered Azure Landing Manifest SHA with
source_system 'synthea-fhir'. The published manifest separately pins upstream
Generator SHA and target_format FHIR_R4. Neither digest may be substituted.
No real Azure/Fabric connection or historical Batch mutation in this suite.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
import hashlib
import json
import unittest

from blob_batch_ledger import BlobMissing, LedgerHold, Snapshot, StageScope, precheck, verify_source
from healthcare_data_engine.models.batch_context import BatchContext


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode()


class FixtureBackend:
    """Exact-key read-only fake, not a usable live Azure credential."""
    def __init__(self, entries):
        self.entries = entries
        self.reads = []

    def read(self, key):
        self.reads.append(key)
        if key not in self.entries:
            raise BlobMissing()
        return self.entries[key]


class G4IdentityBridgeTests(unittest.TestCase):
    def setUp(self):
        self.upstream = "7e4ee4e2676e42d91e955754b7fc4f600838047c17195a630aca851b7204f9d9"
        self.request = "atlanta-fhir-gh-41552666929"
        self.hospital = "atlanta-hospital-a"
        self.feed = "atlanta-hospital-a-fhir-r4"
        self.payload = b'{"resourceType":"Bundle","entry":[]}'
        self.data_key = (
            f"clinical/v1/{self.hospital}/{self.feed}/{self.request}/"
            "FHIR_R4/Bundle-001.json"
        )
        self.manifest = canonical({
            "schema_version": "healthcare-azure-blob-landing-manifest-v1",
            "hospital_id": self.hospital,
            "feed_id": self.feed,
            "request_id": self.request,
            "source_manifest_sha256": self.upstream,
            "target_format": "FHIR_R4",
            "objects": [{
                "blob_key": self.data_key,
                "sha256": digest(self.payload),
                "etag": '"sample-payload"',
                "size_bytes": len(self.payload),
            }],
        })
        self.delivered = digest(self.manifest)
        self.context = BatchContext(
            hospital_id=self.hospital, feed_id=self.feed,
            source_system="synthea-fhir", request_id=self.request,
            manifest_sha256=self.delivered,
            processing_version="fhir-silver-canonical-v1:engine-0.1.1",
            processing_run_id="g4:" + self.request, source_version="FHIR_R4",
            source_ingest_date=date(2026, 11, 2),
            processed_at=datetime(2026, 11, 9, tzinfo=timezone.utc))
        self.scope = StageScope(
            context=self.context, stage="SILVER_APPROVED",
            landing_manifest_sha256=self.delivered,
            landing_manifest_etag='"sample-manifest"',
            mapper_version="g4-canonical-v1",
            wheel_version="0.1.1",
            mapping_profile_sha256="a"*64,
            publication_id="approved-g4-physical-publication",
            publisher_source_manifest_sha256=self.upstream,
            landing_target_format="FHIR_R4",
        )
        self.backend = FixtureBackend({
            self.scope.source_key: Snapshot(self.manifest, '"sample-manifest"'),
            self.data_key: Snapshot(self.payload, '"sample-payload"'),
        })

    def test_preserves_historical_namespaced_batch_id_without_rewriting_g4(self):
        self.assertEqual(self.scope.context.source_system, "synthea-fhir")
        self.assertEqual(self.scope.context.source_version, "FHIR_R4")
        self.assertEqual(self.scope.identity()["batch_id"],
                         self.context.source_batch_id)
        self.assertEqual(self.scope.identity()["source_manifest_sha256"],
                         self.delivered)
        self.assertEqual(self.scope.identity()["publisher_source_manifest_sha256"],
                         self.upstream)
        self.assertNotEqual(self.delivered, self.upstream)
        self.assertEqual(self.scope.identity()["landing_target_format"], "FHIR_R4")

    def test_verified_source_and_blob_only_first_precheck(self):
        verify_source(self.backend, self.scope)
        self.assertEqual(self.backend.reads, [self.scope.source_key, self.data_key])
        self.assertEqual(precheck(self.backend, self.scope), "NEW")
        self.assertTrue(all(not x.startswith("processed/") for x in self.backend.entries))

    def test_missing_explicit_bridge_rejected_before_any_storage_use(self):
        for kwargs in (
            {"publisher_source_manifest_sha256": None},
            {"landing_target_format": None},
            {"landing_target_format": "HL7_V2"},
            {"publisher_source_manifest_sha256": "not-a-sha"},
            {"landing_manifest_sha256": "f"*64},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(LedgerHold):
                StageScope(**{**vars(self.scope), **kwargs})

    def test_upstream_source_manifest_drift_holds(self):
        changed = replace(self.scope, publisher_source_manifest_sha256="f"*64)
        with self.assertRaisesRegex(LedgerHold, "LANDING_MANIFEST_IDENTITY_CONFLICT"):
            verify_source(self.backend, changed)

    def test_format_and_payload_drift_hold(self):
        changed_manifest = self.manifest.replace(b'"FHIR_R4"', b'"HL7_V2"')
        with self.assertRaisesRegex(LedgerHold, "LEGACY_G4_SOURCE_BRIDGE_REQUIRED"):
            # New delivered SHA is inconsistent with the historical G4 batch.
            replace(self.scope, landing_manifest_sha256=digest(changed_manifest))
        self.backend.entries[self.data_key] = Snapshot(b"altered", '"sample-payload"')
        with self.assertRaisesRegex(LedgerHold, "LANDING_PAYLOAD_DRIFT"):
            verify_source(self.backend, self.scope)

    def test_wrong_logical_source_and_version_not_auto_inferred(self):
        for source, version in (("synthea-fhir", "HL7_V2"),
                                ("invented-fhir", "FHIR_R4")):
            bad_context = replace(self.context, source_system=source,
                                  source_version=version)
            with self.assertRaises(LedgerHold):
                replace(self.scope, context=bad_context)
        # A new FHIR_R4 pipeline has a DIFFERENT source Batch ID even with
        # the same delivered bytes; never claim it matches historical G4.
        new_context = replace(self.context, source_system="FHIR_R4")
        new_scope = replace(self.scope, context=new_context)
        self.assertNotEqual(new_scope.identity()["batch_id"],
                            self.scope.identity()["batch_id"])


if __name__ == "__main__":
    unittest.main()

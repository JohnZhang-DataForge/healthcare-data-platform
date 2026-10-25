"""New frozen FHIR + complete OIE readback -> shared Blob Publisher (offline)."""
import json
import tempfile
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from apps.clinical_producers.oie_hl7_publisher import (
    OIEReadback, OIEDeliveryBlocked, SKIP_MARKER,
    prepare_oie_hl7, publish_oie_hl7,
)
from apps.clinical_producers.azure_blob_publisher import (
    BlobAlreadyExists, BlobNotFound, BlobSnapshot,
)
from apps.synthea.synthea_new_generator.generator import (
    COMPLETED, MANIFEST_VERSION, fingerprint, validate_payload, sha256,
)
from apps.synthea.synthea_new_generator.request import SCHEMA_VERSION, normalize

CHANNEL = "69ace705-a675-45f6-b126-a3b22a65212a"
HOSP = "johns-creek-hospital-b"
FEED = "johns-creek-hospital-b-hl7-v2"
REQUEST = "johnscreek-next-0001"
AUTH = "JOHNSCREEKB"
WHEN = "20261024131530+0000"
CONTROL = "-".join((HOSP, FEED, REQUEST, "enc-one", "A01"))


def sample_hl7():
    lines = [
        ("MSH|^~\\&|SYNTHEA_SIM|JOHNSCREEKB|LANDING|SYNTHETIC|" + WHEN +
         "||ADT^A01^ADT_A01|" + CONTROL + "|P|2.5.1"),
        "EVN|A01|" + WHEN,
        "PID|1||patient-one^^^JOHNSCREEKB^MR||Demo^Patient",
    ]
    pv1 = ["PV1", "1", "I"] + [""] * 42
    pv1[19] = "enc-one^^^JOHNSCREEKB^VN"
    pv1[44] = WHEN
    return ("\r".join(lines + ["|".join(pv1)]) + "\r").encode()


class FakeBackend:
    def __init__(self):
        self.remote = {}
        self.writes = []
    def create(self, key, data, metadata, content_type):
        if key in self.remote:
            raise BlobAlreadyExists()
        etag = f'"etag-{len(self.remote)+1}"'
        self.remote[key] = BlobSnapshot(data, dict(metadata), content_type, etag)
        self.writes.append(key)
        return etag
    def read(self, key):
        if key not in self.remote:
            raise BlobNotFound()
        return self.remote[key]


class OIEAdapterTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.profile = ROOT / "config/synthea-new-generator/johns-creek-hl7.json"
        req = normalize({
            "schema_version": SCHEMA_VERSION,
            "request_id": REQUEST, "generation_mode": "NEW_ONLY",
            "population": 1, "state": "Georgia", "city": "Johns Creek",
            "seed": 67890, "reference_date": "20261024",
            "output_formats": ["FHIR_R4"],
        })
        self.folder = self.root / "requests" / REQUEST
        self.fhir = self.folder / "payload" / "fhir" / "patient.json"
        self.fhir.parent.mkdir(parents=True)
        self.fhir.write_text(json.dumps({
            "resourceType": "Bundle", "type": "collection", "entry": [
                {"fullUrl": "urn:uuid:patient-one",
                 "resource": {"resourceType": "Patient", "id": "patient-one"}},
                {"resource": {"resourceType": "Encounter", "id": "enc-one",
                              "subject": {"reference": "urn:uuid:patient-one"},
                              "class": {"system":
                                        "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                                        "code": "IMP"},
                              "status": "finished",
                              "period": {"start": "2026-10-24T09:15:30-04:00"}}},
                {"resource": {"resourceType": "Encounter", "id": "enc-two",
                              "subject": {"reference": "urn:uuid:patient-one"},
                              "class": {"system":
                                        "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                                        "code": "AMB"},
                              "status": "finished",
                              "period": {"start": "2026-10-24T10:00:00-04:00"}}},
            ]
        }), encoding="utf-8")
        (self.folder / "request.json").write_text(json.dumps({
            "request": req, "request_sha256": fingerprint(req),
        }), encoding="utf-8")
        self.manifest = self.folder / "generation-manifest.json"
        self.manifest.write_text(json.dumps({
            "schema_version": MANIFEST_VERSION,
            "request_id": REQUEST, "request_sha256": fingerprint(req),
            "status": COMPLETED,
            **validate_payload(self.folder / "payload", req),
        }), encoding="utf-8")
        self.readbacks = [
            OIEReadback("enc-one", CHANNEL, "1001", "ADT_A01", sample_hl7()),
            OIEReadback("enc-two", CHANNEL, "1002", "SKIP", SKIP_MARKER),
        ]

    def prepare(self, readbacks=None, profile=None):
        return prepare_oie_hl7(
            self.root, profile or self.profile, REQUEST,
            channel_id=CHANNEL, assigning_authority=AUTH,
            readbacks=self.readbacks if readbacks is None else readbacks)

    def publish(self, backend, readbacks=None):
        return publish_oie_hl7(
            self.root, self.profile, REQUEST,
            channel_id=CHANNEL, assigning_authority=AUTH,
            readbacks=self.readbacks if readbacks is None else readbacks,
            landing_prefix="healthcare/v1", backend=backend)

    def test_real_source_identity_hl7_sha_and_skip_count(self):
        plan, sources = self.prepare()
        self.assertEqual(plan["hospital_id"], HOSP)
        self.assertEqual(plan["feed_id"], FEED)
        self.assertEqual(plan["source_manifest_sha256"], sha256(self.manifest))
        self.assertEqual(plan["skipped_non_admissions"], 1)
        self.assertEqual(plan["verification_state"], "OIE_HL7_READBACK_VERIFIED")
        self.assertEqual(plan["objects"][0]["source_event_id"], CONTROL)
        self.assertEqual(sources, {"hl7/enc-one.hl7": sample_hl7()})

    def test_publish_bytes_and_immutable_retry_manifest_last(self):
        backend = FakeBackend()
        first = self.publish(backend)
        self.assertEqual(first["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertEqual(len(backend.writes), 2)
        self.assertEqual(backend.writes[-1], first["manifest_key"])
        key = first["objects"][0]["blob_key"]
        self.assertEqual(backend.remote[key].data, sample_hl7())
        self.assertEqual(json.loads(backend.remote[first["manifest_key"]].data)
                         ["skipped_non_admissions"], 1)
        second = self.publish(backend)
        self.assertEqual(len(backend.writes), 2)
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(second["manifest_create_status"], "ALREADY_MATCHING")

    def test_missing_oie_event_record_fails_closed(self):
        with self.assertRaisesRegex(OIEDeliveryBlocked,
                                    "INCOMPLETE_OIE_MESSAGE_COVERAGE"):
            self.prepare(self.readbacks[:1])
        self.assertEqual(self.fhir.is_file(), True)

    def test_outpatient_a01_and_inpatient_skip_are_rejected(self):
        readbacks = [
            OIEReadback("enc-one", CHANNEL, "1001", "SKIP", SKIP_MARKER),
            self.readbacks[1],
        ]
        with self.assertRaisesRegex(OIEDeliveryBlocked,
                                    "INVALID_NON_ADMISSION_SKIP"):
            self.prepare(readbacks)
        readbacks = [
            self.readbacks[0],
            OIEReadback("enc-two", CHANNEL, "1002", "ADT_A01", sample_hl7()),
        ]
        with self.assertRaisesRegex(OIEDeliveryBlocked,
                                    "ADMISSION_DISPOSITION_MISMATCH"):
            self.prepare(readbacks)

    def test_hl7_tamper_wrong_control_or_channel_fails(self):
        cases = [
            [OIEReadback("enc-one", CHANNEL, "1001", "ADT_A01",
                         sample_hl7().replace(CONTROL.encode(), b"wrong-control")),
             self.readbacks[1]],
            [OIEReadback("enc-one", "00000000-0000-4000-8000-000000000000",
                         "1001", "ADT_A01", sample_hl7()), self.readbacks[1]],
        ]
        for case in cases:
            with self.subTest(case=case[0].channel_id):
                with self.assertRaises(OIEDeliveryBlocked):
                    self.prepare(case)

    def test_wrong_hospital_route_and_duplicate_message_ids_block(self):
        profile = ROOT / "config/synthea-new-generator/atlanta-fhir.json"
        with self.assertRaisesRegex(OIEDeliveryBlocked,
                                    "OIE_HL7_PROFILE_REQUIRED"):
            self.prepare(profile=profile)
        case = [self.readbacks[0],
                OIEReadback("enc-two", CHANNEL, "1001", "SKIP", SKIP_MARKER)]
        with self.assertRaisesRegex(OIEDeliveryBlocked,
                                    "INVALID_OIE_READBACK_RECEIPT"):
            self.prepare(case)

    def test_skip_only_must_not_generate_fake_success_manifest(self):
        # Both sources are AMB, both OIE messages are independently skipped.
        source = json.loads(self.fhir.read_text())
        source["entry"][1]["resource"]["class"]["code"] = "AMB"
        self.fhir.write_text(json.dumps(source), encoding="utf-8")
        req = json.loads((self.folder / "request.json").read_text())["request"]
        self.manifest.write_text(json.dumps({
            "schema_version": MANIFEST_VERSION,
            "request_id": REQUEST, "request_sha256": fingerprint(req),
            "status": COMPLETED,
            **validate_payload(self.folder / "payload", req),
        }), encoding="utf-8")
        records = [OIEReadback("enc-one", CHANNEL, "1001", "SKIP", SKIP_MARKER),
                   self.readbacks[1]]
        with self.assertRaisesRegex(OIEDeliveryBlocked,
                                    "NO_OIE_ADT_A01_TO_PUBLISH"):
            self.prepare(records)


if __name__ == "__main__":
    unittest.main()

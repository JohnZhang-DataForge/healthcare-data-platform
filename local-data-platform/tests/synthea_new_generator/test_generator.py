"""Offline contract/negative tests; all Synthea runs are stubbed, no cloud/K8s."""
import concurrent.futures
import time
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from apps.synthea.synthea_new_generator.request import (
    SCHEMA_VERSION, GenerationBlocked, fingerprint, load_request, normalize,
)
from apps.synthea.synthea_new_generator.generator import (
    build_command, generate, validate_payload,
)


def request(**kwargs):
    d = {
        "schema_version": SCHEMA_VERSION,
        "request_id": "hospital-a-0001",
        "generation_mode": "NEW_ONLY",
        "population": 2,
        "state": "Georgia",
        "city": "Atlanta",
        "seed": 12345,
        "reference_date": "20261024",
        "output_formats": ["FHIR_R4"],
    }
    d.update(kwargs)
    return d


def emit_fixture(argv, *, bad_reference=False, invalid_fhir=False):
    base = next(x.split("=", 1)[1] for x in argv if x.startswith("--exporter.baseDirectory="))
    root = Path(base)
    flags = {x.split("=", 1)[0]:x.split("=", 1)[1] for x in argv if x.startswith("--exporter.")}
    if flags["--exporter.csv.export"] == "true":
        (root / "csv").mkdir(parents=True)
        (root / "csv/patients.csv").write_text("Id,FIRST\npatient1,Ada\n", encoding="utf-8")
        (root / "csv/encounters.csv").write_text(
            "Id,PATIENT\nenc1,patient1\n", encoding="utf-8")
    if flags["--exporter.fhir.export"] == "true":
        (root / "fhir").mkdir(parents=True)
        if invalid_fhir:
            (root / "fhir/patient1.json").write_text("broken json", encoding="utf-8")
        else:
            bundle = {
                "resourceType": "Bundle",
                "type": "collection",
                "entry": [
                    {"fullUrl": "urn:uuid:p1",
                     "resource": {"resourceType": "Patient", "id": "patient1"}},
                    {"fullUrl": "urn:uuid:e1",
                     "resource": {"resourceType": "Encounter", "id": "enc1",
                                  "subject": {"reference": "urn:uuid:missing"
                                              if bad_reference else "urn:uuid:p1"}}},
                ],
            }
            (root / "fhir/patient1.json").write_text(
                json.dumps(bundle), encoding="utf-8")


class StubSynthea:
    def __init__(self, *, code=0, bad_reference=False, invalid_fhir=False):
        self.calls = 0
        self.code = code
        self.bad_reference = bad_reference
        self.invalid_fhir = invalid_fhir

    def __call__(self, argv, **kwargs):
        self.calls += 1
        if self.code == 0:
            emit_fixture(argv, bad_reference=self.bad_reference,
                         invalid_fhir=self.invalid_fhir)
        return subprocess.CompletedProcess(argv, self.code)


class RequestContractTests(unittest.TestCase):
    def test_frozen_normalization_and_fingerprint(self):
        a = normalize(request(output_formats=["FHIR_R4", "CSV"]))
        b = normalize(request(output_formats=["CSV", "FHIR_R4"],
                              clinician_seed=12345, city="Atlanta"))
        self.assertEqual(a, b)
        self.assertEqual(fingerprint(a), fingerprint(b))
        self.assertEqual(a["synthea_version"], "v3.3.0")

    def test_rejects_unknown_invalid_or_missing_values(self):
        variants = [
            {"generation_mode": "UPDATE_ONLY"}, {"generation_mode": "MIX_DATA"},
            {"population": 0}, {"population": 501}, {"population": True},
            {"state": "Atlantis"}, {"city": ""}, {"city": "../Atlanta"},
            {"seed": -1}, {"seed": True}, {"reference_date": "20260230"},
            {"output_formats": []}, {"output_formats": ["HL7_V2"]},
            {"output_formats": ["CSV", "CSV"]},
            {"request_id": "../../escape"}, {"schema_version": "other"},
        ]
        for override in variants:
            with self.subTest(override=override), self.assertRaises(GenerationBlocked):
                normalize(request(**override))
        with self.assertRaises(GenerationBlocked):
            normalize({**request(), "unexpected": "something"})
        with self.assertRaises(GenerationBlocked):
            normalize({"schema_version": SCHEMA_VERSION})

    def test_load_request_preserves_raw_contract_for_generator(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "req.json"
            p.write_text(json.dumps(request()), encoding="utf-8")
            parsed = load_request(p)
            self.assertEqual(parsed, request())
            self.assertEqual(normalize(parsed)["synthea_version"], "v3.3.0")

    def test_request_file_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "req.json"
            p.write_text('{"request_id":"x","request_id":"y"}')
            with self.assertRaises(GenerationBlocked):
                load_request(p)

    def test_command_flags_are_independent_from_hospital(self):
        for formats, fhir, csv in [
            (["FHIR_R4"], "true", "false"),
            (["CSV"], "false", "true"),
            (["FHIR_R4", "CSV"], "true", "true"),
        ]:
            with self.subTest(formats=formats):
                req = normalize(request(output_formats=formats))
                args = build_command(req, Path("/synthea.jar"), Path("/data/new"))
                self.assertIn("--exporter.fhir.export=" + fhir, args)
                self.assertIn("--exporter.csv.export=" + csv, args)
                self.assertEqual(args[args.index("-p") + 1], "2")
                self.assertEqual(args[-2:], ["Georgia", "Atlanta"])
                self.assertEqual(args[args.index("-o") + 1], "false")
                self.assertNotIn("hospital-atlanta", " ".join(args))


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.jar = self.root / "synthea.jar"
        self.jar.write_bytes(b"synthea-jar-placeholder")

    def run_once(self, config=None, runner=None):
        return generate(self.root, config or request(), self.jar, runner or StubSynthea())

    def test_fhir_generate_replay_no_regenerate(self):
        runner = StubSynthea()
        result = self.run_once(runner=runner)
        self.assertEqual(result["status"], "SOURCE_GENERATED_VALIDATED")
        self.assertEqual(result["metrics"]["fhir_patients"], 1)
        self.assertEqual(result["metrics"]["fhir_encounters"], 1)
        self.assertEqual(runner.calls, 1)
        second = self.run_once(runner=runner)
        self.assertEqual(result, second)
        self.assertEqual(runner.calls, 1)
        self.assertEqual(len(result["files"]), 1)

    def test_csv_and_combined_generation(self):
        for selected in (["CSV"], ["CSV", "FHIR_R4"]):
            with self.subTest(formats=selected):
                req = request(request_id="req-gen-" + "-".join(selected).lower().replace("_", "-"),
                              output_formats=selected)
                result = self.run_once(req)
                self.assertEqual(result["metrics"]["csv_patient_rows"], 1)
                self.assertEqual(result["metrics"]["csv_encounter_rows"], 1)
                self.assertEqual(result["metrics"]["fhir_patients"],
                                 1 if "FHIR_R4" in selected else 0)

    def test_same_request_changed_params_blocked(self):
        self.run_once()
        with self.assertRaisesRegex(GenerationBlocked, "IMMUTABLE_RECORD_CONFLICT"):
            self.run_once(request(seed=9))
        with self.assertRaisesRegex(GenerationBlocked, "IMMUTABLE_RECORD_CONFLICT"):
            self.run_once(request(output_formats=["CSV"]))

    def test_corrupt_output_blocks_replay(self):
        self.run_once()
        doc = self.root / "requests/hospital-a-0001/payload/fhir/patient1.json"
        doc.write_text(doc.read_text() + " ")
        with self.assertRaisesRegex(GenerationBlocked, "IMMUTABLE_RECORD_CONFLICT"):
            self.run_once()

    def test_missing_or_wrong_patient_reference_is_rejected(self):
        with self.assertRaisesRegex(GenerationBlocked, "FHIR_ENCOUNTER_PATIENT_REFERENCE"):
            self.run_once(runner=StubSynthea(bad_reference=True))
        self.assertFalse((self.root / "requests/hospital-a-0001/generation-manifest.json").exists())

    def test_invalid_fhir_json_fails_closed(self):
        with self.assertRaisesRegex(GenerationBlocked, "INVALID_FHIR_JSON"):
            self.run_once(runner=StubSynthea(invalid_fhir=True))
        self.assertFalse((self.root / "requests/hospital-a-0001/generation-manifest.json").exists())

    def test_failed_synthea_does_not_publish_manifest(self):
        with self.assertRaisesRegex(GenerationBlocked, "SYNTHEA_EXECUTION_FAILED"):
            self.run_once(runner=StubSynthea(code=17))
        self.assertFalse((self.root / "requests/hospital-a-0001/generation-manifest.json").exists())

    def test_failure_retry_same_parameters_is_safe(self):
        with self.assertRaises(GenerationBlocked):
            self.run_once(runner=StubSynthea(code=17))
        result = self.run_once()
        self.assertEqual(result["status"], "SOURCE_GENERATED_VALIDATED")

    def test_orphan_payload_is_blocked(self):
        folder = self.root / "requests/hospital-a-0001"
        folder.mkdir(parents=True)
        (folder / "payload").mkdir()
        with self.assertRaisesRegex(GenerationBlocked, "ORPHAN_PAYLOAD"):
            self.run_once()

    def test_concurrent_same_request_executes_synthea_once(self):
        class SlowStub(StubSynthea):
            def __call__(self, argv, **kwargs):
                time.sleep(0.05)
                return super().__call__(argv, **kwargs)

        runner = SlowStub()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.run_once, request(), runner) for _ in range(2)]
            results = [f.result() for f in futures]
        self.assertEqual(runner.calls, 1)
        self.assertEqual(results[0], results[1])

    def test_csv_unknown_patient_reference_is_rejected(self):
        req = normalize(request(output_formats=["CSV"]))
        fixture = self.root / "untrusted"
        emit_fixture(build_command(req, self.jar, fixture))
        (fixture / "csv/encounters.csv").write_text(
            "Id,PATIENT\nenc1,unknown\n", encoding="utf-8")
        with self.assertRaisesRegex(GenerationBlocked, "INVALID_CSV_ENCOUNTER_IDENTITIES"):
            validate_payload(fixture, req)

    def test_separate_hospital_requests_do_not_share_state(self):
        atl = self.run_once(request(request_id="atlanta-00001", city="Atlanta"))
        jc = self.run_once(request(request_id="johnscreek-00001",
                                   city="Johns Creek", seed=67890))
        self.assertNotEqual(atl["request_sha256"], jc["request_sha256"])
        self.assertEqual(len(list((self.root / "requests").iterdir())), 2)

    def test_invalid_fhir_file_symlink_is_blocked(self):
        req = normalize(request())
        folder = self.root / "fixture/fhir"
        folder.mkdir(parents=True)
        (folder / "patient.json").symlink_to(self.jar)
        with self.assertRaisesRegex(GenerationBlocked, "UNSAFE_OUTPUT_FILE"):
            validate_payload(folder.parent, req)


if __name__ == "__main__":
    unittest.main()

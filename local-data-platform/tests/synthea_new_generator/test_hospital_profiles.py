"""Offline hospital profiles: each is a caller configuration, not generator code."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from apps.clinical_producers.hospital_profiles import (
    build_request, load_profile, validate_profile,
)
from apps.synthea.synthea_new_generator.request import (
    GenerationBlocked, fingerprint, normalize,
)

PROFILES = ROOT / "config/synthea-new-generator"


class HospitalProfilesTests(unittest.TestCase):
    def test_two_profiles_produce_independent_fhir_source_requests(self):
        atl = load_profile(PROFILES / "atlanta-fhir.json")
        jc = load_profile(PROFILES / "johns-creek-hl7.json")
        self.assertEqual(atl["delivery"]["target_format"], "FHIR_R4")
        self.assertEqual(jc["delivery"]["target_format"], "HL7_V2")
        self.assertEqual(jc["delivery"]["transformer"], "OIE")
        ra = build_request(atl, "atlanta-gen-0001")
        rb = build_request(jc, "johns-creek-gen-0001")
        self.assertEqual(ra["output_formats"], ["FHIR_R4"])
        self.assertEqual(rb["output_formats"], ["FHIR_R4"])
        self.assertEqual(ra["city"], "Atlanta")
        self.assertEqual(rb["city"], "Johns Creek")
        self.assertNotEqual(fingerprint(normalize(ra)), fingerprint(normalize(rb)))
        self.assertNotIn("hospital_id", ra)
        self.assertNotIn("feed_id", rb)

    def test_generation_overrides_without_mutating_profile(self):
        profile = load_profile(PROFILES / "atlanta-fhir.json")
        snapshot = copy.deepcopy(profile)
        req = build_request(profile, "atlanta-gen-0002",
                            population=10, seed=98765, reference_date="20260501")
        self.assertEqual(req["population"], 10)
        self.assertEqual(req["seed"], 98765)
        self.assertEqual(req["reference_date"], "20260501")
        self.assertEqual(profile, snapshot)

    def test_new_hospital_does_not_require_generator_code_change(self):
        profile = copy.deepcopy(load_profile(PROFILES / "atlanta-fhir.json"))
        profile["hospital_id"] = "demo-hospital-d"
        profile["feed_id"] = "demo-hospital-d-fhir"
        profile["location"] = {"state": "New York", "city": "New York"}
        validate_profile(profile)
        generated = build_request(profile, "hospital-d-gen-0001")
        self.assertEqual(generated["state"], "New York")

    def test_invalid_profile_or_transformer_fails(self):
        baseline = load_profile(PROFILES / "johns-creek-hl7.json")
        overrides = [
            ("delivery", {"source_format":"HL7_V2", "target_format":"HL7_V2",
                          "transformer":"OIE"}),
            ("delivery", {"source_format":"FHIR_R4", "target_format":"HL7_V2",
                          "transformer":"DIRECT"}),
            ("location", {"state":"Neverland","city":"Unknown"}),
            ("generation_defaults", {"population":0,"seed":1,
                                     "reference_date":"20261024"}),
        ]
        for key, val in overrides:
            with self.subTest(key=key,val=val):
                invalid = copy.deepcopy(baseline)
                invalid[key] = val
                with self.assertRaises(GenerationBlocked):
                    validate_profile(invalid)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "profile.json"
            file.write_text('{"schema_version":"v1","schema_version":"v2"}')
            with self.assertRaises(GenerationBlocked):
                load_profile(file)


if __name__ == "__main__":
    unittest.main()

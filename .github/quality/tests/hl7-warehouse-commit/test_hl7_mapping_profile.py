"""Offline contract for the one reviewed HL7 v2 -> OMOP Standard Concept profile.

No source-code Mapper, Gold writer, fallback to concept 0, or blanket
G5/step approval. Warehouse must still independently SELECT every concept
before any Candidate publication.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "shared-data-engine/src"))
from healthcare_data_engine.mapping.omop.candidates import load_omop_mapping_profile

PROFILE = (REPO / "azure-fabric/warehouse/omop-foundation/mapping-profiles/"
           "johns-creek-hl7-v2-adt-a01-a03-v2.json")
NAMESPACE = ("johns-creek-hl7:johns-creek-hospital-b:"
             "johns-creek-hospital-b-hl7-v2")
EXPECTED = {
    "gender_concepts": {"F": 8532, "M": 8507},
    "race_concepts": {"2028-9": 8515, "2054-5": 8516, "2106-3": 8527},
    "ethnicity_concepts": {"2135-2": 38003563, "2186-5": 38003564},
    "visit_class_concepts": {"inpatient": 9201},
}


class ReviewedHL7MappingContract(unittest.TestCase):
    def load(self):
        raw = PROFILE.read_bytes()
        return load_omop_mapping_profile(
            raw, hashlib.sha256(raw).hexdigest(), NAMESPACE)

    def test_source_namespace_and_exact_standard_crosswalk(self):
        profile = self.load()
        self.assertEqual(profile["source_system"], NAMESPACE)
        self.assertEqual(profile["mapping_version"], "johns-creek-hl7-omop-cdm54-v2")
        for category, mapping in EXPECTED.items():
            self.assertEqual(profile[category], mapping)
        self.assertEqual(profile["visit_type_concept_id"], 32827)
        self.assertNotIn(0, [x for mapping in EXPECTED.values()
                             for x in mapping.values()])

    def test_crosswalk_is_data_not_another_mapper(self):
        obj = json.loads(PROFILE.read_bytes())
        self.assertEqual(set(obj), {
            "mapping_name", "mapping_version", "source_system",
            "gender_concepts", "race_concepts", "ethnicity_concepts",
            "visit_class_concepts", "visit_type_concept_id"})
        self.assertEqual(obj["visit_class_concepts"], {"inpatient": 9201})
        source = (
            REPO / "local-data-platform/spark/apps/hl7/parse_oie_v2.py"
        ).read_text()
        self.assertIn('"encounter_class": "inpatient"', source)
        self.assertIn('if gender not in {"M", "F"}:', source)

    def test_fails_closed_for_foreign_source(self):
        raw = PROFILE.read_bytes()
        with self.assertRaisesRegex(
                ValueError, "OMOP_MAPPING_PROFILE_SOURCE_NAMESPACE_MISMATCH"):
            load_omop_mapping_profile(
                raw, hashlib.sha256(raw).hexdigest(), "synthea-fhir:foreign:feed")

    def test_fails_closed_for_tamper_or_unpinned_profile(self):
        raw = PROFILE.read_bytes()
        old = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, "OMOP_MAPPING_PROFILE_SHA_CONFLICT"):
            load_omop_mapping_profile(raw + b" ", old, NAMESPACE)
        with self.assertRaisesRegex(ValueError, "OMOP_MAPPING_PROFILE_PIN_MISSING"):
            load_omop_mapping_profile(raw, "", NAMESPACE)


if __name__ == "__main__":
    unittest.main()

"""P1 pure preflight fixtures. All IDs, codes and releases are synthetic."""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "shared-data-engine/src"))
sys.path.insert(0, str(ROOT / "azure-fabric/warehouse/omop-foundation/writer"))
from concept_profile import ConceptProfileHold, inspect_mapping_profile


class ConceptProfileGateTests(unittest.TestCase):
    def setUp(self):
        self.source = "synthetic:hospital-A:fhir-r4"
        self.profile = {
            "mapping_name": "SYNTHETIC_TEST_ONLY_NOT_APPROVED",
            "mapping_version": "test-v1",
            "source_system": self.source,
            "gender_concepts": {"g-test": 10001},
            "race_concepts": {"r-test": 10002},
            "ethnicity_concepts": {"e-test": 10003},
            "visit_class_concepts": {"v-test": 10004},
            "visit_type_concept_id": 10005,
        }
        self.observed = {
            "gender_code": {"g-test": 2},
            "race_code": {"r-test": 2},
            "ethnicity_code": {"e-test": 2},
            "encounter_class": {"v-test": 3},
        }
        domain = ("Gender", "Race", "Ethnicity", "Visit", "Type Concept")
        self.rows = [
            dict(concept_id=10001 + i, domain_id=d, standard_concept="S",
                 invalid_reason=None, valid_start_date="2020-01-01",
                 valid_end_date="2099-12-31")
            for i, d in enumerate(domain)
        ]

    def check(self, **changes):
        raw = json.dumps(self.profile, sort_keys=True, separators=(",", ":")).encode()
        args = dict(
            mapping_profile_bytes=raw,
            mapping_profile_sha256=hashlib.sha256(raw).hexdigest(),
            source_system=self.source,
            observed_code_counts=self.observed,
            vocabulary_rows=self.rows,
            vocabulary_release_id="synthetic-release-not-a-real-approval",
            vocabulary_manifest_sha256="a" * 64,
            expected_vocabulary_manifest_sha256="a" * 64,
            vocabulary_effective_date=date(2026, 11, 4),
        )
        args.update(changes)
        return inspect_mapping_profile(**args)

    def hold(self, diagnostic, **changes):
        with self.assertRaisesRegex(ConceptProfileHold, diagnostic):
            self.check(**changes)

    def test_only_supplied_evidence_preflight_not_approval(self):
        x = self.check()
        self.assertEqual(x.concept_count, 5)
        self.assertEqual(x.vocabulary_manifest_sha256, "a" * 64)
        self.assertEqual(x.status, "P1_CONCEPT_PREFLIGHT_ONLY_NOT_CLINICALLY_APPROVED")
        self.assertEqual(dict(x.observed_counts)["encounter_class"], 3)

    def test_missing_real_release_manifest_or_bad_sha_holds(self):
        self.hold("P1_VOCABULARY_MANIFEST_NOT_PINNED",
                  expected_vocabulary_manifest_sha256="b" * 64)
        self.hold("P1_VOCABULARY_MANIFEST_NOT_PINNED",
                  vocabulary_manifest_sha256="not-an-actual-sha")
        self.hold("P1_VOCABULARY_RELEASE_NOT_PINNED", vocabulary_release_id="")
        self.hold("G5_MAPPING_PROFILE_SHA_CONFLICT", mapping_profile_sha256="0" * 64)

    def test_profile_source_namespace_mismatch_holds(self):
        self.hold("G5_MAPPING_PROFILE_SOURCE_NAMESPACE_MISMATCH",
                  source_system="synthetic:hospital-B:fhir-r4")

    def test_source_unknown_missing_or_bad_frequency_holds(self):
        bad = copy.deepcopy(self.observed)
        bad["encounter_class"]["UNREVIEWED"] = 1
        self.hold("P1_UNMAPPED_SOURCE_CODE:encounter_class", observed_code_counts=bad)
        bad = copy.deepcopy(self.observed)
        bad.pop("race_code")
        self.hold("P1_SOURCE_CODE_INVENTORY_INCOMPLETE", observed_code_counts=bad)
        bad = copy.deepcopy(self.observed)
        bad["gender_code"]["g-test"] = True
        self.hold("P1_SOURCE_CODE_COUNT_INVALID", observed_code_counts=bad)
        bad = copy.deepcopy(self.observed)
        bad["gender_code"] = {}
        self.hold("P1_SOURCE_CODE_INVENTORY_EMPTY", observed_code_counts=bad)

    def test_silent_truncation_or_collation_collision_holds(self):
        bad = copy.deepcopy(self.observed)
        bad["gender_code"] = {"g" * 51: 1}
        self.hold("P1_SOURCE_CODE_INVALID_OR_TRUNCATED", observed_code_counts=bad)
        bad = copy.deepcopy(self.observed)
        bad["gender_code"] = {"g-test": 1, "G-TEST": 1}
        self.hold("P1_SOURCE_CODE_COLLATION_COLLISION", observed_code_counts=bad)

    def test_duplicate_missing_or_invented_concepts_hold(self):
        self.hold("P1_DUPLICATE_OR_INVALID_CONCEPT_ID",
                  vocabulary_rows=self.rows + [self.rows[0]])
        self.hold("P1_CONCEPT_SNAPSHOT_MISSING_OR_EXTRANEOUS",
                  vocabulary_rows=self.rows[:-1])
        self.hold("P1_CONCEPT_SNAPSHOT_MISSING_OR_EXTRANEOUS",
                  vocabulary_rows=self.rows + [dict(self.rows[0], concept_id=99999)])

    def test_wrong_domain_or_nonstandard_hold(self):
        bad = copy.deepcopy(self.rows)
        bad[3]["domain_id"] = "Condition"
        self.hold("P1_CONCEPT_DOMAIN_MISMATCH", vocabulary_rows=bad)
        bad = copy.deepcopy(self.rows)
        bad[0]["standard_concept"] = "C"
        self.hold("P1_CONCEPT_NOT_VALID_STANDARD", vocabulary_rows=bad)
        bad = copy.deepcopy(self.rows)
        bad[1]["invalid_reason"] = "D"
        self.hold("P1_CONCEPT_NOT_VALID_STANDARD", vocabulary_rows=bad)

    def test_expired_future_or_invalid_dates_hold(self):
        bad = copy.deepcopy(self.rows)
        bad[2]["valid_end_date"] = "2020-12-31"
        self.hold("P1_CONCEPT_NOT_VALID_AT_RELEASE_DATE", vocabulary_rows=bad)
        bad = copy.deepcopy(self.rows)
        bad[3]["valid_start_date"] = "2027-01-01"
        self.hold("P1_CONCEPT_NOT_VALID_AT_RELEASE_DATE", vocabulary_rows=bad)
        bad = copy.deepcopy(self.rows)
        bad[0]["valid_start_date"] = "2026-99-99"
        self.hold("P1_CONCEPT_DATE_INVALID", vocabulary_rows=bad)

    def test_reproducible_unchanged_preflight_and_source_counts(self):
        self.assertEqual(self.check(), self.check())
        bad = copy.deepcopy(self.observed)
        bad["encounter_class"]["v-test"] = 5918
        self.assertEqual(dict(self.check(observed_code_counts=bad).observed_counts)[
            "encounter_class"], 5918)
        # A caller must still compare these counts with the independently
        # accepted G4 Patient/Encounter physical Delta snapshots.


if __name__ == "__main__":
    unittest.main()

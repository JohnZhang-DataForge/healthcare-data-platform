"""Synthetic-only target/field Concept profile preflight and negative cases."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date
import hashlib
import json
import unittest

from healthcare_data_engine.mapping.omop.target_concepts import (
    TargetConceptHold, inspect_target_concepts, load_target_concept_profile,
)
from healthcare_data_engine.mapping.omop.registry import (
    DEFAULT_OMOP_REGISTRY, EntityDefinition, EntityRegistry, OmopTarget,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
SOURCE = "synthetic:hospital-a:fhir"
GENDER = ("cdm.person", "gender_concept_id")
RACE = ("cdm.person", "race_concept_id")
VISIT = ("cdm.visit_occurrence", "visit_concept_id")


def vocab(concept_id, domain, *, standard="S", invalid=None, start="2020-01-01",
          end="2099-12-31"):
    return dict(concept_id=concept_id, domain_id=domain,
                standard_concept=standard, invalid_reason=invalid,
                valid_start_date=start, valid_end_date=end)


def profile_dict():
    return {
        "schema_version": "target-concept-v1",
        "source_system": SOURCE,
        "mapping_version": "test-only-v1",
        "vocabulary_manifest_sha256": A,
        "clinical_review_sha256": B,
        "license_review_sha256": C,
        "rules": [
            dict(target_table=GENDER[0], target_field=GENDER[1],
                 source_code="female", concept_id=1001, domain_id="Gender"),
            dict(target_table=RACE[0], target_field=RACE[1],
                 source_code="2054-5", concept_id=1002, domain_id="Race"),
            dict(target_table=VISIT[0], target_field=VISIT[1],
                 source_code="ambulatory", concept_id=1003, domain_id="Visit"),
        ],
    }


def encode(profile):
    raw = json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()
    return raw, hashlib.sha256(raw).hexdigest()


def fixture():
    raw, digest = encode(profile_dict())
    return dict(
        profile=load_target_concept_profile(raw, digest, SOURCE),
        source_system=SOURCE,
        observed={GENDER: {"female": 3}, RACE: {"2054-5": 3},
                  VISIT: {"ambulatory": 5}},
        vocabulary_rows=[vocab(1001, "Gender"), vocab(1002, "Race"),
                         vocab(1003, "Visit")],
        vocabulary_manifest_sha256=A,
        effective_date=date(2026, 11, 5),
    )


class TargetConceptPreflightTests(unittest.TestCase):
    def run_preflight(self, **overrides):
        args = fixture()
        args.update(overrides)
        return inspect_target_concepts(**args)

    def test_good_fixture_remains_preflight_not_clinical_approval(self):
        result = self.run_preflight()
        self.assertEqual(result.status,
                         "TARGET_CONCEPT_PREFLIGHT_ONLY_NOT_CLINICALLY_APPROVED")
        self.assertEqual(result.concept_count, 3)
        self.assertEqual(dict(((a, b), c) for a, b, c in
                              result.observed_counts)[VISIT], 5)

    def test_wrong_domain_race_loinc_measurement_hold(self):
        bad = fixture()["vocabulary_rows"]
        bad[1]["domain_id"] = "Measurement"
        with self.assertRaisesRegex(TargetConceptHold, "WRONG_DOMAIN"):
            self.run_preflight(vocabulary_rows=bad)

    def test_unreviewed_domain_override_for_existing_person_blocked(self):
        wrong = profile_dict()
        wrong["rules"][1]["domain_id"] = "Measurement"
        raw, sha = encode(wrong)
        profile = load_target_concept_profile(raw, sha, SOURCE)
        with self.assertRaisesRegex(TargetConceptHold, "DOMAIN_OR_TARGET_MISMATCH"):
            self.run_preflight(profile=profile)
        with self.assertRaisesRegex(TargetConceptHold, "DOMAIN_OVERRIDE_FORBIDDEN"):
            self.run_preflight(reviewed_field_domains={RACE: "Measurement"})

    def test_source_lexical_unknown_or_case_drift_not_auto_mapped(self):
        source = fixture()["observed"]
        source[RACE] = {"unknown": 3}
        with self.assertRaisesRegex(TargetConceptHold, "SOURCE_UNMAPPED"):
            self.run_preflight(observed=source)
        source[RACE] = {"2054-5": 1, "2054-5".upper(): 2}
        # Numeric LOINC code equals its own uppercase; use gender instead.
        source[RACE] = {"2054-5": 3}
        source[GENDER] = {"female": 2, "FEMALE": 1}
        with self.assertRaisesRegex(TargetConceptHold, "INVENTORY_COLLATION_COLLISION"):
            self.run_preflight(observed=source)

    def test_invalid_source_code_length_or_count(self):
        source = fixture()["observed"]
        source[RACE] = {"x" * 51: 1}
        with self.assertRaisesRegex(TargetConceptHold, "SOURCE_INVALID_OR_TRUNCATED"):
            self.run_preflight(observed=source)
        source[RACE] = {"2054-5": True}
        with self.assertRaisesRegex(TargetConceptHold, "COUNT_INVALID"):
            self.run_preflight(observed=source)

    def test_missing_target_field_inventory_or_empty_hold(self):
        observed = fixture()["observed"]
        observed.pop(RACE)
        with self.assertRaisesRegex(TargetConceptHold, "INVENTORY_INCOMPLETE"):
            self.run_preflight(observed=observed)
        observed = fixture()["observed"]
        observed[RACE] = {}
        with self.assertRaisesRegex(TargetConceptHold, "INVENTORY_EMPTY"):
            self.run_preflight(observed=observed)

    def test_nonstandard_expired_future_invalid_concepts(self):
        for update, reason in (
            ({"standard_concept": "C"}, "NONSTANDARD_OR_INVALID"),
            ({"invalid_reason": "D"}, "NONSTANDARD_OR_INVALID"),
            ({"valid_end_date": "2020-12-31"}, "OUTSIDE_VALID_DATE"),
            ({"valid_start_date": "2027-01-01"}, "OUTSIDE_VALID_DATE"),
            ({"valid_start_date": "2027-99-99"}, "DATE_INVALID"),
        ):
            with self.subTest(update=update):
                rows = fixture()["vocabulary_rows"]
                rows[0].update(update)
                with self.assertRaisesRegex(TargetConceptHold, reason):
                    self.run_preflight(vocabulary_rows=rows)

    def test_missing_or_duplicate_vocabulary_rows(self):
        rows = fixture()["vocabulary_rows"]
        with self.assertRaisesRegex(TargetConceptHold, "SNAPSHOT_MISSING_OR_EXTRANEOUS"):
            self.run_preflight(vocabulary_rows=rows[:-1])
        with self.assertRaisesRegex(TargetConceptHold, "DUPLICATE_OR_INVALID_ID"):
            self.run_preflight(vocabulary_rows=rows + [dict(rows[0])])

    def test_wrong_vocabulary_release_sha_hold(self):
        with self.assertRaisesRegex(TargetConceptHold, "VOCABULARY_RELEASE_MISMATCH"):
            self.run_preflight(vocabulary_manifest_sha256=C)
        with self.assertRaisesRegex(TargetConceptHold, "SHA_NOT_PINNED"):
            self.run_preflight(vocabulary_manifest_sha256="bad")

    def test_byte_integrity_profile_sha_source_and_schema(self):
        raw, sha = encode(profile_dict())
        with self.assertRaisesRegex(TargetConceptHold, "PROFILE_SHA_CONFLICT"):
            load_target_concept_profile(raw, A, SOURCE)
        with self.assertRaisesRegex(TargetConceptHold, "SOURCE_OR_VERSION_MISMATCH"):
            load_target_concept_profile(raw, sha, "synthetic:hospital-b:fhir")
        other = profile_dict()
        other["unknown"] = 1
        data, digest = encode(other)
        with self.assertRaisesRegex(TargetConceptHold, "PROFILE_SCHEMA_INVALID"):
            load_target_concept_profile(data, digest, SOURCE)

    def test_missing_review_or_license_evidence_sha_hold_not_guessed(self):
        for field in ("clinical_review_sha256", "license_review_sha256"):
            value = profile_dict()
            value[field] = ""
            raw, digest = encode(value)
            with self.subTest(field=field):
                with self.assertRaisesRegex(TargetConceptHold, "SHA_NOT_PINNED"):
                    load_target_concept_profile(raw, digest, SOURCE)

    def test_profile_duplicate_json_keys_and_semantic_source_collision(self):
        raw = (b'{"schema_version":"target-concept-v1",'
               b'"schema_version":"target-concept-v1"}')
        digest = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(TargetConceptHold, "DUPLICATE_JSON_KEY"):
            load_target_concept_profile(raw, digest, SOURCE)
        data = profile_dict()
        data["rules"].append({
            **data["rules"][0], "source_code": "FEMALE", "concept_id": 1004,
        })
        raw, digest = encode(data)
        with self.assertRaisesRegex(TargetConceptHold, "SOURCE_COLLATION_COLLISION"):
            load_target_concept_profile(raw, digest, SOURCE)

    def test_future_condition_target_requires_explicit_reviewed_domain(self):
        p, v = DEFAULT_OMOP_REGISTRY.definitions
        extra = EntityDefinition(
            "condition_occurrence", "1", "condition", A, "condition_mapper",
            (OmopTarget("cdm.condition_occurrence", "condition_occurrence_id"),),
            dependencies=("person", "visit_occurrence"),
            publication_group="clinical_facts")
        registry = EntityRegistry((p, v, extra))
        data = profile_dict()
        data["rules"].append(dict(
            target_table="cdm.condition_occurrence",
            target_field="condition_concept_id",
            source_code="diagnosis-code", concept_id=1004, domain_id="Condition"))
        raw, sha = encode(data)
        profile = load_target_concept_profile(raw, sha, SOURCE)
        args = fixture()
        args.update(profile=profile, registry=registry)
        args["observed"][("cdm.condition_occurrence", "condition_concept_id")] = {
            "diagnosis-code": 1,
        }
        args["vocabulary_rows"].append(vocab(1004, "Condition"))
        with self.assertRaisesRegex(TargetConceptHold, "DOMAIN_OR_TARGET_MISMATCH"):
            inspect_target_concepts(**args)
        accepted = inspect_target_concepts(
            **args, reviewed_field_domains={
                ("cdm.condition_occurrence", "condition_concept_id"): "Condition"})
        self.assertEqual(accepted.concept_count, 4)
        self.assertIn("NOT_CLINICALLY_APPROVED", accepted.status)

    def test_profile_is_deterministic_over_permuted_observations(self):
        first = self.run_preflight()
        items = list(reversed(list(fixture()["observed"].items())))
        second = self.run_preflight(observed=dict(items))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

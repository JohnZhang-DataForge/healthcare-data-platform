"""Offline LocalDP -> G5/FHIR profile parity using authoritative legacy files.

Synthetic source inventories only. The resulting profile is a DRAFT,
NOT clinical review, vocabulary license, Candidate Delta or Gold approval.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import unittest

from healthcare_data_engine.mapping.omop.local_profile import (
    FHIR_R4_LOCALDP_ALIASES, LocalProfileDraft, LocalProfileHold,
    build_localdp_mapping_draft, build_mapping_coverage_review,
)
from healthcare_data_engine.adapters.fhir_r4.omop_code_aliases import (
    FHIR_R4_LOCALDP_ALIASES as ADAPTER_ALIASES, FHIR_R4_RACE_REVIEW_HINTS,
)
from dataclasses import replace
from healthcare_data_engine.mapping.omop.candidates import load_omop_mapping_profile

ROOT = Path(__file__).resolve().parents[5]
LEGACY = runpy.run_path(str(ROOT / "local-data-platform/spark/common/omop.py"))
VISIT = json.loads((ROOT / "local-data-platform/spark/contracts/omop/visit-class-v1.json").read_text())
SOURCE = "synthea-fhir:atlanta-hospital-a:atlanta-hospital-a-fhir-r4"
OBSERVED = {
    "gender_code": {"female": 54, "male": 46},
    "race_code": {
        "2054-5": 53, "2106-3": 38, "2028-9": 5,
        "UNK": 2, "1002-5": 1, "2076-8": 1,
    },
    "ethnicity_code": {"2186-5": 92, "2135-2": 8},
    "encounter_class": {
        "ambulatory": 5684, "emergency": 164, "inpatient": 55,
        "virtual": 11, "home": 4,
    },
}


def make(**overrides):
    options = dict(
        source_system=SOURCE,
        mapping_version="localdp-synthea-fhir-draft-v1",
        gender_concepts=LEGACY["GENDER_CONCEPTS"],
        race_concepts=LEGACY["RACE_CONCEPTS"],
        ethnicity_concepts=LEGACY["ETHNICITY_CONCEPTS"],
        visit_class_contract=VISIT,
        aliases=FHIR_R4_LOCALDP_ALIASES,
        observed_codes=OBSERVED,
    )
    options.update(overrides)
    return build_localdp_mapping_draft(**options)


class LocalDPG5ProfileTests(unittest.TestCase):
    def test_existing_g5_mapper_accepts_one_exact_profile_schema(self):
        draft = make()
        self.assertEqual(hashlib.sha256(draft.profile_bytes).hexdigest(),
                         draft.profile_sha256)
        profile = load_omop_mapping_profile(
            draft.profile_bytes, draft.profile_sha256, SOURCE)
        self.assertEqual(set(profile), {
            "mapping_name", "mapping_version", "source_system",
            "gender_concepts", "race_concepts", "ethnicity_concepts",
            "visit_class_concepts", "visit_type_concept_id"})
        self.assertEqual(profile["gender_concepts"]["female"], LEGACY["GENDER_CONCEPTS"]["F"])
        self.assertEqual(profile["gender_concepts"]["male"], LEGACY["GENDER_CONCEPTS"]["M"])
        self.assertEqual(profile["race_concepts"]["2054-5"], LEGACY["RACE_CONCEPTS"]["black"])
        self.assertEqual(profile["race_concepts"]["2106-3"], LEGACY["RACE_CONCEPTS"]["white"])
        self.assertEqual(profile["race_concepts"]["2028-9"], LEGACY["RACE_CONCEPTS"]["asian"])
        self.assertEqual(profile["race_concepts"]["2076-8"], LEGACY["RACE_CONCEPTS"]["hawaiian"])
        self.assertEqual(profile["ethnicity_concepts"]["2135-2"],
                         LEGACY["ETHNICITY_CONCEPTS"]["hispanic"])
        self.assertEqual(profile["ethnicity_concepts"]["2186-5"],
                         LEGACY["ETHNICITY_CONCEPTS"]["nonhispanic"])
        for klass, rule in VISIT["class_to_visit_concept"].items():
            self.assertEqual(profile["visit_class_concepts"][klass], rule["concept_id"])
        self.assertEqual(profile["visit_type_concept_id"], VISIT["visit_type_concept_id"])
        self.assertEqual(len(profile["visit_class_concepts"]), 10)

    def test_real_inventory_has_two_unresolved_source_codes_and_no_silent_zero(self):
        draft = make()
        self.assertFalse(draft.ready_for_clinical_review)
        self.assertFalse(draft.authorized_for_candidate_write)
        self.assertEqual(draft.unresolved_source_codes,
                         ("race_code:1002-5", "race_code:UNK"))
        profile = json.loads(draft.profile_bytes)
        self.assertNotIn("UNK", profile["race_concepts"])
        self.assertNotIn("1002-5", profile["race_concepts"])
        self.assertNotIn(0, profile["race_concepts"].values())
        self.assertNotIn(0, profile["visit_class_concepts"].values())

    def test_supported_source_subset_still_only_a_draft_not_approval(self):
        safe = deepcopy(OBSERVED)
        safe["race_code"].pop("UNK")
        safe["race_code"].pop("1002-5")
        draft = make(observed_codes=safe)
        self.assertTrue(draft.ready_for_clinical_review)
        self.assertFalse(draft.authorized_for_candidate_write)
        self.assertEqual(draft.unresolved_source_codes, ())

    def test_byte_determinism_under_inventory_reordering(self):
        reordered = {k: dict(reversed(list(values.items())))
                     for k, values in reversed(list(OBSERVED.items()))}
        self.assertEqual(make(observed_codes=reordered).profile_bytes,
                         make().profile_bytes)
        self.assertEqual(make(observed_codes=reordered).profile_sha256,
                         make().profile_sha256)

    def test_legacy_rules_are_not_copied_into_shared_concept_id_constants(self):
        from healthcare_data_engine.mapping.omop import local_profile
        source = Path(local_profile.__file__).read_text()
        self.assertNotIn("9202", source)
        self.assertNotIn("8515", source)
        self.assertNotIn("38003563", source)
        self.assertIn("visit_class_contract", source)

    def test_wrong_legacy_visit_baseline_holds(self):
        contract = dict(VISIT, source_system="another")
        with self.assertRaisesRegex(LocalProfileHold, "VISIT_CONTRACT_NOT_VERIFIED"):
            make(visit_class_contract=contract)

    def test_new_or_unknown_source_class_cannot_be_defaulted(self):
        observed = deepcopy(OBSERVED)
        observed["encounter_class"]["unknown-mode"] = 1
        draft = make(observed_codes=observed)
        self.assertIn("encounter_class:unknown-mode", draft.unresolved_source_codes)

    def test_bad_alias_target_or_implicit_fallback_holds(self):
        aliases = deepcopy(FHIR_R4_LOCALDP_ALIASES)
        aliases["race_code"]["1002-5"] = "american_indian_unreviewed"
        with self.assertRaisesRegex(LocalProfileHold, "UNVERIFIED_ALIAS"):
            make(aliases=aliases)
        aliases = deepcopy(FHIR_R4_LOCALDP_ALIASES)
        aliases["gender_code"]["unknown"] = "UNK"
        with self.assertRaisesRegex(LocalProfileHold, "UNVERIFIED_ALIAS"):
            make(aliases=aliases)

    def test_null_zero_boolean_and_collation_conflicting_ids_rejected(self):
        for cid in (0, None, True):
            with self.subTest(cid=cid):
                gender = dict(LEGACY["GENDER_CONCEPTS"], F=cid)
                with self.assertRaisesRegex(LocalProfileHold, "ENTRY_INVALID"):
                    make(gender_concepts=gender)
        codes = deepcopy(OBSERVED)
        codes["gender_code"]["FEMALE"] = 1
        with self.assertRaisesRegex(LocalProfileHold, "INVENTORY_INVALID"):
            make(observed_codes=codes)

    def test_cross_hospital_and_invalid_alias_field_rejected(self):
        with self.assertRaisesRegex(LocalProfileHold, "NAMESPACE_OR_VERSION"):
            make(source_system="synthea-fhir")
        alias = dict(FHIR_R4_LOCALDP_ALIASES)
        alias["extra_field"] = {}
        with self.assertRaisesRegex(LocalProfileHold, "FIELD_INVENTORY_INCOMPLETE"):
            make(aliases=alias)

    def test_unknown_code_is_source_not_fhir_parsing_corruption(self):
        draft = make()
        self.assertIn("race_code:UNK", draft.unresolved_source_codes)
        self.assertEqual(OBSERVED["gender_code"]["male"] + OBSERVED["gender_code"]["female"], 100)
        self.assertEqual(sum(OBSERVED["encounter_class"].values()), 5918)




SOURCE_BATCH = "2e110eb1971fcfa3ebb4dda6782c49a7608955855a2de45a3d77ada47fea8adb"
MANIFEST = "425a25a6337e86a2df39c1f7993d46fd0555cfed9107dde415521fde755ff2f1"


def coverage(**overrides):
    params = dict(
        draft=make(), observed_codes=OBSERVED,
        source_batch_id=SOURCE_BATCH, manifest_sha256=MANIFEST,
        patient_count=100, encounter_count=5918,
        source_meanings={
            ("race_code", key): meaning
            for key, meaning in FHIR_R4_RACE_REVIEW_HINTS.items()
        },
    )
    params.update(overrides)
    return build_mapping_coverage_review(**params)


class LocalDPMappingCoverageTests(unittest.TestCase):
    def test_fhir_specific_aliases_owned_by_adapter_only(self):
        self.assertIs(ADAPTER_ALIASES, FHIR_R4_LOCALDP_ALIASES)
        self.assertEqual(ADAPTER_ALIASES["gender_code"]["female"], "F")
        from healthcare_data_engine.mapping.omop import local_profile
        code = Path(local_profile.__file__).read_text()
        self.assertNotIn('"2028-9": "asian"', code)
        self.assertNotIn('"2076-8": "hawaiian"', code)
        self.assertNotIn('"1002-5": "american_indian"', code)
        self.assertEqual(FHIR_R4_RACE_REVIEW_HINTS["1002-5"],
                         "AMERICAN_INDIAN_OR_ALASKA_NATIVE")
        self.assertEqual(FHIR_R4_RACE_REVIEW_HINTS["UNK"],
                         "HL7_NULLFLAVOR_UNKNOWN")

    def test_frozen_fhir_source_coverage_counts_and_two_real_gaps(self):
        result = coverage()
        self.assertEqual(result.status, "MAPPING_COVERAGE_REVIEW_ONLY_NO_CLINICAL_APPROVAL")
        self.assertFalse(result.candidate_write_authorized)
        self.assertFalse(result.ready_for_clinical_review)
        self.assertEqual(result.patient_count, 100)
        self.assertEqual(result.encounter_count, 5918)
        self.assertEqual(result.source_batch_id, SOURCE_BATCH)
        self.assertEqual(result.manifest_sha256, MANIFEST)
        self.assertEqual(result.profile_sha256, make().profile_sha256)
        self.assertEqual(len(result.inventory_sha256), 64)
        self.assertEqual(dict(result.unmapped_records_by_field), {
            "gender_code": 0, "race_code": 3,
            "ethnicity_code": 0, "encounter_class": 0})
        self.assertEqual(
            [(x.source_field, x.source_code, x.observed_count, x.source_meaning)
             for x in result.gaps],
            [
                ("race_code", "1002-5", 1, "AMERICAN_INDIAN_OR_ALASKA_NATIVE"),
                ("race_code", "UNK", 2, "HL7_NULLFLAVOR_UNKNOWN"),
            ])
        self.assertTrue(all("REVIEW" in x.disposition for x in result.gaps))

    def test_no_guessing_omop_id_zero_and_unresolved_draft_cannot_publish(self):
        result = coverage()
        self.assertFalse(result.candidate_write_authorized)
        self.assertTrue(all(not hasattr(x, "concept_id") for x in result.gaps))
        self.assertNotIn('"1002-5"', make().profile_bytes.decode())
        self.assertNotIn('"UNK"', make().profile_bytes.decode())

    def test_immutable_digest_and_source_counts_independent_of_order(self):
        reordered = {k: dict(reversed(list(OBSERVED[k].items())))
                     for k in reversed(list(OBSERVED))}
        x, y = coverage(), coverage(observed_codes=reordered)
        self.assertEqual(x.inventory_sha256, y.inventory_sha256)
        self.assertEqual(x.gaps, y.gaps)
        self.assertEqual(x.unmapped_records_by_field, y.unmapped_records_by_field)

    def test_missing_fields_and_incorrect_totals_rejected(self):
        counts = deepcopy(OBSERVED)
        counts.pop("ethnicity_code")
        with self.assertRaisesRegex(LocalProfileHold, "INVENTORY_FIELDS_MISSING"):
            coverage(observed_codes=counts)
        counts = deepcopy(OBSERVED)
        counts["race_code"]["UNK"] = 1
        with self.assertRaisesRegex(LocalProfileHold, "SOURCE_COUNT_DRIFT"):
            coverage(observed_codes=counts)
        with self.assertRaisesRegex(LocalProfileHold, "SOURCE_COUNT_DRIFT"):
            coverage(encounter_count=5917)

    def test_unpinned_manifest_or_batch_rejected(self):
        for change in (
            {"source_batch_id": "untrusted"},
            {"manifest_sha256": "bad-sha"},
            {"patient_count": True},
            {"encounter_count": 0},
        ):
            with self.subTest(change=change):
                with self.assertRaisesRegex(LocalProfileHold, "SOURCE_FENCE_NOT_PINNED"):
                    coverage(**change)

    def test_clinical_review_gaps_must_match_byte_pinned_draft(self):
        draft = make()
        with self.assertRaisesRegex(LocalProfileHold, "PROFILE_INVENTORY_CONFLICT"):
            coverage(draft=replace(draft, unresolved_source_codes=()))
        with self.assertRaisesRegex(LocalProfileHold, "PROFILE_SHA_OR_STATUS_HOLD"):
            coverage(draft=replace(draft, profile_sha256="f" * 64))
        with self.assertRaisesRegex(LocalProfileHold, "PROFILE_SHA_OR_STATUS_HOLD"):
            coverage(draft=replace(draft, status="SIGNED_CLINICAL_APPROVED"))

    def test_observed_only_source_hint_cannot_add_new_codes(self):
        with self.assertRaisesRegex(LocalProfileHold, "SOURCE_MEANING_UNOBSERVED"):
            coverage(source_meanings={("race_code", "MISSING_SOURCE_CODE"): "UNKNOWN"})
        with self.assertRaisesRegex(LocalProfileHold, "SOURCE_MEANING_INVALID"):
            coverage(source_meanings={("race_code", "UNK"): "review=approved"})

    def test_negative_and_casefold_codes_cannot_fake_batch_coverage(self):
        for change in (
            lambda x: x["race_code"].update({"UNK": -1}),
            lambda x: x["gender_code"].update({"FEMALE": 1}),
            lambda x: x["race_code"].update({"": 1}),
        ):
            counts = deepcopy(OBSERVED)
            change(counts)
            with self.assertRaisesRegex(LocalProfileHold, "SOURCE_CODE_INVALID"):
                coverage(observed_codes=counts)

    def test_review_is_portable_across_source_namespace_with_explicit_aliases(self):
        other = "synthea-fhir:atlanta-hospital-b:hospital-b-fhir-r4"
        draft = make(source_system=other)
        result = coverage(draft=draft)
        self.assertEqual(result.source_system, other)
        self.assertFalse(result.candidate_write_authorized)
        self.assertEqual(len(result.gaps), 2)


if __name__ == "__main__":
    unittest.main()

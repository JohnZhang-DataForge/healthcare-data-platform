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



# The official HL7 FHIR-to-OMOP guide (ballot) identifies this familiar Race
# Concept, but it is still only a synthetic F1 row in the offline tests.
# Real current Warehouse SQL evidence and clinical approval are separate.
from datetime import date
from healthcare_data_engine.mapping.omop.race_resolution import (
    CDC_RACE_CODE_SYSTEM, HL7_NULLFLAVOR_CODE_SYSTEM,
    propose_race_resolution,
)

F1_CANDIDATE = {
    "concept_id": 8657,
    "concept_name": "American Indian or Alaska Native",
    "domain_id": "Race",
    "vocabulary_id": "Race",
    "standard_concept": "S",
    "invalid_reason": None,
    "valid_start_date": "2000-01-01",
    "valid_end_date": "2099-12-31",
}


def race_proposal(**overrides):
    args = dict(
        coverage=coverage(),
        draft=make(),
        proposed_f1_concept_row=F1_CANDIDATE,
        f1_release_metadata_sha256="d" * 64,
        observed_race_coding_systems={
            "1002-5": {CDC_RACE_CODE_SYSTEM: 1},
            "UNK": {HL7_NULLFLAVOR_CODE_SYSTEM: 2},
        },
        as_of=date(2026, 11, 7),
    )
    args.update(overrides)
    return propose_race_resolution(**args)


class RaceF1AndMissingValueSourceReviewTests(unittest.TestCase):
    def test_reviewed_standard_target_draft_adds_1002_only_and_never_unk_zero(self):
        result = race_proposal()
        self.assertEqual(result.status,
                         "RACE_MAPPING_DRAFT_ONLY_F1_PHYSICAL_AND_CLINICAL_HOLD")
        self.assertFalse(result.candidate_write_authorized)
        self.assertFalse(result.clinically_approved)
        self.assertEqual(result.original_profile_sha256, make().profile_sha256)
        self.assertEqual(result.source_batch_id, SOURCE_BATCH)
        self.assertEqual(result.manifest_sha256, MANIFEST)
        self.assertEqual(result.source_system, SOURCE)
        self.assertEqual(result.proposed_standard_race_concept_id, 8657)
        self.assertEqual(hashlib.sha256(result.proposed_profile_bytes).hexdigest(),
                         result.proposed_profile_sha256)
        profile = load_omop_mapping_profile(
            result.proposed_profile_bytes, result.proposed_profile_sha256, SOURCE)
        self.assertEqual(profile["race_concepts"]["1002-5"], 8657)
        self.assertNotIn("UNK", profile["race_concepts"])
        self.assertNotIn(0, profile["race_concepts"].values())
        self.assertEqual(result.unresolved_source_codes, ("race_code:UNK",))
        self.assertEqual(result.pending_no_information_source_count, 2)
        self.assertEqual(result.pending_no_information_policy,
                         "UNK_OMOP_CDM54_ZERO_REQUIRES_EXPLICIT_REVIEW")

    def test_source_and_semantic_authority_separated(self):
        self.assertEqual(
            race_proposal().claimed_f1_release_sha256, "d" * 64)
        from healthcare_data_engine.mapping.omop import race_resolution
        source = Path(race_resolution.__file__).read_text()
        # The shared logic must not copy target Concept numbers from HL7 IG.
        self.assertNotIn("8657", source)
        self.assertNotIn("execute_gold", source)
        self.assertNotIn("spark.read", source)
        self.assertFalse(hasattr(race_proposal(), "commit"))

    def test_incorrect_raw_fhir_system_missing_or_counts_hold(self):
        for coding in (
            {},
            {"1002-5": {CDC_RACE_CODE_SYSTEM: 1}},
            {"1002-5": {"http://loinc.org": 1},
             "UNK": {HL7_NULLFLAVOR_CODE_SYSTEM: 2}},
            {"1002-5": {CDC_RACE_CODE_SYSTEM: 1},
             "UNK": {"http://example.org/other": 2}},
            {"1002-5": {CDC_RACE_CODE_SYSTEM: 1},
             "UNK": {HL7_NULLFLAVOR_CODE_SYSTEM: 1}},
            {"1002-5": {CDC_RACE_CODE_SYSTEM: True},
             "UNK": {HL7_NULLFLAVOR_CODE_SYSTEM: 2}},
        ):
            with self.subTest(coding=coding):
                with self.assertRaisesRegex(LocalProfileHold,
                                            "RAW_CODING_SYSTEM"):
                    race_proposal(observed_race_coding_systems=coding)

    def test_wrong_f1_domain_nonstandard_invalid_and_wrong_semantic_hold(self):
        failures = (
            {"concept_name": "Native Hawaiian or Other Pacific Islander"},
            {"domain_id": "Measurement"},
            {"vocabulary_id": "SNOMED"},
            {"standard_concept": None},
            {"standard_concept": "C"},
            {"invalid_reason": "D"},
            {"concept_id": True},
            {"concept_id": 0},
        )
        for field_update in failures:
            with self.subTest(field_update=field_update):
                row = dict(F1_CANDIDATE, **field_update)
                with self.assertRaisesRegex(LocalProfileHold,
                                            "NONSTANDARD_OR_WRONG_SEMANTICS"):
                    race_proposal(proposed_f1_concept_row=row)

    def test_f1_date_window_and_schema_hold(self):
        for row in (
            dict(F1_CANDIDATE, valid_end_date="2020-01-01"),
            dict(F1_CANDIDATE, valid_start_date="2027-01-01"),
            dict(F1_CANDIDATE, valid_end_date="2026-99-99"),
            dict(F1_CANDIDATE, unreviewed_extra="untrusted"),
        ):
            with self.subTest(row=row):
                with self.assertRaises(LocalProfileHold):
                    race_proposal(proposed_f1_concept_row=row)
        with self.assertRaisesRegex(LocalProfileHold, "DATE_INVALID"):
            race_proposal(as_of="2026-11-07-other")

    def test_wrong_batch_manifest_f1_metadata_sha_or_profile_hold(self):
        for change in (
            {"f1_release_metadata_sha256": "fake"},
            {"draft": replace(make(), profile_sha256="a"*64)},
            {"draft": replace(make(), unresolved_source_codes=())},
            {"coverage": replace(coverage(), profile_sha256="f"*64)},
            {"coverage": replace(coverage(), source_batch_id="bad")},
            {"coverage": replace(coverage(), manifest_sha256="wrong")},
        ):
            with self.subTest(change=change):
                with self.assertRaises(LocalProfileHold):
                    race_proposal(**change)

    def test_unknown_additional_or_zero_mapped_gap_will_not_silently_pass(self):
        altered = replace(
            coverage(),
            gaps=tuple(list(coverage().gaps) + [
                replace(coverage().gaps[0],
                        source_code="extra-code", observed_count=1)
            ]))
        with self.assertRaisesRegex(LocalProfileHold, "GAP_SCOPE"):
            race_proposal(coverage=altered)
        orig = json.loads(make().profile_bytes)
        orig["race_concepts"]["UNK"] = 0
        raw = json.dumps(orig, sort_keys=True).encode()
        draft = replace(make(), profile_bytes=raw,
                        profile_sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(LocalProfileHold):
            race_proposal(draft=draft)

    def test_proposed_f1_row_and_unknown_never_masquerade_as_f1_sql_readback(self):
        result = race_proposal()
        self.assertNotEqual(result.proposed_profile_sha256,
                            result.original_profile_sha256)
        self.assertIn("DRAFT_ONLY", result.status)
        self.assertIn("REQUIRES_EXPLICIT_REVIEW",
                      result.pending_no_information_policy)
        self.assertEqual(len(result.claimed_source_coding_sha256), 64)

    def test_proposal_stable_under_coverage_reordering_and_other_hospital(self):
        original = race_proposal()
        reread = race_proposal()
        self.assertEqual(original.proposed_profile_bytes,
                         reread.proposed_profile_bytes)
        self.assertEqual(original.claimed_source_coding_sha256,
                         reread.claimed_source_coding_sha256)
        source_b = "synthea-fhir:atlanta-hospital-b:hospital-b-fhir-r4"
        draft_b = make(source_system=source_b)
        cov_b = coverage(draft=draft_b)
        other = race_proposal(draft=draft_b, coverage=cov_b)
        self.assertEqual(other.source_system, source_b)
        self.assertNotEqual(original.proposed_profile_sha256,
                            other.proposed_profile_sha256)
        self.assertFalse(other.candidate_write_authorized)

if __name__ == "__main__":
    unittest.main()

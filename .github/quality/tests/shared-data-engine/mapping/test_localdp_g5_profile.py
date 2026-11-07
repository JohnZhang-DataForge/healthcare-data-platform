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
    FHIR_R4_LOCALDP_ALIASES, LocalProfileHold, build_localdp_mapping_draft,
)
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


if __name__ == "__main__":
    unittest.main()

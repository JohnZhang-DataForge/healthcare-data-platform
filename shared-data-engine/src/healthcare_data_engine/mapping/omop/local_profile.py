"""Derive a G5 mapping-profile DRAFT from authoritative legacy LocalDP rules.

The LocalDP demographic dictionaries and Visit JSON are supplied *as inputs*,
rather than copied into a second hard-coded Concept table. FHIR-specific
source-code aliases describe translation to existing LocalDP semantic keys.
This is a pure, platform-neutral helper. It grants no clinical approval,
Vocabulary rights, P3 Candidate publication, SQL write or OMOP Gold COMMIT.

Unknown / unreviewed source codes remain unresolved and fail-closed. A draft
must not be mistaken for a signed, approved mapping profile.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping

_FIELDS = ("gender_code", "race_code", "ethnicity_code", "encounter_class")
_SHA_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")

# Backwards-compatible import path, while the FHIR adapter now owns all
# source-specific code semantics. Do not define FHIR/CSV/HL7 codes here.
from healthcare_data_engine.adapters.fhir_r4.omop_code_aliases import (
    FHIR_R4_LOCALDP_ALIASES,
)

class LocalProfileHold(ValueError):
    """Safe contract errors only; never print source patient values."""


@dataclass(frozen=True)
class LocalProfileDraft:
    profile_bytes: bytes
    profile_sha256: str
    unresolved_source_codes: tuple[str, ...]
    status: str = "LOCALDP_RULES_DRAFT_ONLY_NOT_APPROVED"

    @property
    def ready_for_clinical_review(self) -> bool:
        return not self.unresolved_source_codes

    @property
    def authorized_for_candidate_write(self) -> bool:
        return False


def _codes(value: object, *, name: str) -> dict[str, int]:
    if not isinstance(value, Mapping) or not value or len(value) > 128:
        raise LocalProfileHold("LOCALDP_" + name + "_MAPPING_INVALID")
    result = {}
    folded = set()
    for key, concept in value.items():
        if (not isinstance(key, str) or not _SHA_CODE.fullmatch(key)
                or key.casefold() in folded or type(concept) is not int
                or not 1 <= concept <= 2147483647):
            raise LocalProfileHold("LOCALDP_" + name + "_ENTRY_INVALID")
        folded.add(key.casefold())
        result[key] = concept
    return result


def _aliases(value: object, *, name: str, target: Mapping[str, int]) -> dict[str, int]:
    if not isinstance(value, Mapping) or not value or len(value) > 128:
        raise LocalProfileHold("LOCALDP_" + name + "_ALIASES_INVALID")
    translated: dict[str, int] = {}
    folded = set()
    for source, original in value.items():
        if (not isinstance(source, str) or not _SHA_CODE.fullmatch(source)
                or source.casefold() in folded
                or not isinstance(original, str) or original not in target):
            raise LocalProfileHold("LOCALDP_" + name + "_UNVERIFIED_ALIAS")
        folded.add(source.casefold())
        translated[source] = target[original]
    return translated


def build_localdp_mapping_draft(
    *, source_system: str, mapping_version: str,
    gender_concepts: Mapping[str, int], race_concepts: Mapping[str, int],
    ethnicity_concepts: Mapping[str, int],
    visit_class_contract: Mapping[str, object],
    aliases: Mapping[str, Mapping[str, str]],
    observed_codes: Mapping[str, Mapping[str, int]],
) -> LocalProfileDraft:
    """Produce the exact existing Shared G5 Mapper profile schema, byte-pinned.

    Inputs come from the unmodified LocalDP `spark/common/omop.py` and
    `spark/contracts/omop/visit-class-v1.json`; this helper doesn't import
    Local Spark/PG or duplicate its Concept ID definitions. `aliases` are
    source-specific and reviewable (e.g. FHIR R4 vs CSV), not fallback guesses.
    `observed_codes` must be complete batch inventory, not selected samples.
    """
    if (not isinstance(source_system, str)
            or len(source_system.split(":")) != 3
            or not all(_SHA_CODE.fullmatch(part) for part in source_system.split(":"))
            or not isinstance(mapping_version, str)
            or not _SHA_CODE.fullmatch(mapping_version)):
        raise LocalProfileHold("LOCALDP_PROFILE_NAMESPACE_OR_VERSION_INVALID")
    if (not isinstance(visit_class_contract, Mapping)
            or visit_class_contract.get("mapping_name") !=
            "synthea-encounter-class-to-omop-visit-v1"
            or visit_class_contract.get("visit_source_value") != "encounter_class"
            or visit_class_contract.get("source_system") != "synthea"):
        raise LocalProfileHold("LOCALDP_VISIT_CONTRACT_NOT_VERIFIED")
    raw_visit = visit_class_contract.get("class_to_visit_concept")
    if not isinstance(raw_visit, Mapping) or not raw_visit:
        raise LocalProfileHold("LOCALDP_VISIT_CLASS_NOT_VERIFIED")
    classes = {}
    for code, rule in raw_visit.items():
        if not isinstance(rule, Mapping) or set(rule) != {"concept_id", "concept_name"}:
            raise LocalProfileHold("LOCALDP_VISIT_RULE_INVALID")
        classes[code] = rule["concept_id"]
    local = {
        "gender_code": _codes(gender_concepts, name="GENDER"),
        "race_code": _codes(race_concepts, name="RACE"),
        "ethnicity_code": _codes(ethnicity_concepts, name="ETHNICITY"),
        "encounter_class": _codes(classes, name="VISIT"),
    }
    visit_type = visit_class_contract.get("visit_type_concept_id")
    if type(visit_type) is not int or not 1 <= visit_type <= 2147483647:
        raise LocalProfileHold("LOCALDP_VISIT_TYPE_INVALID")
    if (not isinstance(aliases, Mapping) or set(aliases) != set(_FIELDS)
            or not isinstance(observed_codes, Mapping)
            or set(observed_codes) != set(_FIELDS)):
        raise LocalProfileHold("LOCALDP_PROFILE_FIELD_INVENTORY_INCOMPLETE")
    translated = {
        field: _aliases(aliases[field], name=field.upper(), target=local[field])
        for field in _FIELDS
    }
    unresolved = []
    for field in _FIELDS:
        inventory = observed_codes[field]
        if not isinstance(inventory, Mapping) or not inventory:
            raise LocalProfileHold("LOCALDP_" + field.upper() + "_INVENTORY_EMPTY")
        seen = set()
        for code, count in inventory.items():
            if (not isinstance(code, str) or not _SHA_CODE.fullmatch(code)
                    or code.casefold() in seen or type(count) is not int
                    or count <= 0):
                raise LocalProfileHold("LOCALDP_" + field.upper() + "_INVENTORY_INVALID")
            seen.add(code.casefold())
            if code not in translated[field]:
                unresolved.append(field + ":" + code)
    profile = {
        "mapping_name": "localdp-shared-omop-person-visit-draft",
        "mapping_version": mapping_version,
        "source_system": source_system,
        "gender_concepts": translated["gender_code"],
        "race_concepts": translated["race_code"],
        "ethnicity_concepts": translated["ethnicity_code"],
        "visit_class_concepts": translated["encounter_class"],
        "visit_type_concept_id": visit_type,
    }
    raw = json.dumps(profile, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    # Do not return an approval object, only the existing G5 Mapper's
    # structural profile bytes and the explicit unresolved source codes.
    from healthcare_data_engine.mapping.omop.candidates import (
        load_omop_mapping_profile,
    )
    load_omop_mapping_profile(raw, hashlib.sha256(raw).hexdigest(), source_system)
    return LocalProfileDraft(
        raw, hashlib.sha256(raw).hexdigest(),
        tuple(sorted(unresolved)),
    )


@dataclass(frozen=True)
class MappingReviewGap:
    """One observed aggregate source code still lacking an OMOP mapping rule."""
    source_field: str
    source_code: str
    observed_count: int
    source_meaning: str = "UNREVIEWED"
    disposition: str = "REQUIRES_CLINICAL_AND_F1_VOCABULARY_REVIEW"


@dataclass(frozen=True)
class MappingCoverageReview:
    """No row-level PHI and no permission to write a Candidate or Gold row."""
    source_system: str
    source_batch_id: str
    manifest_sha256: str
    profile_sha256: str
    inventory_sha256: str
    patient_count: int
    encounter_count: int
    unmapped_records_by_field: tuple[tuple[str, int], ...]
    gaps: tuple[MappingReviewGap, ...]
    status: str = "MAPPING_COVERAGE_REVIEW_ONLY_NO_CLINICAL_APPROVAL"

    @property
    def ready_for_clinical_review(self) -> bool:
        return len(self.gaps) == 0

    @property
    def candidate_write_authorized(self) -> bool:
        return False


def build_mapping_coverage_review(
    draft: LocalProfileDraft, *,
    observed_codes: Mapping[str, Mapping[str, int]],
    source_batch_id: str, manifest_sha256: str,
    patient_count: int, encounter_count: int,
    source_meanings: Mapping[tuple[str, str], str] | None = None,
) -> MappingCoverageReview:
    """Bound source-code review to an exact source batch, manifest and G5 SHA.

    Input is a **caller-provided** full, aggregate-only canonical Silver
    inventory. This pure function validates field totals and code coverage;
    it CANNOT prove the physical Silver approval, clinical signoff, or an F1
    Vocabulary release. Callers must independently read physical Silver.
    The supplied source_meanings are descriptive review hints, NEVER target IDs.
    """
    from healthcare_data_engine.mapping.omop.candidates import (
        load_omop_mapping_profile,
    )

    if (not isinstance(draft, LocalProfileDraft)
            or draft.status != "LOCALDP_RULES_DRAFT_ONLY_NOT_APPROVED"
            or hashlib.sha256(draft.profile_bytes).hexdigest() != draft.profile_sha256):
        raise LocalProfileHold("LOCALDP_REVIEW_PROFILE_SHA_OR_STATUS_HOLD")
    if (not isinstance(source_batch_id, str)
            or not re.fullmatch(r"[0-9a-f]{64}", source_batch_id)
            or not isinstance(manifest_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", manifest_sha256)
            or type(patient_count) is not int or patient_count <= 0
            or type(encounter_count) is not int or encounter_count <= 0):
        raise LocalProfileHold("LOCALDP_REVIEW_SOURCE_FENCE_NOT_PINNED")

    try:
        source_system = json.loads(draft.profile_bytes.decode("utf-8"))["source_system"]
        profile = load_omop_mapping_profile(
            draft.profile_bytes, draft.profile_sha256, source_system)
    except (UnicodeDecodeError, ValueError, KeyError, TypeError):
        raise LocalProfileHold("LOCALDP_REVIEW_G5_PROFILE_INVALID") from None

    if (not isinstance(observed_codes, Mapping)
            or set(observed_codes) != set(_FIELDS)
            or source_meanings is not None
            and not isinstance(source_meanings, Mapping)):
        raise LocalProfileHold("LOCALDP_REVIEW_INVENTORY_FIELDS_MISSING")
    expected_counts = {
        "gender_code": patient_count, "race_code": patient_count,
        "ethnicity_code": patient_count, "encounter_class": encounter_count,
    }
    profile_maps = {
        "gender_code": profile["gender_concepts"],
        "race_code": profile["race_concepts"],
        "ethnicity_code": profile["ethnicity_concepts"],
        "encounter_class": profile["visit_class_concepts"],
    }
    gaps = []
    inventory = {}
    unmapped = {}
    for field in _FIELDS:
        counts = observed_codes[field]
        if not isinstance(counts, Mapping) or not counts or len(counts) > 128:
            raise LocalProfileHold("LOCALDP_REVIEW_SOURCE_FIELD_EMPTY")
        folded = set()
        cleaned = {}
        for code, count in counts.items():
            if (not isinstance(code, str) or not _SHA_CODE.fullmatch(code)
                    or len(code) > 50 or code.casefold() in folded
                    or type(count) is not int or count <= 0):
                raise LocalProfileHold("LOCALDP_REVIEW_SOURCE_CODE_INVALID")
            folded.add(code.casefold())
            cleaned[code] = count
        if sum(cleaned.values()) != expected_counts[field]:
            raise LocalProfileHold("LOCALDP_REVIEW_SOURCE_COUNT_DRIFT")
        inventory[field] = cleaned
        unmapped[field] = 0
        for code, count in cleaned.items():
            if code in profile_maps[field]:
                continue
            meaning = "UNREVIEWED"
            if source_meanings is not None:
                meaning = source_meanings.get((field, code), "UNREVIEWED")
                if (not isinstance(meaning, str)
                        or not 0 < len(meaning) <= 96
                        or not re.fullmatch("[A-Z0-9_]+", meaning)):
                    raise LocalProfileHold("LOCALDP_REVIEW_SOURCE_MEANING_INVALID")
            unmapped[field] += count
            gaps.append(MappingReviewGap(field, code, count, meaning))
    if source_meanings is not None:
        if not all(
            isinstance(key, tuple) and len(key) == 2 and key[0] in _FIELDS
            and isinstance(key[1], str) and key[1] in inventory[key[0]]
            for key in source_meanings
        ):
            raise LocalProfileHold("LOCALDP_REVIEW_SOURCE_MEANING_UNOBSERVED")

    gaps = tuple(sorted(gaps, key=lambda x: (x.source_field, x.source_code)))
    if tuple(x.source_field + ":" + x.source_code for x in gaps) != (
            draft.unresolved_source_codes):
        raise LocalProfileHold("LOCALDP_REVIEW_PROFILE_INVENTORY_CONFLICT")
    raw_inventory = json.dumps(inventory, sort_keys=True, ensure_ascii=False,
                               separators=(",", ":"), allow_nan=False).encode("utf-8")
    return MappingCoverageReview(
        source_system=source_system,
        source_batch_id=source_batch_id,
        manifest_sha256=manifest_sha256,
        profile_sha256=draft.profile_sha256,
        inventory_sha256=hashlib.sha256(raw_inventory).hexdigest(),
        patient_count=patient_count,
        encounter_count=encounter_count,
        unmapped_records_by_field=tuple((f, unmapped[f]) for f in _FIELDS),
        gaps=gaps,
    )

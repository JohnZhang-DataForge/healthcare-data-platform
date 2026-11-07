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

# FHIR R4 US Core codes -> *existing LocalDP semantic key*, NOT Concept IDs.
# Candidate crosswalk only; clinical reviewer must confirm each translation.
# US Core race 1002-5 and source UNK have no LocalDP race counterpart, and
# MUST remain a visible HOLD instead of inventing an OMOP concept or default 0.
FHIR_R4_LOCALDP_ALIASES = {
    "gender_code": {"male": "M", "female": "F"},
    "race_code": {
        "2028-9": "asian", "2054-5": "black",
        "2106-3": "white", "2076-8": "hawaiian",
    },
    "ethnicity_code": {
        "2135-2": "hispanic", "2186-5": "nonhispanic",
    },
    "encounter_class": {
        k: k for k in (
            "ambulatory", "emergency", "home", "hospice", "inpatient",
            "outpatient", "snf", "urgentcare", "virtual", "wellness",
        )
    },
}


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

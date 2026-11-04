"""Fail-closed P1 preflight of a proposed clinical mapping profile.

NO Azure/Spark/SQL I/O and NO clinical approval. The caller MUST independently
read G4 Silver code frequencies, the exact F1 vocabulary release and its
concept rows. Returned PASS means only internally consistent supplied evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Mapping, Sequence

from healthcare_data_engine.mapping.omop.candidates import load_omop_mapping_profile

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
# Exact source fields and OMOP concept domains; no hardcoded code->concept IDs.
_ROLES = {
    "gender_code": ("gender_concepts", "Gender"),
    "race_code": ("race_concepts", "Race"),
    "ethnicity_code": ("ethnicity_concepts", "Ethnicity"),
    "encounter_class": ("visit_class_concepts", "Visit"),
}
_REQUIRED_CONCEPT = frozenset({
    "concept_id", "domain_id", "standard_concept", "invalid_reason",
    "valid_start_date", "valid_end_date",
})


class ConceptProfileHold(ValueError):
    """Non-sensitive deterministic diagnostic, never sample patient data."""


@dataclass(frozen=True)
class ConceptPreflight:
    profile_sha256: str
    vocabulary_manifest_sha256: str
    vocabulary_release_id: str
    effective_date: str
    observed_counts: tuple[tuple[str, int], ...]
    concept_count: int
    status: str = "P1_CONCEPT_PREFLIGHT_ONLY_NOT_CLINICALLY_APPROVED"


def _sha(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def _date(value: object) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
            if parsed.isoformat() == value:
                return parsed
        except ValueError:
            pass
    raise ConceptProfileHold("P1_CONCEPT_DATE_INVALID")


def inspect_mapping_profile(
    *, mapping_profile_bytes: bytes, mapping_profile_sha256: str,
    source_system: str, observed_code_counts: Mapping[str, Mapping[str, int]],
    vocabulary_rows: Sequence[Mapping[str, Any]],
    vocabulary_release_id: str,
    vocabulary_manifest_sha256: str,
    expected_vocabulary_manifest_sha256: str,
    vocabulary_effective_date: date,
) -> ConceptPreflight:
    """Validate supplied code coverage, concept domains and release validity.

    Does NOT prove that inputs came from physical Fabric or approve a clinical
    code-to-concept mapping. Real Source/SQL readback and reviewer signoff are
    separate mandatory gates before Candidate writes.
    """
    if not _sha(vocabulary_manifest_sha256) or not _sha(
            expected_vocabulary_manifest_sha256) or (
            vocabulary_manifest_sha256 != expected_vocabulary_manifest_sha256):
        raise ConceptProfileHold("P1_VOCABULARY_MANIFEST_NOT_PINNED")
    if (not isinstance(vocabulary_release_id, str)
            or not vocabulary_release_id.strip()
            or vocabulary_release_id != vocabulary_release_id.strip()
            or len(vocabulary_release_id) > 128):
        raise ConceptProfileHold("P1_VOCABULARY_RELEASE_NOT_PINNED")
    as_of = _date(vocabulary_effective_date)
    try:
        profile = load_omop_mapping_profile(
            mapping_profile_bytes, mapping_profile_sha256, source_system)
    except ValueError as exc:
        raise ConceptProfileHold(str(exc)) from exc
    if not isinstance(observed_code_counts, Mapping) or (
            set(observed_code_counts) != set(_ROLES)):
        raise ConceptProfileHold("P1_SOURCE_CODE_INVENTORY_INCOMPLETE")

    expected: dict[int, set[str]] = {}
    count_summary: list[tuple[str, int]] = []
    for source_col, (profile_key, domain) in _ROLES.items():
        observed = observed_code_counts[source_col]
        lookup = profile[profile_key]
        if not isinstance(observed, Mapping) or not observed:
            raise ConceptProfileHold("P1_SOURCE_CODE_INVENTORY_EMPTY")
        seen_folded: set[str] = set()
        total = 0
        for code, count in observed.items():
            if (not isinstance(code, str) or not code or code != code.strip()
                    or len(code) > 50 or any(ord(c) < 32 for c in code)):
                raise ConceptProfileHold("P1_SOURCE_CODE_INVALID_OR_TRUNCATED")
            if code.casefold() in seen_folded:
                raise ConceptProfileHold("P1_SOURCE_CODE_COLLATION_COLLISION")
            seen_folded.add(code.casefold())
            if type(count) is not int or count <= 0:
                raise ConceptProfileHold("P1_SOURCE_CODE_COUNT_INVALID")
            if code not in lookup:
                raise ConceptProfileHold("P1_UNMAPPED_SOURCE_CODE:" + source_col)
            total += count
        count_summary.append((source_col, total))
        for cid in lookup.values():
            expected.setdefault(cid, set()).add(domain)
    type_id = profile["visit_type_concept_id"]
    expected.setdefault(type_id, set()).add("Type Concept")
    if not isinstance(vocabulary_rows, (list, tuple)):
        raise ConceptProfileHold("P1_CONCEPT_ROWS_NOT_A_SNAPSHOT")

    actual = {}
    for row in vocabulary_rows:
        if not isinstance(row, Mapping) or not _REQUIRED_CONCEPT.issubset(row):
            raise ConceptProfileHold("P1_CONCEPT_ROW_SCHEMA_INVALID")
        cid = row["concept_id"]
        if type(cid) is not int or cid <= 0 or cid in actual:
            raise ConceptProfileHold("P1_DUPLICATE_OR_INVALID_CONCEPT_ID")
        actual[cid] = row
    if set(actual) != set(expected):
        raise ConceptProfileHold("P1_CONCEPT_SNAPSHOT_MISSING_OR_EXTRANEOUS")
    for cid, domains in expected.items():
        row = actual[cid]
        if len(domains) != 1 or row["domain_id"] not in domains:
            raise ConceptProfileHold("P1_CONCEPT_DOMAIN_MISMATCH")
        if row["standard_concept"] != "S" or row["invalid_reason"] is not None:
            raise ConceptProfileHold("P1_CONCEPT_NOT_VALID_STANDARD")
        if not (_date(row["valid_start_date"]) <= as_of <=
                _date(row["valid_end_date"])):
            raise ConceptProfileHold("P1_CONCEPT_NOT_VALID_AT_RELEASE_DATE")
    return ConceptPreflight(
        mapping_profile_sha256, vocabulary_manifest_sha256,
        vocabulary_release_id, as_of.isoformat(),
        tuple(sorted(count_summary)), len(expected))

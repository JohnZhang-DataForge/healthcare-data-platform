"""Source-only FHIR Race resolution review against a supplied F1 vocabulary row.

This is NOT a clinical approval, an F1 SQL readback, a release signature,
a Candidate writer, or a license grant. A proposal for 1002-5 can be rendered
as a NEW G5 profile draft only after strict structural/domain/valid-date
checks. HL7 NullFlavor UNK remains unresolved; the CDM54 Concept 0 convention
is documented here as a *review question*, never inserted into the G5 mapper.
The input F1 row and source coding counts are CALLER-SUPPLIED and must later
be proven by independent physical SQL and immutable FHIR source readback.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import re
from typing import Mapping

from healthcare_data_engine.mapping.omop.candidates import load_omop_mapping_profile
from healthcare_data_engine.mapping.omop.local_profile import (
    LocalProfileDraft, LocalProfileHold, MappingCoverageReview,
)

CDC_RACE_CODE_SYSTEM = "urn:oid:2.16.840.1.113883.6.238"
HL7_NULLFLAVOR_CODE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-NullFlavor"

# These are SOURCE code-system identifiers, not OMOP target Concept IDs.
SOURCE_SYSTEMS = {"1002-5": CDC_RACE_CODE_SYSTEM,
                  "UNK": HL7_NULLFLAVOR_CODE_SYSTEM}
_REVIEWED_SOURCE_MEANING = "American Indian or Alaska Native"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,49}\Z")


@dataclass(frozen=True)
class RaceResolutionDraft:
    """A nonzero target proposal and a separate unresolved no-info question."""

    proposed_profile_bytes: bytes
    proposed_profile_sha256: str
    original_profile_sha256: str
    source_system: str
    source_batch_id: str
    manifest_sha256: str
    source_inventory_sha256: str
    claimed_f1_release_sha256: str
    proposed_standard_race_concept_id: int
    verified_source_coding_sha256: str
    unresolved_source_codes: tuple[str, ...]
    pending_no_information_source_count: int
    pending_no_information_policy: str = "UNK_OMOP_CDM54_ZERO_REQUIRES_EXPLICIT_REVIEW"
    status: str = "RACE_MAPPING_DRAFT_ONLY_F1_PHYSICAL_AND_CLINICAL_HOLD"

    @property
    def candidate_write_authorized(self) -> bool:
        return False

    @property
    def clinically_approved(self) -> bool:
        return False


def _date(value: object) -> date:
    if type(value) is date:
        return value
    if type(value) is str:
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            pass
        else:
            if parsed.isoformat() == value:
                return parsed
    raise LocalProfileHold("G5_RACE_F1_DATE_INVALID")


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def propose_race_resolution(
    coverage: MappingCoverageReview, draft: LocalProfileDraft, *,
    proposed_f1_concept_row: Mapping[str, object],
    f1_release_metadata_sha256: str,
    observed_race_coding_systems: Mapping[str, Mapping[str, int]],
    as_of: date,
) -> RaceResolutionDraft:
    """Require exact source+profile+F1 Concept evidence, but return *draft*.

    `observed_race_coding_systems` must be derived by a caller from
    immutable, independently verified raw FHIR codings; the existing
    Canonical Patient v1 holds just `race_code` and cannot independently
    prove the Coding.system. No raw resource or PHI enters this function.
    """
    if (not isinstance(coverage, MappingCoverageReview)
            or coverage.status != "MAPPING_COVERAGE_REVIEW_ONLY_NO_CLINICAL_APPROVAL"
            or not isinstance(draft, LocalProfileDraft)
            or draft.status != "LOCALDP_RULES_DRAFT_ONLY_NOT_APPROVED"
            or type(draft.profile_bytes) is not bytes
            or hashlib.sha256(draft.profile_bytes).hexdigest() != draft.profile_sha256
            or coverage.profile_sha256 != draft.profile_sha256
            or type(coverage.inventory_sha256) is not str
            or not _SHA256.fullmatch(coverage.inventory_sha256)
            or type(coverage.source_batch_id) is not str
            or not _SHA256.fullmatch(coverage.source_batch_id)
            or type(coverage.manifest_sha256) is not str
            or not _SHA256.fullmatch(coverage.manifest_sha256)
            or not isinstance(f1_release_metadata_sha256, str)
            or not _SHA256.fullmatch(f1_release_metadata_sha256)):
        raise LocalProfileHold("G5_RACE_SOURCE_PROFILE_OR_F1_PIN_INVALID")
    try:
        original = json.loads(draft.profile_bytes.decode("utf-8"))
        source_system = original["source_system"]
        load_omop_mapping_profile(draft.profile_bytes, draft.profile_sha256,
                                  source_system)
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        raise LocalProfileHold("G5_RACE_PROFILE_INVALID") from None
    if source_system != coverage.source_system:
        raise LocalProfileHold("G5_RACE_SOURCE_SCOPE_MISMATCH")

    # Be deliberately narrow: this Change does not resolve arbitrary codes
    # or additional missing-value types by extrapolating from known examples.
    gaps = {(gap.source_field, gap.source_code): gap.observed_count
            for gap in coverage.gaps}
    if (not gaps or len(gaps) != len(coverage.gaps)
            or set(gaps) - {("race_code", "1002-5"), ("race_code", "UNK")}
            or ("race_code", "1002-5") not in gaps
            or any(type(n) is not int or n <= 0 for n in gaps.values())):
        raise LocalProfileHold("G5_RACE_GAP_SCOPE_NOT_VERIFIED")
    unknown_count = gaps.get(("race_code", "UNK"), 0)
    if (not isinstance(observed_race_coding_systems, Mapping)
            or set(observed_race_coding_systems) != {code for _, code in gaps}):
        raise LocalProfileHold("G5_RACE_RAW_CODING_SYSTEM_INCOMPLETE")
    coding = {}
    for (_, code), count in sorted(gaps.items()):
        systems = observed_race_coding_systems[code]
        expected = SOURCE_SYSTEMS[code]
        if (not isinstance(systems, Mapping) or set(systems) != {expected}
                or type(systems[expected]) is not int
                or systems[expected] != count):
            raise LocalProfileHold("G5_RACE_RAW_CODING_SYSTEM_MISMATCH")
        coding[code] = {expected: count}

    if not isinstance(proposed_f1_concept_row, Mapping):
        raise LocalProfileHold("G5_RACE_F1_ROW_MISSING")
    required = {
        "concept_id", "concept_name", "domain_id", "standard_concept",
        "invalid_reason", "valid_start_date", "valid_end_date", "vocabulary_id",
    }
    if set(proposed_f1_concept_row) != required:
        raise LocalProfileHold("G5_RACE_F1_ROW_SCHEMA_MISMATCH")
    row = proposed_f1_concept_row
    concept_id = row["concept_id"]
    if (type(concept_id) is not int or not 1 <= concept_id <= 2147483647
            or row["concept_name"] != _REVIEWED_SOURCE_MEANING
            or row["domain_id"] != "Race"
            or row["vocabulary_id"] != "Race"
            or row["standard_concept"] != "S"
            or row["invalid_reason"] is not None):
        raise LocalProfileHold("G5_RACE_F1_NONSTANDARD_OR_WRONG_SEMANTICS")
    as_of_date = _date(as_of)
    if not _date(row["valid_start_date"]) <= as_of_date <= _date(row["valid_end_date"]):
        raise LocalProfileHold("G5_RACE_F1_OUTSIDE_EFFECTIVE_DATE")
    if ("1002-5" in original["race_concepts"] or
            "UNK" in original["race_concepts"]):
        raise LocalProfileHold("G5_RACE_PROFILE_MUST_BE_UNRESOLVED")

    # This *proposes* a separate candidate profile, does not mutate LocalDP
    # or return any write capability. An unsigned/claimed SQL row is never
    # enough for Notebook or Runner to treat the new SHA as approved.
    proposed = dict(original)
    proposed["race_concepts"] = {
        **original["race_concepts"], "1002-5": concept_id,
    }
    proposed["mapping_version"] = original["mapping_version"] + "-race-review-v1"
    if len(proposed["mapping_version"]) > 128:
        raise LocalProfileHold("G5_RACE_PROFILE_VERSION_OVERFLOW")
    serialized = _canonical(proposed)
    proposed_sha = hashlib.sha256(serialized).hexdigest()
    load_omop_mapping_profile(serialized, proposed_sha, source_system)
    expected_unresolved = tuple(sorted(
        f + ":" + c for f, c in gaps if c != "1002-5"
    ))
    # The original source-only coverage and the independently produced
    # LocalDP draft MUST agree; no unexplained or missing source code.
    if tuple(sorted(draft.unresolved_source_codes)) != tuple(sorted(
            f + ":" + c for f, c in gaps)):
        raise LocalProfileHold("G5_RACE_PROFILE_INVENTORY_GAP_DRIFT")

    return RaceResolutionDraft(
        proposed_profile_bytes=serialized,
        proposed_profile_sha256=proposed_sha,
        original_profile_sha256=draft.profile_sha256,
        source_system=source_system,
        source_batch_id=coverage.source_batch_id,
        manifest_sha256=coverage.manifest_sha256,
        source_inventory_sha256=coverage.inventory_sha256,
        claimed_f1_release_sha256=f1_release_metadata_sha256,
        proposed_standard_race_concept_id=concept_id,
        verified_source_coding_sha256=hashlib.sha256(_canonical(coding)).hexdigest(),
        unresolved_source_codes=expected_unresolved,
        pending_no_information_source_count=unknown_count,
    )

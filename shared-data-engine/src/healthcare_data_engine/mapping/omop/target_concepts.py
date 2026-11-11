"""Target/field-scoped OMOP Concept preflight; never clinical approval.

Operates only on supplied, cryptographically pinned profile bytes, observed
codes and independently obtained Vocabulary rows. No cloud I/O, lexical
matching, Concept guessing or writes. This complements existing FHIR P1
preflight without replacing its frozen Person/Visit input contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from healthcare_data_engine.mapping.omop.registry import EntityRegistry, DEFAULT_OMOP_REGISTRY

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_NAME = re.compile(r"[a-z][a-z0-9_]*\Z")
_TABLE = re.compile(r"cdm\.[a-z][a-z0-9_]*\Z")
# These OMOP field domains are non-negotiable in the current accepted P1.
DEFAULT_FIELD_DOMAINS = {
    ("cdm.person", "gender_concept_id"): "Gender",
    ("cdm.person", "race_concept_id"): "Race",
    ("cdm.person", "ethnicity_concept_id"): "Ethnicity",
    ("cdm.visit_occurrence", "visit_concept_id"): "Visit",
    ("cdm.visit_occurrence", "visit_type_concept_id"): "Type Concept",
}
_LEGACY_FIELDS = frozenset({"schema_version", "source_system", "mapping_version",
                            "vocabulary_manifest_sha256", "clinical_review_sha256",
                            "license_review_sha256", "rules"})
# New FHIR/HL7 Technical Admission profile binds Vocabulary and explicit
# target rules, not nonexistent human reviewer receipts.
_TECHNICAL_FIELDS = _LEGACY_FIELDS - {
    "clinical_review_sha256", "license_review_sha256",
}
_RULE_FIELDS = frozenset({"target_table", "target_field", "source_code",
                          "concept_id", "domain_id"})
_VOCAB_FIELDS = frozenset({"concept_id", "domain_id", "standard_concept",
                           "invalid_reason", "valid_start_date", "valid_end_date"})


class TargetConceptHold(ValueError):
    """Diagnostic never includes sensitive source code values."""


def _sha(value: object) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise TargetConceptHold("TARGET_CONCEPT_SHA_NOT_PINNED")
    return value


def _clinical_code(value: object) -> str:
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value) > 50 or any(ord(c) < 32 for c in value)):
        raise TargetConceptHold("TARGET_CONCEPT_SOURCE_INVALID_OR_TRUNCATED")
    return value


def _day(value: object) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
            if parsed.isoformat() == value:
                return parsed
        except ValueError:
            pass
    raise TargetConceptHold("TARGET_CONCEPT_DATE_INVALID")


@dataclass(frozen=True)
class TargetConceptRule:
    target_table: str
    target_field: str
    source_code: str
    concept_id: int
    domain_id: str

    def __post_init__(self):
        if not isinstance(self.target_table, str) or not _TABLE.fullmatch(self.target_table):
            raise TargetConceptHold("TARGET_CONCEPT_TABLE_INVALID")
        if not isinstance(self.target_field, str) or not _NAME.fullmatch(self.target_field):
            raise TargetConceptHold("TARGET_CONCEPT_FIELD_INVALID")
        _clinical_code(self.source_code)
        if type(self.concept_id) is not int or self.concept_id <= 0:
            raise TargetConceptHold("TARGET_CONCEPT_ID_INVALID")
        if not isinstance(self.domain_id, str) or not self.domain_id.strip():
            raise TargetConceptHold("TARGET_CONCEPT_DOMAIN_INVALID")


@dataclass(frozen=True)
class TargetConceptProfile:
    source_system: str
    mapping_version: str
    vocabulary_manifest_sha256: str
    clinical_review_sha256: str | None
    license_review_sha256: str | None
    mapping_sha256: str
    rules: tuple[TargetConceptRule, ...]
    status: str = "SOURCE_PROFILE_ONLY_NOT_CLINICALLY_APPROVED"


@dataclass(frozen=True)
class TargetConceptPreflight:
    mapping_sha256: str
    vocabulary_manifest_sha256: str
    concept_count: int
    observed_counts: tuple[tuple[str, str, int], ...]
    status: str = "TARGET_CONCEPT_PREFLIGHT_ONLY_NOT_CLINICALLY_APPROVED"


def load_target_concept_profile(
    raw: bytes, expected_sha256: str, source_system: str,
) -> TargetConceptProfile:
    """Reject duplicate JSON keys and any unreviewed profile fields."""
    _sha(expected_sha256)
    if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise TargetConceptHold("TARGET_CONCEPT_PROFILE_SHA_CONFLICT")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise TargetConceptHold("TARGET_CONCEPT_PROFILE_DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TargetConceptHold("TARGET_CONCEPT_PROFILE_INVALID_JSON") from exc
    schema = data.get("schema_version") if isinstance(data, dict) else None
    expected_fields = (
        _LEGACY_FIELDS if schema == "target-concept-v1"
        else _TECHNICAL_FIELDS if schema == "target-concept-v2" else None
    )
    if expected_fields is None or set(data) != expected_fields:
        raise TargetConceptHold("TARGET_CONCEPT_PROFILE_SCHEMA_INVALID")
    if (not isinstance(source_system, str) or not source_system
            or data["source_system"] != source_system
            or not isinstance(data["mapping_version"], str)
            or not data["mapping_version"].strip()):
        raise TargetConceptHold("TARGET_CONCEPT_SOURCE_OR_VERSION_MISMATCH")
    vocab = _sha(data["vocabulary_manifest_sha256"])
    if schema == "target-concept-v1":
        clinical = _sha(data["clinical_review_sha256"])
        license_sha = _sha(data["license_review_sha256"])
    else:
        # A technical v2 source profile is not a disguised human attestation.
        clinical = license_sha = None
    if not isinstance(data["rules"], list) or not data["rules"]:
        raise TargetConceptHold("TARGET_CONCEPT_RULES_EMPTY")
    rules = []
    seen = set()
    for row in data["rules"]:
        if not isinstance(row, dict) or set(row) != _RULE_FIELDS:
            raise TargetConceptHold("TARGET_CONCEPT_RULE_SCHEMA_INVALID")
        rule = TargetConceptRule(**row)
        identity = (rule.target_table, rule.target_field, rule.source_code.casefold())
        if identity in seen:
            raise TargetConceptHold("TARGET_CONCEPT_SOURCE_COLLATION_COLLISION")
        seen.add(identity)
        rules.append(rule)
    status = (
        "SOURCE_TECHNICAL_CONCEPT_PROFILE_ONLY_NOT_RELEASE"
        if schema == "target-concept-v2"
        else "SOURCE_PROFILE_ONLY_NOT_CLINICALLY_APPROVED"
    )
    return TargetConceptProfile(source_system, data["mapping_version"], vocab,
                                clinical, license_sha, expected_sha256,
                                tuple(rules), status=status)


def inspect_target_concepts(
    profile: TargetConceptProfile, *,
    source_system: str,
    observed: Mapping[tuple[str, str], Mapping[str, int]],
    vocabulary_rows: Sequence[Mapping[str, Any]],
    vocabulary_manifest_sha256: str,
    effective_date: date,
    registry: EntityRegistry = DEFAULT_OMOP_REGISTRY,
    reviewed_field_domains: Mapping[tuple[str, str], str] | None = None,
    technical_field_domains: Mapping[tuple[str, str], str] | None = None,
) -> TargetConceptPreflight:
    """Pure source/code/domain/validity preflight, never writer authority.

    v2 does not require a human Clinical/License signature. The caller MUST
    still independently check actual source-code semantics, Vocabulary
    provenance and usage rights, physical SQL, DQ and readback. A claimed
    digest or technically valid Concept does not prove clinical equivalence.
    The older reviewed_field_domains alias is retained for legacy callers.
    """
    if not isinstance(profile, TargetConceptProfile) or profile.source_system != source_system:
        raise TargetConceptHold("TARGET_CONCEPT_SOURCE_MISMATCH")
    if _sha(vocabulary_manifest_sha256) != profile.vocabulary_manifest_sha256:
        raise TargetConceptHold("TARGET_CONCEPT_VOCABULARY_RELEASE_MISMATCH")
    as_of = _day(effective_date)
    if not isinstance(registry, EntityRegistry):
        raise TargetConceptHold("TARGET_CONCEPT_REGISTRY_INVALID")
    tables = {t.table for d in registry.definitions for t in d.targets}
    if reviewed_field_domains is not None and technical_field_domains is not None:
        raise TargetConceptHold("TARGET_CONCEPT_DOMAIN_POLICY_AMBIGUOUS")
    additional_domains = (
        technical_field_domains if technical_field_domains is not None
        else reviewed_field_domains
    )
    if additional_domains is not None and not isinstance(additional_domains, Mapping):
        raise TargetConceptHold("TARGET_CONCEPT_DOMAIN_POLICY_INVALID")
    allowed = dict(DEFAULT_FIELD_DOMAINS)
    for field, domain in (additional_domains or {}).items():
        if (not isinstance(field, tuple) or len(field) != 2
                or not isinstance(domain, str) or not domain
                or field in allowed and allowed[field] != domain):
            raise TargetConceptHold("TARGET_CONCEPT_DOMAIN_OVERRIDE_FORBIDDEN")
        allowed[field] = domain
    if not isinstance(observed, Mapping) or not observed:
        raise TargetConceptHold("TARGET_CONCEPT_INVENTORY_MISSING")
    defined: dict[tuple[str, str, str], TargetConceptRule] = {}
    required: dict[int, str] = {}
    for rule in profile.rules:
        field = (rule.target_table, rule.target_field)
        if rule.target_table not in tables or allowed.get(field) != rule.domain_id:
            raise TargetConceptHold("TARGET_CONCEPT_DOMAIN_OR_TARGET_MISMATCH")
        if rule.concept_id in required and required[rule.concept_id] != rule.domain_id:
            raise TargetConceptHold("TARGET_CONCEPT_REUSED_ACROSS_DOMAINS")
        required[rule.concept_id] = rule.domain_id
        defined[(*field, rule.source_code)] = rule
    if set(observed) != {(x.target_table, x.target_field) for x in profile.rules}:
        raise TargetConceptHold("TARGET_CONCEPT_INVENTORY_INCOMPLETE")
    totals = []
    for field, counts in observed.items():
        if not isinstance(counts, Mapping) or not counts:
            raise TargetConceptHold("TARGET_CONCEPT_INVENTORY_EMPTY")
        folded = set()
        total = 0
        for code, number in counts.items():
            _clinical_code(code)
            if code.casefold() in folded:
                raise TargetConceptHold("TARGET_CONCEPT_INVENTORY_COLLATION_COLLISION")
            folded.add(code.casefold())
            if type(number) is not int or number <= 0:
                raise TargetConceptHold("TARGET_CONCEPT_COUNT_INVALID")
            if (*field, code) not in defined:
                raise TargetConceptHold("TARGET_CONCEPT_SOURCE_UNMAPPED")
            total += number
        totals.append((*field, total))
    if not isinstance(vocabulary_rows, (tuple, list)):
        raise TargetConceptHold("TARGET_CONCEPT_VOCABULARY_SNAPSHOT_INVALID")
    actual = {}
    for row in vocabulary_rows:
        if not isinstance(row, Mapping) or not _VOCAB_FIELDS.issubset(row):
            raise TargetConceptHold("TARGET_CONCEPT_VOCABULARY_SCHEMA_INVALID")
        cid = row["concept_id"]
        if type(cid) is not int or cid <= 0 or cid in actual:
            raise TargetConceptHold("TARGET_CONCEPT_DUPLICATE_OR_INVALID_ID")
        actual[cid] = row
    if set(actual) != set(required):
        raise TargetConceptHold("TARGET_CONCEPT_SNAPSHOT_MISSING_OR_EXTRANEOUS")
    for cid, domain in required.items():
        item = actual[cid]
        if item["domain_id"] != domain:
            raise TargetConceptHold("TARGET_CONCEPT_WRONG_DOMAIN")
        if item["standard_concept"] != "S" or item["invalid_reason"] is not None:
            raise TargetConceptHold("TARGET_CONCEPT_NONSTANDARD_OR_INVALID")
        if not _day(item["valid_start_date"]) <= as_of <= _day(item["valid_end_date"]):
            raise TargetConceptHold("TARGET_CONCEPT_OUTSIDE_VALID_DATE")
    status = (
        "TARGET_CONCEPT_TECHNICAL_PREFLIGHT_ONLY_NOT_RELEASE"
        if profile.status == "SOURCE_TECHNICAL_CONCEPT_PROFILE_ONLY_NOT_RELEASE"
        else "TARGET_CONCEPT_PREFLIGHT_ONLY_NOT_CLINICALLY_APPROVED"
    )
    return TargetConceptPreflight(profile.mapping_sha256,
                                  profile.vocabulary_manifest_sha256,
                                  len(actual), tuple(sorted(totals)), status=status)

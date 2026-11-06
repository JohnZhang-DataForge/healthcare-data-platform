"""Compatibility bridge from frozen G5 Person/Visit candidates to target-indexed output.

The same existing strict Silver/Concept/ID mapper runs first. This module does
not allocate Visit IDs, approve clinical mapping or publish physical Gold.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from healthcare_data_engine.mapping.omop.candidates import (
    OmopCandidates, build_omop_candidates,
)
from healthcare_data_engine.mapping.omop.registry import (
    DEFAULT_OMOP_REGISTRY, EntityRegistry, EntityRegistryHold,
)

_SHA = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class TargetCandidate:
    entity_key: str
    table: str
    rows: Any
    row_count: int
    id_state: str

    def __post_init__(self) -> None:
        if type(self.row_count) is not int or self.row_count < 0 or self.rows is None:
            raise EntityRegistryHold("ENTITY_CANDIDATE_INVALID_COUNT_OR_ROWS")
        if self.id_state not in ("EXTERNAL_PERSON_MAP_NOT_GOLD",
                                 "VISIT_ID_NOT_ALLOCATED"):
            raise EntityRegistryHold("ENTITY_CANDIDATE_ID_STATE_UNREVIEWED")


@dataclass(frozen=True)
class EntityCandidateSet:
    targets: tuple[TargetCandidate, ...]
    source_batch_id: str
    manifest_sha256: str
    processing_version: str
    mapping_sha256: str
    status: str = "ENTITY_CANDIDATE_ONLY_NOT_PUBLISHED"

    def __post_init__(self) -> None:
        if (not isinstance(self.targets, tuple) or not self.targets
                or len({c.table for c in self.targets}) != len(self.targets)
                or any(not isinstance(c, TargetCandidate) for c in self.targets)):
            raise EntityRegistryHold("ENTITY_CANDIDATE_DUPLICATE_OR_INVALID_TARGET")
        if (not isinstance(self.source_batch_id, str) or not self.source_batch_id
                or not isinstance(self.processing_version, str)
                or not self.processing_version or
                any(not isinstance(v, str) or not _SHA.fullmatch(v)
                    for v in (self.manifest_sha256, self.mapping_sha256))):
            raise EntityRegistryHold("ENTITY_CANDIDATE_PROVENANCE_INVALID")
        if self.status != "ENTITY_CANDIDATE_ONLY_NOT_PUBLISHED":
            raise EntityRegistryHold("ENTITY_CANDIDATE_CANNOT_PUBLISH")

    def for_table(self, table: str) -> TargetCandidate:
        for target in self.targets:
            if target.table == table:
                return target
        raise EntityRegistryHold("ENTITY_CANDIDATE_TARGET_NOT_REGISTERED")


def adapt_person_visit_candidates(
    legacy: OmopCandidates, *, source_batch_id: str,
    manifest_sha256: str, processing_version: str,
    registry: EntityRegistry = DEFAULT_OMOP_REGISTRY,
) -> EntityCandidateSet:
    """Wrap the existing strict mapping result; do not invent Visit INT IDs."""
    if not isinstance(legacy, OmopCandidates) or (
            legacy.status != "OMOP_CANDIDATE_ONLY_NOT_PUBLISHED"):
        raise EntityRegistryHold("ENTITY_LEGACY_CANDIDATE_NOT_APPROVED")
    if (not isinstance(registry, EntityRegistry) or
            tuple(d.entity_key for d in registry.dependency_order(
                ("person", "visit_occurrence"))) != ("person", "visit_occurrence")):
        raise EntityRegistryHold("ENTITY_LEGACY_REGISTRY_CONFLICT")
    person_def = registry.definition("person")
    visit_def = registry.definition("visit_occurrence")
    if (tuple(t.table for t in person_def.targets) != ("cdm.person",)
            or tuple(t.table for t in visit_def.targets) != ("cdm.visit_occurrence",)):
        raise EntityRegistryHold("ENTITY_LEGACY_TARGET_CONTRACT_CONFLICT")
    return EntityCandidateSet(
        targets=(
            TargetCandidate("person", "cdm.person", legacy.person,
                            legacy.person_count, "EXTERNAL_PERSON_MAP_NOT_GOLD"),
            TargetCandidate("visit_occurrence", "cdm.visit_occurrence", legacy.visit,
                            legacy.visit_count, "VISIT_ID_NOT_ALLOCATED"),
        ),
        source_batch_id=source_batch_id,
        manifest_sha256=manifest_sha256,
        processing_version=processing_version,
        mapping_sha256=legacy.mapping_sha256,
    )


def build_registered_person_visit_candidates(
    patients, encounters, identity_map, concepts, *,
    approval, hospital_id: str, source_system: str,
    source_batch_id: str, manifest_sha256: str,
    processing_version: str, mapping_profile_bytes: bytes,
    mapping_profile_sha256: str, raw_publish_run_id: str,
    registry: EntityRegistry = DEFAULT_OMOP_REGISTRY,
) -> EntityCandidateSet:
    """Execute the identical legacy G5 fail-closed mapper before wrapping.

    `registry` only checks output ownership and dependencies. Physical Silver
    verification is still the caller's responsibility; no Gold entitlement.
    """
    legacy = build_omop_candidates(
        patients, encounters, identity_map, concepts,
        approval=approval, hospital_id=hospital_id, source_system=source_system,
        source_batch_id=source_batch_id, manifest_sha256=manifest_sha256,
        processing_version=processing_version,
        mapping_profile_bytes=mapping_profile_bytes,
        mapping_profile_sha256=mapping_profile_sha256,
        raw_publish_run_id=raw_publish_run_id,
    )
    return adapt_person_visit_candidates(
        legacy, source_batch_id=source_batch_id,
        manifest_sha256=manifest_sha256,
        processing_version=processing_version, registry=registry,
    )

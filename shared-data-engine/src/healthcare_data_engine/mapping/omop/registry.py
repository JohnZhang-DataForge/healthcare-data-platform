"""Explicit platform-neutral OMOP entity registry and stable derived-row identities.

Declarative metadata only: no SQL, SparkSession, file I/O or clinical inference.
An entry is a *candidate contract*, never a Fabric/PG commit authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


_CANONICAL_SHA = {
    "patient": "e0be146222f13b2f24a84d883d70117fac9aab984c184558dab88726ac5a3dab",
    "encounter": "473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837",
}
_IDENT = re.compile(r"[a-z][a-z0-9_]*\Z")
_TABLE = re.compile(r"cdm\.[a-z][a-z0-9_]*\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class EntityRegistryHold(ValueError):
    """Nonclinical reason code only; never embed patient/source identifiers."""


def _name(value: object, field: str) -> str:
    if not isinstance(value, str) or not _IDENT.fullmatch(value):
        raise EntityRegistryHold("ENTITY_INVALID_" + field)
    return value


def _source(value: object, field: str) -> str:
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value) > 256 or any(ord(c) < 32 for c in value)):
        raise EntityRegistryHold("ENTITY_INVALID_" + field)
    return value


@dataclass(frozen=True)
class OmopTarget:
    table: str
    primary_key: str

    def __post_init__(self) -> None:
        if not isinstance(self.table, str) or not _TABLE.fullmatch(self.table):
            raise EntityRegistryHold("ENTITY_INVALID_OMOP_TABLE")
        _name(self.primary_key, "PRIMARY_KEY")


@dataclass(frozen=True)
class EntityDefinition:
    entity_key: str
    definition_version: str
    canonical_entity: str
    canonical_contract_sha256: str
    mapper_name: str
    targets: tuple[OmopTarget, ...]
    dependencies: tuple[str, ...] = ()
    publication_group: str = "person_visit_base"
    identity_strategy: str = "warehouse_global_int"

    def __post_init__(self) -> None:
        _name(self.entity_key, "KEY")
        _source(self.definition_version, "VERSION")
        _name(self.canonical_entity, "CANONICAL")
        if not isinstance(self.canonical_contract_sha256, str) or not _SHA.fullmatch(
                self.canonical_contract_sha256):
            raise EntityRegistryHold("ENTITY_CANONICAL_CONTRACT_SHA_INVALID")
        _name(self.mapper_name, "MAPPER")
        _name(self.publication_group, "PUBLICATION_GROUP")
        if self.identity_strategy != "warehouse_global_int":
            raise EntityRegistryHold("ENTITY_IDENTITY_STRATEGY_UNREVIEWED")
        if (not isinstance(self.targets, tuple) or not self.targets
                or any(not isinstance(t, OmopTarget) for t in self.targets)
                or len({t.table for t in self.targets}) != len(self.targets)):
            raise EntityRegistryHold("ENTITY_TARGETS_INVALID")
        if (not isinstance(self.dependencies, tuple)
                or any(not isinstance(x, str) or not _IDENT.fullmatch(x)
                       for x in self.dependencies)
                or len(set(self.dependencies)) != len(self.dependencies)):
            raise EntityRegistryHold("ENTITY_DEPENDENCIES_INVALID")


@dataclass(frozen=True)
class EntityRegistry:
    definitions: tuple[EntityDefinition, ...]

    def __post_init__(self) -> None:
        if (not isinstance(self.definitions, tuple) or not self.definitions
                or any(not isinstance(d, EntityDefinition) for d in self.definitions)):
            raise EntityRegistryHold("ENTITY_REGISTRY_EMPTY_OR_INVALID")
        keys: dict[str, EntityDefinition] = {}
        owners: dict[str, str] = {}
        for definition in self.definitions:
            if definition.entity_key in keys:
                raise EntityRegistryHold("ENTITY_REGISTRY_DUPLICATE_KEY")
            keys[definition.entity_key] = definition
            for target in definition.targets:
                if target.table in owners:
                    raise EntityRegistryHold("ENTITY_REGISTRY_TARGET_CONFLICT")
                owners[target.table] = definition.entity_key
        visited: set[str] = set()
        active: set[str] = set()

        def visit(key: str) -> None:
            if key in active:
                raise EntityRegistryHold("ENTITY_REGISTRY_DEPENDENCY_CYCLE")
            if key in visited:
                return
            if key not in keys:
                raise EntityRegistryHold("ENTITY_REGISTRY_UNKNOWN_DEPENDENCY")
            active.add(key)
            for parent in keys[key].dependencies:
                visit(parent)
            active.remove(key)
            visited.add(key)

        for key in sorted(keys):
            visit(key)

    def definition(self, key: str) -> EntityDefinition:
        for value in self.definitions:
            if value.entity_key == key:
                return value
        raise EntityRegistryHold("ENTITY_NOT_REGISTERED")

    def dependency_order(self, requested: Iterable[str]) -> tuple[EntityDefinition, ...]:
        """Stable topological order, including transitive parents."""
        found: set[str] = set()
        result: list[EntityDefinition] = []

        def append(key: str) -> None:
            definition = self.definition(key)
            if key in found:
                return
            for parent in sorted(definition.dependencies):
                append(parent)
            found.add(key)
            result.append(definition)

        keys = tuple(requested)
        if not keys:
            raise EntityRegistryHold("ENTITY_SELECTION_EMPTY")
        for key in sorted(keys):
            append(key)
        return tuple(result)


@dataclass(frozen=True)
class DerivedRowKey:
    """Stable source-derived identity, NOT an OMOP INT assignment.

    A caller must provide a persistent clinical/business discriminator for
    distinct outputs of the same role. No row ordinal/random/hash-derived IDs.
    """
    target_table: str
    hospital_id: str
    source_system: str
    source_business_key: str
    derived_role: str = "primary"
    derived_discriminator: str = ""

    def __post_init__(self) -> None:
        if not _TABLE.fullmatch(self.target_table):
            raise EntityRegistryHold("ENTITY_INVALID_OMOP_TABLE")
        _source(self.hospital_id, "HOSPITAL")
        _source(self.source_system, "SOURCE_SYSTEM")
        _source(self.source_business_key, "SOURCE_BUSINESS_KEY")
        _name(self.derived_role, "DERIVED_ROLE")
        if self.derived_discriminator:
            _source(self.derived_discriminator, "DERIVED_DISCRIMINATOR")
        if self.derived_role != "primary" and not self.derived_discriminator:
            raise EntityRegistryHold("ENTITY_DERIVED_DISCRIMINATOR_REQUIRED")

    def folded(self) -> tuple[str, ...]:
        return tuple(value.casefold() for value in (
            self.target_table, self.hospital_id, self.source_system,
            self.source_business_key, self.derived_role, self.derived_discriminator,
        ))


def verify_unique_derived_rows(keys: Iterable[DerivedRowKey]) -> tuple[DerivedRowKey, ...]:
    rows = tuple(keys)
    folded: set[tuple[str, ...]] = set()
    for key in rows:
        if not isinstance(key, DerivedRowKey):
            raise EntityRegistryHold("ENTITY_DERIVED_KEY_TYPE_INVALID")
        value = key.folded()
        if value in folded:
            raise EntityRegistryHold("ENTITY_DERIVED_KEY_COLLISION")
        folded.add(value)
    return rows


DEFAULT_OMOP_REGISTRY = EntityRegistry((
    EntityDefinition(
        "person", "1", "patient", _CANONICAL_SHA["patient"],
        "build_omop_candidates", (OmopTarget("cdm.person", "person_id"),),
    ),
    EntityDefinition(
        "visit_occurrence", "1", "encounter", _CANONICAL_SHA["encounter"],
        "build_omop_candidates", (OmopTarget("cdm.visit_occurrence", "visit_occurrence_id"),),
        dependencies=("person",),
    ),
))

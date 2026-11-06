"""Pure multi-entity FK reference checks against a typed Identity Preview.

No database FK/UNIQUE enforcement is assumed; this cannot prove physical Gold
readback or authorize a Warehouse COMMIT. No cross-hospital identity inference.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping

from healthcare_data_engine.mapping.omop.registry import (
    DEFAULT_OMOP_REGISTRY, DerivedRowKey, EntityRegistry,
)
from healthcare_data_engine.identity.preview import (
    IdentityPreview, IdentityPreviewHold,
)

_SHA = re.compile(r"[0-9a-f]{64}\Z")


class ReferenceHold(ValueError):
    """Non-sensitive FK reason code; never show source business keys."""


@dataclass(frozen=True)
class ResolvedParent:
    parent_entity: str
    parent_key: DerivedRowKey
    omop_id: int
    state: str
    status: str = "FK_PREFLIGHT_ONLY_NOT_COMMITTED"


def resolve_parent_reference(
    *, registry: EntityRegistry = DEFAULT_OMOP_REGISTRY,
    child_entity: str,
    child_key: DerivedRowKey,
    parent_entity: str,
    parent_key: DerivedRowKey | None,
    identity_preview: IdentityPreview,
    committed_readback_sha256: str | None = None,
    required: bool = True,
) -> ResolvedParent | None:
    """Resolve one declared dependency, fail-closed on provisional cross-group.

    A PERSISTED parent requires the *caller* to independently verify its
    committed state and supply the pinned readback digest. A digest supplied
    by itself is not trusted evidence and NEVER grants COMMIT authorization.
    """
    if not isinstance(registry, EntityRegistry) or not isinstance(child_key, DerivedRowKey):
        raise ReferenceHold("FK_REGISTRY_OR_CHILD_INVALID")
    child = registry.definition(child_entity)
    parent = registry.definition(parent_entity)
    if parent_entity not in child.dependencies:
        raise ReferenceHold("FK_UNDECLARED_DEPENDENCY")
    if child_key.target_table not in {t.table for t in child.targets}:
        raise ReferenceHold("FK_CHILD_TARGET_UNREGISTERED")
    if type(required) is not bool:
        raise ReferenceHold("FK_REQUIREMENT_INVALID")
    if parent_key is None:
        if required:
            raise ReferenceHold("FK_REQUIRED_PARENT_MISSING")
        if committed_readback_sha256 is not None:
            raise ReferenceHold("FK_ABSENT_PARENT_WITH_RECEIPT")
        return None
    if (not isinstance(parent_key, DerivedRowKey)
            or parent_key.target_table not in {t.table for t in parent.targets}):
        raise ReferenceHold("FK_PARENT_TARGET_UNREGISTERED")
    if (child_key.hospital_id != parent_key.hospital_id
            or child_key.source_system != parent_key.source_system):
        raise ReferenceHold("FK_CROSS_HOSPITAL_OR_SOURCE_NAMESPACE")
    if (not isinstance(identity_preview, IdentityPreview)
            or identity_preview.status != "ID_PREVIEW_ONLY_NOT_PERSISTED"
            or not isinstance(identity_preview.identities, tuple)):
        raise ReferenceHold("FK_IDENTITY_PREVIEW_INVALID")
    try:
        chosen = identity_preview.for_key(parent_key)
    except IdentityPreviewHold as exc:
        raise ReferenceHold("FK_PARENT_ID_NOT_IN_PREVIEW") from exc
    if chosen.snapshot_fingerprint != identity_preview.snapshot_fingerprint:
        raise ReferenceHold("FK_IDENTITY_SNAPSHOT_CONFLICT")
    if chosen.state == "PROVISIONAL":
        if child.publication_group != parent.publication_group:
            raise ReferenceHold("FK_PROVISIONAL_PARENT_CROSS_GROUP")
        if committed_readback_sha256 is not None:
            raise ReferenceHold("FK_PROVISIONAL_PARENT_NOT_DURABLE")
    elif chosen.state == "PERSISTED":
        if (not isinstance(committed_readback_sha256, str)
                or not _SHA.fullmatch(committed_readback_sha256)):
            raise ReferenceHold("FK_COMMITTED_PARENT_READBACK_REQUIRED")
    else:
        raise ReferenceHold("FK_PARENT_ID_STATE_INVALID")
    return ResolvedParent(parent_entity, parent_key, chosen.omop_id, chosen.state)


def resolve_declared_dependencies(
    *, registry: EntityRegistry,
    child_entity: str,
    child_key: DerivedRowKey,
    references: Mapping[str, DerivedRowKey | None],
    identity_preview: IdentityPreview,
    committed_readbacks: Mapping[str, str] | None = None,
) -> tuple[ResolvedParent, ...]:
    """Require every declared parent; no silent dropping of missing FKs.

    Optional relationships need a separately reviewed field-level contract
    before a publisher can claim omission is valid.
    """
    definition = registry.definition(child_entity)
    if not isinstance(references, Mapping) or set(references) != set(definition.dependencies):
        raise ReferenceHold("FK_DEPENDENCY_SET_INCOMPLETE")
    receipts = committed_readbacks or {}
    if not isinstance(receipts, Mapping) or set(receipts) - set(references):
        raise ReferenceHold("FK_UNEXPECTED_READBACK_RECEIPT")
    result = []
    for entity in sorted(definition.dependencies):
        item = resolve_parent_reference(
            registry=registry, child_entity=child_entity, child_key=child_key,
            parent_entity=entity, parent_key=references[entity],
            identity_preview=identity_preview,
            committed_readback_sha256=receipts.get(entity),
        )
        assert item is not None
        result.append(item)
    return tuple(result)

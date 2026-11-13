"""Public API for platform-neutral healthcare data transformations.

No Spark session, provider SDK, filesystem or network I/O on import.
"""
from healthcare_data_engine.models.batch_context import BatchContext, SourceObject
from healthcare_data_engine.adapters.fhir_r4.bundle import parse_fhir_resources
from healthcare_data_engine.adapters.fhir_r4.patient import normalize_fhir_patient
from healthcare_data_engine.adapters.fhir_r4.encounter import normalize_fhir_encounter
from healthcare_data_engine.canonical.validation import load_pinned_contract, canonical_schema, validate_row
from healthcare_data_engine.quality.result import Finding, ParsedResources, TransformResult
from healthcare_data_engine.reconciliation.patient_encounter import reconcile_patient_encounter, PatientEncounterReconciliation
from healthcare_data_engine.reconciliation.replay import PublicationRecord, decide_replay

__version__ = "0.1.14"
__all__ = [
    "BatchContext", "SourceObject", "parse_fhir_resources",
    "normalize_fhir_patient", "normalize_fhir_encounter",
    "load_pinned_contract", "canonical_schema", "validate_row",
    "Finding", "ParsedResources", "TransformResult",
    "PublicationRecord", "decide_replay", "reconcile_patient_encounter", "PatientEncounterReconciliation",
]

# G5 OMOP mapping API is pure PySpark and has no platform I/O.
from healthcare_data_engine.mapping.omop.candidates import (
    OmopCandidates, load_omop_mapping_profile, build_omop_candidates,
)
__all__ += ["OmopCandidates", "load_omop_mapping_profile", "build_omop_candidates"]

# Public, pure Multi-Entity contract (source-only 0.1.4 candidate).
from healthcare_data_engine.mapping.omop.registry import (
    EntityDefinition, EntityRegistry, EntityRegistryHold, OmopTarget,
    DerivedRowKey, DEFAULT_OMOP_REGISTRY, verify_unique_derived_rows,
)
from healthcare_data_engine.mapping.omop.entity_candidates import (
    TargetCandidate, EntityCandidateSet, adapt_person_visit_candidates,
    build_registered_person_visit_candidates,
)
__all__ += [
    "EntityDefinition", "EntityRegistry", "EntityRegistryHold", "OmopTarget",
    "DerivedRowKey", "DEFAULT_OMOP_REGISTRY", "verify_unique_derived_rows",
    "TargetCandidate", "EntityCandidateSet", "adapt_person_visit_candidates",
    "build_registered_person_visit_candidates",
]

# Pure source-only Identity/Concept/FK preflight, not actual Gold allocation.
from healthcare_data_engine.identity.preview import (
    IdentityPreviewHold, PersistedIdentity, IdentitySnapshot, PlannedIdentity,
    IdentityPreview, verify_allocation_proposal, bridge_f2_person_visit_allocation,
    require_preview_snapshot_unchanged,
)
from healthcare_data_engine.identity.references import (
    ReferenceHold, ResolvedParent, resolve_parent_reference,
    resolve_declared_dependencies,
)
from healthcare_data_engine.mapping.omop.target_concepts import (
    TargetConceptHold, TargetConceptRule, TargetConceptProfile,
    TargetConceptPreflight, load_target_concept_profile,
    inspect_target_concepts,
)
__all__ += [
    "IdentityPreviewHold", "PersistedIdentity", "IdentitySnapshot",
    "PlannedIdentity", "IdentityPreview", "verify_allocation_proposal",
    "bridge_f2_person_visit_allocation", "require_preview_snapshot_unchanged",
    "ReferenceHold", "ResolvedParent", "resolve_parent_reference",
    "resolve_declared_dependencies",
    "TargetConceptHold", "TargetConceptRule", "TargetConceptProfile",
    "TargetConceptPreflight", "load_target_concept_profile",
    "inspect_target_concepts",
]

# Source-only G5/F2 provisional-ID candidate handoff. Not a Gold map.
from healthcare_data_engine.identity.candidate_handoff import (
    CandidateIdentityHold, CandidatePersonId, CandidateVisitId,
    PersonVisitCandidateHandoff, plan_candidate_identity_handoff,
)
__all__ += [
    "CandidateIdentityHold", "CandidatePersonId", "CandidateVisitId",
    "PersonVisitCandidateHandoff", "plan_candidate_identity_handoff",
]

# P3 immutable Candidate release/replay planner, pure business code.
# This API has no filesystem/Spark/SQL/Fabric I/O and cannot grant Gold.
from healthcare_data_engine.mapping.omop.candidate_publication import (
    CandidatePublicationHold, CandidatePublicationPlan, FrozenCandidateScope,
    ObservedCandidate, freeze_candidate_scope, decide_candidate_publication,
    classify_mapping_failure,
)
__all__ += [
    "CandidatePublicationHold", "CandidatePublicationPlan",
    "FrozenCandidateScope", "ObservedCandidate",
    "freeze_candidate_scope", "decide_candidate_publication",
    "classify_mapping_failure",
]

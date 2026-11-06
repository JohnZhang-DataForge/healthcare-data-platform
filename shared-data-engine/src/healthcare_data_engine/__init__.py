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

__version__ = "0.1.4"
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

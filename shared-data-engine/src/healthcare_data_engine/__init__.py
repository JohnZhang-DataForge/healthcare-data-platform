"""Public API for platform-neutral healthcare data transformations.

No Spark session, provider SDK, filesystem or network I/O on import.
"""
from healthcare_data_engine.models.batch_context import BatchContext, SourceObject
from healthcare_data_engine.adapters.fhir_r4.bundle import parse_fhir_resources
from healthcare_data_engine.adapters.fhir_r4.patient import normalize_fhir_patient
from healthcare_data_engine.adapters.fhir_r4.encounter import normalize_fhir_encounter
from healthcare_data_engine.canonical.validation import load_pinned_contract, canonical_schema, validate_row
from healthcare_data_engine.quality.result import Finding, ParsedResources, TransformResult
from healthcare_data_engine.reconciliation.replay import PublicationRecord, decide_replay

__version__ = "0.1.0"
__all__ = [
    "BatchContext", "SourceObject", "parse_fhir_resources",
    "normalize_fhir_patient", "normalize_fhir_encounter",
    "load_pinned_contract", "canonical_schema", "validate_row",
    "Finding", "ParsedResources", "TransformResult",
    "PublicationRecord", "decide_replay",
]

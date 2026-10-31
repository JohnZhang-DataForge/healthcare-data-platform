"""FHIR R4 Encounter to Local Canonical Encounter v1 with strict Patient FK."""
from __future__ import annotations
from datetime import datetime, timezone

from healthcare_data_engine.adapters.fhir_r4.references import resolve_patient
from healthcare_data_engine.canonical.validation import validate_row
from healthcare_data_engine.models.batch_context import BatchContext
from healthcare_data_engine.quality.result import Finding, ParsedResources, TransformResult

CLASS_CODES = {
    "AMB": "ambulatory", "EMER": "emergency", "IMP": "inpatient",
    "HH": "home", "VR": "virtual",
    "ambulatory": "ambulatory", "emergency": "emergency",
    "inpatient": "inpatient", "outpatient": "outpatient",
    "home": "home", "hospice": "hospice", "snf": "snf",
    "urgentcare": "urgentcare", "virtual": "virtual", "wellness": "wellness",
}


def _instant(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("FHIR_PERIOD_START_END_REQUIRED")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("FHIR_PERIOD_MISSING_TIMEZONE")
    return result.astimezone(timezone.utc)


def _reference_id(value: object, kind: str) -> str | None:
    if not isinstance(value, dict):
        return None
    ref = value.get("reference")
    if not isinstance(ref, str):
        return None
    prefix = kind + "/"
    return ref[len(prefix):] if ref.startswith(prefix) and ref.count("/") == 1 else None


def normalize_fhir_encounter(parsed: ParsedResources, contract: dict,
                             context: BatchContext) -> TransformResult:
    if contract.get("entity") != "encounter" or contract.get("canonical_version") != "v1":
        raise ValueError("ENCOUNTER_CONTRACT_REQUIRED")
    accepted, quarantined, rejected = [], [], [
        x for x in parsed.rejected if x.resource_type in ("Encounter", "")]
    for item in parsed.accepted:
        if item.resource_type != "Encounter":
            continue
        resource = item.resource
        subject = resource.get("subject")
        ref = subject.get("reference") if isinstance(subject, dict) else None
        patient = resolve_patient(ref, parsed.accepted)
        if patient is None:
            rejected.append(Finding("REJECTED", "UNRESOLVED_PATIENT_REFERENCE",
                                    str(ref), "Encounter", item.resource_id, item.source.source_file))
            continue
        try:
            period = resource.get("period")
            period = period if isinstance(period, dict) else {}
            start, end = _instant(period.get("start")), _instant(period.get("end"))
            if end < start:
                raise ValueError("ENCOUNTER_END_BEFORE_START")
            raw_class = resource.get("class")
            raw_class = raw_class if isinstance(raw_class, dict) else {}
            code = raw_class.get("code")
            encounter_class = CLASS_CODES.get(code)
            if encounter_class is None:
                raise ValueError("ENCOUNTER_CLASS_MISSING_OR_UNMAPPED")
            types = resource.get("type")
            if not isinstance(types, list) or not types or not isinstance(types[0], dict):
                raise ValueError("ENCOUNTER_TYPE_MISSING")
            codings = types[0].get("coding")
            if not isinstance(codings, list) or not codings or not isinstance(codings[0], dict):
                raise ValueError("ENCOUNTER_CODING_MISSING")
            source_code = codings[0].get("code")
            if not isinstance(source_code, str) or not source_code.strip():
                raise ValueError("ENCOUNTER_SOURCE_CODE_MISSING")
            row = {
                "source_encounter_id": item.resource_id,
                "source_person_id": patient.resource_id,
                "start_datetime": start,
                "end_datetime": end,
                "encounter_class": encounter_class,
                "source_code": source_code,
                "source_description": types[0].get("text"),
                "source_organization_id": _reference_id(resource.get("serviceProvider"), "Organization"),
                "source_provider_id": None, "source_payer_id": None,
                "base_encounter_cost": None, "total_claim_cost": None, "payer_coverage": None,
                "reason_code": None, "reason_description": None,
                **context.provenance(item.source),
            }
            errors = validate_row(row, contract)
            if errors:
                raise ValueError("CONTRACT_V1:" + ";".join(errors))
        except (ValueError, TypeError, AttributeError) as exc:
            quarantined.append(Finding("QUARANTINED", "ENCOUNTER_CANONICAL_V1_INCOMPATIBLE",
                                       str(exc), "Encounter", item.resource_id, item.source.source_file))
        else:
            accepted.append(row)
    return TransformResult(tuple(accepted), tuple(quarantined), tuple(rejected))

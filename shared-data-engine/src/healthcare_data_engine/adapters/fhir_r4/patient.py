"""FHIR R4 Patient to Local Canonical Patient v1, without clinical defaults."""
from __future__ import annotations
from datetime import date

from healthcare_data_engine.canonical.validation import validate_row
from healthcare_data_engine.models.batch_context import BatchContext
from healthcare_data_engine.quality.result import Finding, ParsedResources, TransformResult

RACE_URL = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race"
ETHNICITY_URL = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity"
GENDERS = {"male", "female", "other", "unknown"}


def _extension_codes(resource: dict, uri: str) -> list[str]:
    result = []
    for extension in resource.get("extension", []):
        if not isinstance(extension, dict) or extension.get("url") != uri:
            continue
        for part in [extension, *extension.get("extension", [])]:
            if not isinstance(part, dict):
                continue
            coding = part.get("valueCoding")
            if isinstance(coding, dict) and isinstance(coding.get("code"), str):
                result.append(coding["code"])
            concepts = part.get("valueCodeableConcept", {}).get("coding", []) if isinstance(
                part.get("valueCodeableConcept", {}), dict) else []
            for value in concepts:
                if isinstance(value, dict) and isinstance(value.get("code"), str):
                    result.append(value["code"])
    return list(dict.fromkeys(result))


def _date(value: object, nullable: bool) -> date | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError("FHIR_DATE_REQUIRED")
    return date.fromisoformat(value)


def normalize_fhir_patient(parsed: ParsedResources, contract: dict,
                           context: BatchContext) -> TransformResult:
    if contract.get("entity") != "patient" or contract.get("canonical_version") != "v1":
        raise ValueError("PATIENT_CONTRACT_REQUIRED")
    accepted, quarantined = [], []
    for item in parsed.accepted:
        if item.resource_type != "Patient":
            continue
        resource = item.resource
        try:
            races = _extension_codes(resource, RACE_URL)
            ethnicities = _extension_codes(resource, ETHNICITY_URL)
            if len(races) != 1:
                raise ValueError("FHIR_RACE_MISSING_OR_AMBIGUOUS")
            if len(ethnicities) != 1:
                raise ValueError("FHIR_ETHNICITY_MISSING_OR_AMBIGUOUS")
            gender = resource.get("gender")
            if gender not in GENDERS:
                raise ValueError("FHIR_GENDER_MISSING_OR_INVALID")
            row = {
                "source_record_id": item.resource_id,
                "birth_date": _date(resource.get("birthDate"), False),
                "death_date": _date(resource.get("deceasedDateTime", "").split("T")[0], True)
                if resource.get("deceasedDateTime") else None,
                "gender_code": gender,
                "race_code": races[0],
                "ethnicity_code": ethnicities[0],
                **context.provenance(item.source),
            }
            errors = validate_row(row, contract)
            if errors:
                raise ValueError("CONTRACT_V1:" + ";".join(errors))
        except (ValueError, TypeError, AttributeError) as exc:
            quarantined.append(Finding("QUARANTINED", "PATIENT_CANONICAL_V1_INCOMPATIBLE",
                                       str(exc), "Patient", item.resource_id, item.source.source_file))
        else:
            accepted.append(row)
    return TransformResult(tuple(accepted), tuple(quarantined),
                           tuple(x for x in parsed.rejected if x.resource_type in ("Patient", "")))

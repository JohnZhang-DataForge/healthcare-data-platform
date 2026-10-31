"""FHIR R4 reference resolution; fullUrl, URN UUID and relative IDs are explicit."""
from __future__ import annotations
from healthcare_data_engine.quality.result import ParsedResource


def resolve_patient(reference: str, resources: tuple[ParsedResource, ...]) -> ParsedResource | None:
    if not isinstance(reference, str) or not reference:
        return None
    patients = [x for x in resources if x.resource_type == "Patient"]
    # Full URL may be urn:uuid, absolute URL or another opaque FHIR identifier.
    exact = [x for x in patients if x.full_url == reference]
    if len(exact) == 1:
        return exact[0]
    if exact:
        return None
    if reference.startswith("Patient/") and reference.count("/") == 1:
        rid = reference.split("/", 1)[1]
        relative = [x for x in patients if x.resource_id == rid]
        return relative[0] if len(relative) == 1 else None
    return None

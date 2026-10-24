"""Strict immutable request contract for the new generator; no OMOP dependencies."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

SCHEMA_VERSION = "synthea-new-generation-request-v1"
SYNTHEA_VERSION = "v3.3.0"
SYNTHEA_COMMIT = "995cf2fd33e67918d4e33110d9f68ad248002221"
MAX_POPULATION = 500  # conservative bounded initial limit; revisit after real resource tests
MAX_SEED = 2**63 - 1
REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{7,65}$")
CITY = re.compile(r"^[A-Za-z][A-Za-z .'-]{0,79}$")
STATES = frozenset((
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
))
FORMATS = frozenset(("CSV", "FHIR_R4"))
REQUIRED = frozenset((
    "schema_version", "request_id", "generation_mode", "population",
    "state", "seed", "reference_date", "output_formats",
))
OPTIONAL = frozenset(("city", "clinician_seed"))


class GenerationBlocked(ValueError):
    """Invalid request, unsafe immutable state, or invalid generated payload."""


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise GenerationBlocked("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def load_request(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise GenerationBlocked("INVALID_REQUEST_FILE")
    try:
        return normalize(json.loads(path.read_text(encoding="utf-8"),
                                    object_pairs_hook=_reject_duplicates))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GenerationBlocked("INVALID_REQUEST_JSON") from exc


def normalize(raw: dict) -> dict:
    if not isinstance(raw, dict) or not REQUIRED.issubset(raw) or set(raw) - REQUIRED - OPTIONAL:
        raise GenerationBlocked("INVALID_REQUEST_FIELDS")
    if raw["schema_version"] != SCHEMA_VERSION or raw["generation_mode"] != "NEW_ONLY":
        raise GenerationBlocked("UNSUPPORTED_REQUEST_MODE_OR_VERSION")
    if not isinstance(raw["request_id"], str) or not REQUEST_ID.fullmatch(raw["request_id"]):
        raise GenerationBlocked("INVALID_REQUEST_ID")
    if type(raw["population"]) is not int or not 1 <= raw["population"] <= MAX_POPULATION:
        raise GenerationBlocked("INVALID_POPULATION")
    if not isinstance(raw["state"], str) or raw["state"] not in STATES:
        raise GenerationBlocked("INVALID_STATE")
    city = raw.get("city")
    if city is not None and (not isinstance(city, str) or not CITY.fullmatch(city)
                             or city != city.strip()):
        raise GenerationBlocked("INVALID_CITY")
    for key in ("seed", "clinician_seed"):
        val = raw.get(key, raw["seed"])
        if type(val) is not int or not 1 <= val <= MAX_SEED:
            raise GenerationBlocked("INVALID_SEED")
    reference = raw["reference_date"]
    if not isinstance(reference, str) or not re.fullmatch(r"\d{8}", reference):
        raise GenerationBlocked("INVALID_REFERENCE_DATE")
    try:
        parsed = dt.datetime.strptime(reference, "%Y%m%d")
        if parsed.strftime("%Y%m%d") != reference:
            raise ValueError("noncanonical date")
    except ValueError as exc:
        raise GenerationBlocked("INVALID_REFERENCE_DATE") from exc
    formats = raw["output_formats"]
    if (not isinstance(formats, list) or not formats
            or any(not isinstance(fmt, str) or fmt not in FORMATS for fmt in formats)
            or len(set(formats)) != len(formats)):
        raise GenerationBlocked("INVALID_OUTPUT_FORMATS")
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": raw["request_id"],
        "generation_mode": "NEW_ONLY",
        "population": raw["population"],
        "state": raw["state"],
        "city": city,
        "seed": raw["seed"],
        "clinician_seed": raw.get("clinician_seed", raw["seed"]),
        "reference_date": reference,
        "output_formats": sorted(formats),
        "synthea_version": SYNTHEA_VERSION,
        "synthea_commit": SYNTHEA_COMMIT,
    }


def canonical_bytes(data: dict) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n").encode("utf-8")


def fingerprint(request: dict) -> str:
    return hashlib.sha256(canonical_bytes(request)).hexdigest()

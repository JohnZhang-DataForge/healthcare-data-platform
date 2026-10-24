"""Translate versioned simulated-hospital feed profiles into Synthea source requests.

Generator does not import this module: hospital/format routing belongs to the caller.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from apps.synthea.synthea_new_generator.request import (
    GenerationBlocked, SCHEMA_VERSION, canonical_bytes, normalize,
)

PROFILE_VERSION = "synthea-hospital-feed-profile-v1"
ID = re.compile(r"^[a-z][a-z0-9-]{2,63}$")


def _pairs_unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise GenerationBlocked("DUPLICATE_PROFILE_KEY")
        result[key] = value
    return result


def validate_profile(profile: dict) -> dict:
    if not isinstance(profile, dict) or set(profile) != {
        "schema_version", "hospital_id", "feed_id", "location",
        "generation_defaults", "delivery",
    } or profile.get("schema_version") != PROFILE_VERSION:
        raise GenerationBlocked("INVALID_HOSPITAL_PROFILE")
    for key in ("hospital_id", "feed_id"):
        if not isinstance(profile[key], str) or not ID.fullmatch(profile[key]):
            raise GenerationBlocked("INVALID_HOSPITAL_FEED_ID")
    location = profile["location"]
    if not isinstance(location, dict) or set(location) != {"state", "city"}:
        raise GenerationBlocked("INVALID_HOSPITAL_LOCATION")
    defaults = profile["generation_defaults"]
    if not isinstance(defaults, dict) or set(defaults) != {
        "population", "seed", "reference_date",
    }:
        raise GenerationBlocked("INVALID_GENERATION_DEFAULTS")
    delivery = profile["delivery"]
    if not isinstance(delivery, dict) or set(delivery) != {
        "source_format", "target_format", "transformer",
    } or delivery["source_format"] != "FHIR_R4":
        raise GenerationBlocked("INVALID_FEED_DELIVERY")
    targets = {("FHIR_R4", "DIRECT"), ("HL7_V2", "OIE")}
    if (delivery["target_format"], delivery["transformer"]) not in targets:
        raise GenerationBlocked("INVALID_FEED_TRANSFORMER")
    # Reuse the generator's real geographic/quantity/format contract.
    build_request(profile, "profile-check-0001")
    return profile


def load_profile(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise GenerationBlocked("INVALID_PROFILE_FILE")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"),
                         object_pairs_hook=_pairs_unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GenerationBlocked("INVALID_PROFILE_JSON") from exc
    return validate_profile(raw)


def build_request(profile: dict, request_id: str, *, population=None,
                  seed=None, reference_date=None) -> dict:
    """Profiles select inputs only; same generator for FHIR and HL7 feeds."""
    loc = profile["location"]
    defaults = profile["generation_defaults"]
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "generation_mode": "NEW_ONLY",
        "population": defaults["population"] if population is None else population,
        "state": loc["state"],
        "city": loc["city"],
        "seed": defaults["seed"] if seed is None else seed,
        "reference_date": (defaults["reference_date"] if reference_date is None
                           else reference_date),
        "output_formats": [profile["delivery"]["source_format"]],
    }
    # Return the wire request, not the normalized internal representation.
    normalize(request)
    return request


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a simulated-hospital request")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--population", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--reference-date")
    args = parser.parse_args()
    try:
        profile = load_profile(args.profile)
        request = build_request(profile, args.request_id,
                                population=args.population, seed=args.seed,
                                reference_date=args.reference_date)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(canonical_bytes(request))
    except (GenerationBlocked, OSError, ValueError) as exc:
        print("HOSPITAL_PROFILE_BLOCKED=" + str(exc).split("\n", 1)[0], file=sys.stderr)
        return 1
    print("HOSPITAL_PROFILE_REQUEST_CREATED=" + args.request_id)
    print("HOSPITAL_SOURCE_FORMAT=FHIR_R4")
    return 0


if __name__ == "__main__":
    sys.exit(main())

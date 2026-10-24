"""Read-only, fail-closed FHIR handoff from a frozen Synthea generation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from apps.clinical_producers.hospital_profiles import load_profile
from apps.synthea.synthea_new_generator.generator import (
    COMPLETED, MANIFEST_VERSION, sha256, validate_payload,
)
from apps.synthea.synthea_new_generator.request import (
    GenerationBlocked, OPTIONAL, REQUIRED, REQUEST_ID, fingerprint, normalize,
)

VERSION = "synthea-fhir-source-handoff-v1"
STATUS = "SOURCE_HANDOFF_VERIFIED"


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise GenerationBlocked("DUPLICATE_HANDOFF_INPUT_KEY")
        obj[key] = value
    return obj


def _read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise GenerationBlocked("MISSING_OR_UNSAFE_HANDOFF_INPUT")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GenerationBlocked("INVALID_HANDOFF_INPUT_JSON") from exc
    if not isinstance(doc, dict):
        raise GenerationBlocked("INVALID_HANDOFF_INPUT_SHAPE")
    return doc


def verify_handoff(state_root: Path, profile_path: Path, request_id: str) -> dict:
    """Verify actual local bytes; never create a READY marker or write to cloud."""
    profile = load_profile(profile_path)
    if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
        raise GenerationBlocked("INVALID_HANDOFF_REQUEST_ID")
    state_root = Path(state_root)
    request_base = state_root / "requests"
    folder = request_base / request_id
    payload = folder / "payload"
    if any(x.is_symlink() or not x.is_dir()
           for x in (state_root, request_base, folder, payload)):
        raise GenerationBlocked("UNSAFE_HANDOFF_DIRECTORY")

    frozen = _read_json(folder / "request.json")
    if set(frozen) != {"request", "request_sha256"} or not isinstance(frozen["request"], dict):
        raise GenerationBlocked("INVALID_FROZEN_REQUEST")
    request = frozen["request"]
    wire = {k: v for k, v in request.items() if k in REQUIRED | OPTIONAL}
    if (normalize(wire) != request or request["request_id"] != request_id
            or fingerprint(request) != frozen["request_sha256"]):
        raise GenerationBlocked("FROZEN_REQUEST_MISMATCH")
    if ("FHIR_R4" not in request["output_formats"]
            or request["state"] != profile["location"]["state"]
            or request["city"] != profile["location"]["city"]):
        raise GenerationBlocked("HANDOFF_PROFILE_REQUEST_MISMATCH")

    manifest_path = folder / "generation-manifest.json"
    manifest = _read_json(manifest_path)
    actual = validate_payload(payload, request)
    expected = {
        "schema_version": MANIFEST_VERSION,
        "request_id": request_id,
        "request_sha256": fingerprint(request),
        "status": COMPLETED,
        **actual,
    }
    if manifest != expected:
        raise GenerationBlocked("HANDOFF_MANIFEST_MISMATCH")
    fhir_files = [dict(row) for row in actual["files"] if row["format"] == "FHIR_R4"]
    if not fhir_files:
        raise GenerationBlocked("HANDOFF_MISSING_FHIR")
    return {
        "schema_version": VERSION,
        "status": STATUS,
        "hospital_id": profile["hospital_id"],
        "feed_id": profile["feed_id"],
        "request_id": request_id,
        "request_sha256": fingerprint(request),
        "source_manifest_sha256": sha256(manifest_path),
        "request_relative_path": "requests/" + request_id,
        "source_format": "FHIR_R4",
        "target_format": profile["delivery"]["target_format"],
        "transformer": profile["delivery"]["transformer"],
        "files": fhir_files,
        "metrics": actual["metrics"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only FHIR producer handoff verification")
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--request-id", required=True)
    args = parser.parse_args()
    try:
        handoff = verify_handoff(args.state_root, args.profile, args.request_id)
    except (GenerationBlocked, OSError, ValueError) as exc:
        print("FHIR_SOURCE_HANDOFF_BLOCKED=" + str(exc).split("\n", 1)[0], file=sys.stderr)
        return 1
    print(json.dumps(handoff, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())

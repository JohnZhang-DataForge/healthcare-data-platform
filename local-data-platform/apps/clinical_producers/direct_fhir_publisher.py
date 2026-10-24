"""Verified Generator FHIR R4 -> common Blob Publisher; no hospital-specific code.

This adapter reads a frozen read-only Synthea source and follows the external
hospital feed Profile. No OIE, new Generator invocation, or Azure credentials.
"""
from __future__ import annotations

from pathlib import Path
from pathlib import PurePosixPath

from apps.clinical_producers.azure_blob_publisher import BlobBackend, publish_immutable
from apps.clinical_producers.blob_publish_contract import VERSION as PLAN_VERSION
from apps.clinical_producers.hospital_profiles import load_profile
from apps.clinical_producers.source_handoff import verify_handoff
from apps.synthea.synthea_new_generator.generator import sha256


class DirectFHIRBlocked(ValueError):
    """Frozen FHIR delivery cannot be proven safe for direct publishing."""


def prepare_direct_fhir(state_root: Path, profile_path: Path,
                        request_id: str) -> tuple[dict, dict[str, bytes]]:
    """Build a complete verified Publisher plan before allowing any PUT.

    verify_handoff independently validates frozen Request, Generator Manifest,
    Patient/Encounter references, hospital geography and every file SHA256.
    """
    profile = load_profile(Path(profile_path))
    if profile["delivery"] != {
        "source_format": "FHIR_R4",
        "target_format": "FHIR_R4",
        "transformer": "DIRECT",
    }:
        raise DirectFHIRBlocked("DIRECT_FHIR_PROFILE_REQUIRED")

    handoff = verify_handoff(Path(state_root), Path(profile_path), request_id)
    if (handoff["hospital_id"] != profile["hospital_id"]
            or handoff["feed_id"] != profile["feed_id"]
            or handoff["target_format"] != "FHIR_R4"
            or handoff["transformer"] != "DIRECT"):
        raise DirectFHIRBlocked("HANDOFF_DELIVERY_IDENTITY_MISMATCH")
    folder = Path(state_root) / handoff["request_relative_path"]
    manifest = folder / "generation-manifest.json"
    payload = folder / "payload"
    if (manifest.is_symlink() or
            sha256(manifest) != handoff["source_manifest_sha256"]):
        raise DirectFHIRBlocked("SOURCE_MANIFEST_CHANGED")

    sources = {}
    objects = []
    for file in handoff["files"]:
        name = file["path"]
        relative = PurePosixPath(name)
        if (len(relative.parts) != 2 or relative.parts[0] != "fhir"
                or relative.is_absolute() or str(relative) != name
                or set(file) != {"path", "format", "sha256", "size_bytes"}
                or file["format"] != "FHIR_R4"):
            raise DirectFHIRBlocked("UNSAFE_HANDOFF_FILE")
        target = payload / relative
        if (target.is_symlink() or target.parent.is_symlink()
                or not target.is_file()):
            raise DirectFHIRBlocked("UNSAFE_HANDOFF_FILE")
        sources[name] = target.read_bytes()
        objects.append({
            "name": name,
            "size_bytes": file["size_bytes"],
            "sha256": file["sha256"],
            "source_event_id": None,
        })

    # Manifest and source might change during a non-readonly local test.
    # Real deployment MUST mount the original Generator PVC readOnly.
    if sha256(manifest) != handoff["source_manifest_sha256"]:
        raise DirectFHIRBlocked("SOURCE_MANIFEST_CHANGED")

    plan = {
        "schema_version": PLAN_VERSION,
        "hospital_id": handoff["hospital_id"],
        "feed_id": handoff["feed_id"],
        "request_id": handoff["request_id"],
        "source_manifest_sha256": handoff["source_manifest_sha256"],
        "target_format": "FHIR_R4",
        "verification_state": "SOURCE_HANDOFF_VERIFIED",
        "skipped_non_admissions": 0,
        "objects": objects,
    }
    return plan, sources


def publish_direct_fhir(state_root: Path, profile_path: Path, request_id: str,
                        *, landing_prefix: str, backend: BlobBackend) -> dict:
    """Calls the shared immutable publisher only after local handoff succeeds.

    Live Azure operations require an explicitly authorized/constructed backend.
    """
    plan, sources = prepare_direct_fhir(state_root, profile_path, request_id)
    return publish_immutable(plan, sources, landing_prefix=landing_prefix,
                             backend=backend)

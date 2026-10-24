#!/usr/bin/env python3
"""Allowlisted single-image build plan for manually dispatched Local DP CI.

No docker/network/registry operations occur in this module.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass


REGISTRY = "ghcr.io/johnzhang-dataforge"
ALLOWED_OPERATIONS = frozenset({"validate", "publish", "promote-latest"})
DIGEST_PATTERN = re.compile(r"sha256:[a-f0-9]{64}\Z")


@dataclass(frozen=True)
class ImageSpec:
    package: str
    dockerfile_dir: str
    smoke: str
    parent_package: str = ""
    writer_import: bool = False


IMAGES: dict[str, ImageSpec] = {
    "synthea": ImageSpec(
        "healthcare-data-platform-synthea", "synthea",
        "test -s /opt/synthea/synthea-with-dependencies.jar",
    ),
    "task004-runtime": ImageSpec(
        "healthcare-data-platform-task004-runtime", "task004-runtime",
        "test -x /usr/local/bin/task004-runtime",
    ),
    "task004-cdm-runtime": ImageSpec(
        "healthcare-data-platform-task004-cdm-runtime", "task004-cdm-runtime",
        "test -s /opt/task004/cdm_runtime_cli.py",
    ),
    "landing-discovery-runtime": ImageSpec(
        "healthcare-landing-discovery", "landing-discovery-runtime",
        "test -s /opt/healthcare/landing_discovery/run_airflow_scan.py",
    ),
    "landing-claim-runtime": ImageSpec(
        "healthcare-landing-claim", "landing-claim-runtime",
        "test -s /opt/healthcare/landing_claim/claim_discovered_inventory.py",
    ),
    "synthea-new-only": ImageSpec(
        "healthcare-data-platform-local-dp-synthea-new-only", "synthea-new-only",
        "test -s /opt/synthea-new-only/entrypoint.py",
        parent_package="healthcare-data-platform-synthea",
    ),
    "landing-processing-runtime": ImageSpec(
        "healthcare-data-platform-local-dp-landing-processing-v2",
        "landing-processing-runtime",
        "test -s /data/spark/healthcare-data-platform/apps/task004/csv-contract-v2.json",
        parent_package="healthcare-data-platform-task004-runtime",
    ),
    "new-only-omop-writer": ImageSpec(
        "healthcare-data-platform-local-dp-omop-writer", "new-only-omop-writer",
        "test -s /opt/task004/new_only_airflow_writer.py",
        parent_package="healthcare-data-platform-task004-cdm-runtime",
        writer_import=True,
    ),
}


def build_plan(image: str, operation: str, git_ref: str, parent_digest: str = "") -> dict[str, str]:
    """Reject unknown selections and mutation on non-Main; return static safe output."""
    if image not in IMAGES:
        raise ValueError("BLOCKED:IMAGE_NOT_ALLOWLISTED")
    if operation not in ALLOWED_OPERATIONS:
        raise ValueError("BLOCKED:OPERATION_NOT_ALLOWLISTED")
    if operation != "validate" and git_ref != "refs/heads/main":
        raise ValueError("BLOCKED:IMAGE_PUBLISH_REQUIRES_MAIN")
    spec = IMAGES[image]
    if parent_digest and not spec.parent_package:
        raise ValueError("BLOCKED:BASE_IMAGE_HAS_NO_PARENT")
    if parent_digest and not DIGEST_PATTERN.fullmatch(parent_digest):
        raise ValueError("BLOCKED:INVALID_PARENT_DIGEST")
    return {
        "package": f"{REGISTRY}/{spec.package}",
        "dockerfile": f"local-data-platform/images/{spec.dockerfile_dir}/Dockerfile",
        "parent_repo": f"{REGISTRY}/{spec.parent_package}" if spec.parent_package else "",
        "parent_digest": parent_digest,
        "smoke": spec.smoke,
        "writer_import": str(spec.writer_import).lower(),
        "publish": str(operation != "validate").lower(),
        "promote": str(operation == "promote-latest").lower(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--git-ref", required=True)
    parser.add_argument("--parent-digest", default="")
    args = parser.parse_args()
    try:
        result = build_plan(args.image, args.operation, args.git_ref, args.parent_digest)
    except ValueError as exc:
        parser.error(str(exc))
    for key, value in result.items():
        assert "\n" not in value and "\r" not in value, key
        print(f"{key}={value}")


if __name__ == "__main__":
    main()

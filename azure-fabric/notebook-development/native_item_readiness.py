"""Fail-closed read-only Native Item readiness check (no Fabric API/cloud I/O)."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

ITEMS = {
    "Notebook": "notebooks/ingestion/nb_fhir_ingest.Notebook",
    "DataPipeline": "pipelines/pl_fhir_ingest.DataPipeline",
    "Environment": "environments/env_healthcare.Environment",
}

@dataclass(frozen=True)
class Readiness:
    state: str
    reasons: tuple[str, ...]


def check_native_export(workspace_git_root: Path) -> Readiness:
    """Never infer logicalId/GUID from names or past johnzhang-test metadata.

    Valid exported file content/IDs and live Fabric Git status require a later
    authorized read-only preflight; presence here only permits further review.
    """
    errors = []
    for kind, name in ITEMS.items():
        path = workspace_git_root / name
        if not (path.is_dir() and (path / ".platform").is_file()):
            errors.append("MISSING_REAL_EXPORTED_" + kind.upper() + ":" + name)
    if errors:
        return Readiness("BLOCKED_NATIVE_EXPORT", tuple(errors))
    return Readiness("HOLD_NATIVE_ID_FORMAT_REVIEW",
                     ("not deployment approval; verify exported .platform/logicalIds, "
                      "Git connection, RBAC, capacity/cost, Environment Published versions",))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "workspaces/healthcare-omop"
    result = check_native_export(root)
    print(result.state)
    for reason in result.reasons:
        print(reason)
    raise SystemExit(2)  # never claim deployability from file presence alone

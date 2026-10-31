"""Read-only Fabric Git Native source preflight; never assert live runtime success."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import re

ITEMS = {
    "Notebook": ("nb_fhir_ingest.Notebook", "nb_fhir_ingest", "notebook-content.py"),
    "DataPipeline": ("pl_fhir_ingest.DataPipeline", "pl_fhir_ingest", "pipeline-content.json"),
    "Environment": ("env_healthcare.Environment", "env_healthcare", "Setting/Sparkcompute.yml"),
}
UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")


@dataclass(frozen=True)
class Readiness:
    state: str
    reasons: tuple[str, ...]


def check_native_export(workspace_git_root: Path) -> Readiness:
    errors = []
    seen = set()
    for kind, (folder, display_name, content_path) in ITEMS.items():
        path = workspace_git_root / folder
        if not (path / ".platform").is_file() or not (path / content_path).is_file():
            errors.append("MISSING_REAL_EXPORTED_" + kind.upper() + ":" + folder)
            continue
        try:
            obj = json.loads((path / ".platform").read_text(encoding="utf-8"))
            metadata = obj["metadata"]
            config = obj["config"]
        except (OSError, ValueError, KeyError, TypeError):
            errors.append("INVALID_PLATFORM_METADATA:" + folder)
            continue
        if not isinstance(metadata, dict) or not isinstance(config, dict):
            errors.append("INVALID_PLATFORM_METADATA:" + folder)
            continue
        if metadata.get("type") != kind or metadata.get("displayName") != display_name:
            errors.append("INVALID_NATIVE_IDENTITY:" + folder)
        identifier = config.get("logicalId")
        if not isinstance(identifier, str) or not UUID.fullmatch(identifier) or identifier.lower() == "00000000-0000-0000-0000-000000000000":
            errors.append("INVALID_NATIVE_LOGICAL_ID:" + folder)
        elif identifier.lower() in seen:
            errors.append("DUPLICATE_NATIVE_LOGICAL_ID:" + folder)
        else:
            seen.add(identifier.lower())
    if errors:
        return Readiness("BLOCKED_NATIVE_EXPORT", tuple(errors))
    return Readiness("HOLD_NATIVE_RUNTIME_DEPLOYMENT",
                     ("Fabric Git source present; Wheel/Environment publish and binding, "
                      "Workspace Update-from-Git, Spark/Delta E2E remain unverified",))


if __name__ == "__main__":
    workspace = Path(__file__).resolve().parents[1] / "workspaces/healthcare-omop"
    result = check_native_export(workspace)
    print(result.state)
    for reason in result.reasons:
        print(reason)
    raise SystemExit(2)

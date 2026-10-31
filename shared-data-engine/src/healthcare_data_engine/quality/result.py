"""Typed transformation outcomes; Accepted is never confused with Quarantine/Reject."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Finding:
    classification: str  # QUARANTINED or REJECTED
    reason: str
    detail: str
    resource_type: str
    resource_id: str
    source_file: str


@dataclass(frozen=True)
class ParsedResource:
    resource: dict[str, Any]
    resource_type: str
    resource_id: str
    full_url: str | None
    source: Any  # immutable SourceObject; no platform dependencies


@dataclass(frozen=True)
class ParsedResources:
    accepted: tuple[ParsedResource, ...]
    rejected: tuple[Finding, ...]

    @property
    def metrics(self) -> dict[str, int]:
        return {"accepted": len(self.accepted), "rejected": len(self.rejected)}


@dataclass(frozen=True)
class TransformResult:
    accepted: tuple[dict[str, Any], ...]
    quarantined: tuple[Finding, ...]
    rejected: tuple[Finding, ...]

    @property
    def metrics(self) -> dict[str, int]:
        return {"accepted": len(self.accepted),
                "quarantined": len(self.quarantined),
                "rejected": len(self.rejected),
                "total": len(self.accepted) + len(self.quarantined) + len(self.rejected)}

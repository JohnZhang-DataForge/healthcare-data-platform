"""Immutable, explicit source, processing and publication identities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import re


@dataclass(frozen=True)
class BatchContext:
    hospital_id: str
    feed_id: str
    source_system: str
    request_id: str
    manifest_sha256: str
    processing_version: str
    processing_run_id: str
    source_version: str
    source_ingest_date: date
    processed_at: datetime
    publication_id: str | None = None
    canonical_version: str = "v1"
    adapter_version: str = "0.1.0"

    def __post_init__(self) -> None:
        for name in ("hospital_id", "feed_id", "source_system", "request_id",
                     "processing_version", "processing_run_id", "source_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("INVALID_SOURCE_CONTEXT:" + name)
        if not isinstance(self.manifest_sha256, str) or not re.fullmatch(
                r"[a-fA-F0-9]{64}", self.manifest_sha256):
            raise ValueError("INVALID_MANIFEST_SHA256")
        if not isinstance(self.source_ingest_date, date) or isinstance(
                self.source_ingest_date, datetime):
            raise ValueError("INVALID_SOURCE_INGEST_DATE")
        if not isinstance(self.processed_at, datetime) or self.processed_at.tzinfo is None:
            raise ValueError("PROCESSED_AT_REQUIRES_TIMEZONE")

    @property
    def namespaced_source_system(self) -> str:
        return ":".join((self.source_system, self.hospital_id, self.feed_id))

    @property
    def source_batch_id(self) -> str:
        payload = json.dumps(
            (self.hospital_id, self.feed_id, self.source_system,
             self.request_id, self.manifest_sha256.lower()),
            separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def processing_identity(self) -> tuple[str, str]:
        return self.source_batch_id, self.processing_version

    def provenance(self, source: SourceObject) -> dict:
        return {
            "source_system": self.namespaced_source_system,
            "source_version": self.source_version,
            "source_batch_id": self.source_batch_id,
            "source_ingest_date": self.source_ingest_date,
            "source_file": source.source_file,
            "source_file_sha256": source.sha256.lower(),
            "source_file_size_bytes": source.size_bytes,
            "adapter_name": "fhir_r4",
            "adapter_version": self.adapter_version,
            "canonical_version": self.canonical_version,
            "processing_run_id": self.processing_run_id,
            "processed_at": self.processed_at.astimezone(timezone.utc),
        }


@dataclass(frozen=True)
class SourceObject:
    """Caller supplies exact original bytes and independent expected receipt values."""
    source_file: str
    payload: bytes
    sha256: str
    size_bytes: int
    hospital_id: str | None = None
    feed_id: str | None = None
    source_system: str | None = None

    @classmethod
    def from_bytes(cls, source_file: str, payload: bytes, **kwargs) -> SourceObject:
        return cls(source_file, payload, hashlib.sha256(payload).hexdigest(),
                   len(payload), **kwargs)

    def verify(self, context: BatchContext) -> str | None:
        if not isinstance(self.payload, bytes) or not isinstance(self.source_file, str) or not self.source_file:
            return "INVALID_SOURCE_OBJECT"
        if self.hospital_id is not None and self.hospital_id != context.hospital_id:
            return "CROSS_HOSPITAL_SOURCE_CONFLICT"
        if self.feed_id is not None and self.feed_id != context.feed_id:
            return "CROSS_FEED_SOURCE_CONFLICT"
        if self.source_system is not None and self.source_system != context.source_system:
            return "CROSS_SOURCE_SYSTEM_CONFLICT"
        if self.size_bytes != len(self.payload):
            return "SOURCE_SIZE_MISMATCH"
        if not isinstance(self.sha256, str) or self.sha256.lower() != hashlib.sha256(
                self.payload).hexdigest():
            return "SOURCE_SHA256_MISMATCH"
        return None

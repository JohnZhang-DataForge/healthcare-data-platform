"""Read-only replay and unknown-ACK decisions. No data writes or ledger mutation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from healthcare_data_engine.models.batch_context import BatchContext


@dataclass(frozen=True)
class PublicationRecord:
    hospital_id: str
    feed_id: str
    source_system: str
    request_id: str
    manifest_sha256: str
    processing_version: str
    publication_id: str
    approved: bool


def decide_replay(context: BatchContext, records: Iterable[PublicationRecord],
                  unknown_ack: bool = False) -> str:
    """Return NEW, SKIP, HOLD_CONFLICT, HOLD_VERSION or VERIFY_READONLY."""
    if unknown_ack:
        return "VERIFY_READONLY"
    for record in records:
        if (record.hospital_id, record.feed_id, record.source_system, record.request_id) != (
                context.hospital_id, context.feed_id, context.source_system, context.request_id):
            continue
        if record.manifest_sha256.lower() != context.manifest_sha256.lower():
            return "HOLD_CONFLICT"
        if record.processing_version != context.processing_version:
            return "HOLD_VERSION"
        if not record.approved or not record.publication_id:
            return "VERIFY_READONLY"
        return "SKIP"
    return "NEW"

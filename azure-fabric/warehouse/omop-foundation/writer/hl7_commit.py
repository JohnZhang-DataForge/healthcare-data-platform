"""HL7 Canonical Silver -> existing Shared Candidate / Warehouse Gold writer.

This is a trusted-runner integration boundary, not a new OMOP mapper or
independent SQL writer. The caller must supply authenticated, independently
reopened OneLake Delta and Warehouse SQL readers; the function verifies the
complete source-bound Silver batch twice before delegating to the EXISTING
candidate/Gold transaction implementation. No notebook flag or approval
boolean is sufficient to authorize a write.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
import re
from typing import Any

from healthcare_data_engine.canonical.validation import load_pinned_contract, validate_row
from healthcare_data_engine.identity.candidate_handoff import PersonVisitCandidateHandoff
from healthcare_data_engine.mapping.omop.candidate_publication import FrozenCandidateScope
from healthcare_data_engine.models.batch_context import BatchContext
from fhir_commit import commit_verified_fhir_batch

HL7_HOSPITAL = "johns-creek-hospital-b"
HL7_FEED = "johns-creek-hospital-b-hl7-v2"
HL7_SOURCE = "johns-creek-hl7"
HL7_ADAPTER = "1.3.5"
HL7_FORMAT = "HL7v2.5.1"
SOURCE_PRESERVATION = "VERIFIED_HL7_CANDIDATE_V1"
SILVER_TABLES = frozenset(
    {"canonical_patient", "canonical_encounter", "silver_approval"})
SHA = re.compile(r"[0-9a-f]{64}\Z")


class HL7CommitHold(RuntimeError):
    """Only fixed diagnostic reasons; never embed clinical identifiers."""


def _verify_scope(context: BatchContext, scope: FrozenCandidateScope,
                  handoff: PersonVisitCandidateHandoff) -> None:
    if (not isinstance(context, BatchContext)
            or not isinstance(scope, FrozenCandidateScope)
            or not isinstance(handoff, PersonVisitCandidateHandoff)):
        raise HL7CommitHold("HL7_GOLD_TYPED_SOURCE_HANDOFF_REQUIRED")
    if (context.hospital_id != HL7_HOSPITAL
            or context.feed_id != HL7_FEED
            or context.source_system != HL7_SOURCE
            or context.source_version != HL7_FORMAT
            or context.adapter_version != HL7_ADAPTER
            or context.canonical_version != "v1"
            or scope.hospital_id != context.hospital_id
            or scope.feed_id != context.feed_id
            or scope.source_system != context.namespaced_source_system
            or scope.request_id != context.request_id
            or scope.source_batch_id != context.source_batch_id
            or scope.manifest_sha256 != context.manifest_sha256.lower()
            or scope.silver_processing_version != context.processing_version
            or scope.silver_publication_id != handoff.silver_publication_id
            or handoff.hospital_id != context.hospital_id
            or handoff.source_system != context.namespaced_source_system
            or handoff.source_batch_id != context.source_batch_id
            or handoff.manifest_sha256 != context.manifest_sha256.lower()
            or handoff.processing_version != context.processing_version
            or handoff.snapshot_fingerprint != scope.identity_snapshot_fingerprint
            or handoff.status != "CANDIDATE_ID_HANDOFF_ONLY_NOT_PERSISTED"):
        raise HL7CommitHold("HL7_GOLD_SOURCE_IDENTITY_OR_SCOPE_DRIFT")


def _verify_silver(reader: Callable[[], Mapping[str, object]],
                   context: BatchContext, scope: FrozenCandidateScope,
                   patient_contract_bytes: bytes,
                   encounter_contract_bytes: bytes) -> None:
    """Read real Silver twice; require all source rows, FK, DQ and approval.

    Readers MUST be trusted-runner implementations issuing independent fresh
    authenticated physical Delta GETs. Merely passing a dict here is never
    sufficient for COMMIT: the downstream existing Writer also opens physical
    Candidate and Warehouse independently, with a trusted release gate.
    """
    if not callable(reader):
        raise HL7CommitHold("HL7_GOLD_INDEPENDENT_SILVER_READER_REQUIRED")
    try:
        patient_contract = load_pinned_contract(patient_contract_bytes, "patient")
        encounter_contract = load_pinned_contract(encounter_contract_bytes, "encounter")
    except Exception:
        raise HL7CommitHold("HL7_GOLD_PINNED_CANONICAL_CONTRACT_DRIFT") from None
    if not patient_contract or not encounter_contract:
        raise HL7CommitHold("HL7_GOLD_CANONICAL_CONTRACT_UNAVAILABLE")
    approval_expected = {
        "source_batch_id": scope.source_batch_id,
        "manifest_sha256": scope.manifest_sha256,
        "processing_version": scope.silver_processing_version,
        "publication_id": scope.silver_publication_id,
        "patient_count": scope.patient_count,
        "encounter_count": scope.encounter_count,
        "quarantine_count": 0,
        "patient_contract_sha256": hashlib.sha256(
            patient_contract_bytes).hexdigest(),
        "encounter_contract_sha256": hashlib.sha256(
            encounter_contract_bytes).hexdigest(),
        "source_preservation_strategy": SOURCE_PRESERVATION,
        "status": "SILVER_APPROVED",
    }
    observations = []
    try:
        for _ in range(2):
            observed = reader()
            if not isinstance(observed, Mapping) or set(observed) != SILVER_TABLES:
                raise HL7CommitHold("HL7_GOLD_SILVER_TABLE_SET_DRIFT")
            patients = observed["canonical_patient"]
            encounters = observed["canonical_encounter"]
            approvals = observed["silver_approval"]
            if (not isinstance(patients, (tuple, list))
                    or not isinstance(encounters, (tuple, list))
                    or not isinstance(approvals, (tuple, list))
                    or len(approvals) != 1
                    or not isinstance(approvals[0], Mapping)
                    or dict(approvals[0]) != approval_expected
                    or len(patients) != scope.patient_count
                    or len(encounters) != scope.encounter_count):
                raise HL7CommitHold("HL7_GOLD_SILVER_APPROVAL_OR_COUNTS_DRIFT")
            person_ids, encounter_ids = set(), set()
            prefix = ("clinical/v1/" + HL7_HOSPITAL + "/" + HL7_FEED +
                      "/" + context.request_id + "/HL7_V2/hl7/")
            for rows, primary, contract in (
                    (patients, "source_record_id", patient_contract),
                    (encounters, "source_encounter_id", encounter_contract)):
                for row in rows:
                    if not isinstance(row, Mapping):
                        raise HL7CommitHold("HL7_GOLD_SILVER_ROW_TYPE_DRIFT")
                    if validate_row(row, contract):
                        raise HL7CommitHold("HL7_GOLD_SILVER_CANONICAL_CONTRACT_INVALID")
                    if (row.get("source_system") != context.namespaced_source_system
                            or row.get("source_batch_id") != scope.source_batch_id
                            or row.get("source_version") != HL7_FORMAT
                            or row.get("adapter_name") != "hl7apy"
                            or row.get("adapter_version") != HL7_ADAPTER
                            or row.get("canonical_version") != "v1"
                            or not isinstance(row.get("source_file"), str)
                            or not row["source_file"].startswith(prefix)
                            or not isinstance(row.get("source_file_sha256"), str)
                            or not SHA.fullmatch(row["source_file_sha256"])
                            or not isinstance(row.get(primary), str)
                            or not row[primary]):
                        raise HL7CommitHold("HL7_GOLD_SILVER_SOURCE_OR_CONTRACT_DRIFT")
                    keys = person_ids if primary == "source_record_id" else encounter_ids
                    if row[primary] in keys:
                        raise HL7CommitHold("HL7_GOLD_SILVER_DUPLICATE_SOURCE_KEY")
                    keys.add(row[primary])
            if any(not isinstance(row.get("source_person_id"), str)
                   or row["source_person_id"] not in person_ids
                   for row in encounters):
                raise HL7CommitHold("HL7_GOLD_SILVER_ORPHAN_ENCOUNTER")
            # Convert only to serializable, complete equality snapshots; no
            # computed SHA or a single external receipt replaces row equality.
            observations.append((
                tuple(dict(row) for row in patients),
                tuple(dict(row) for row in encounters),
                dict(approvals[0]),
            ))
    except HL7CommitHold:
        raise
    except Exception:
        raise HL7CommitHold("HL7_GOLD_SILVER_PHYSICAL_READ_FAILED") from None
    if observations[0] != observations[1]:
        raise HL7CommitHold("HL7_GOLD_SILVER_TWO_PHYSICAL_READS_DISAGREE")


def commit_verified_hl7_batch(
    *, context: BatchContext, scope: FrozenCandidateScope,
    handoff: PersonVisitCandidateHandoff,
    patient_contract_bytes: bytes, encounter_contract_bytes: bytes,
    read_silver_physical: Callable[[], Mapping[str, object]],
    connection: Any, independent_connection: Callable[[], Any],
    single_writer_fence: Callable[[], bool],
    release_gate: Callable[[Any], bool],
    read_candidate_physical: Callable[[], Mapping[str, object]],
    read_warehouse_physical: Callable[[], Any],
    mapping_version: str, writer_version: str,
    technical_evidence_sha256: str,
) -> str:
    """Delegate HL7 Gold/Replay to the proven source-neutral existing Writer.

    This is not the live controller. Its caller must independently establish
    Fabric/OIDC authority, the original HL7 raw provenance, real Vocabulary,
    correct published Environment and an exclusive Warehouse writer lease.
    """
    _verify_scope(context, scope, handoff)
    if (not isinstance(technical_evidence_sha256, str)
            or not SHA.fullmatch(technical_evidence_sha256)
            or not isinstance(mapping_version, str) or not mapping_version
            or not isinstance(writer_version, str) or not writer_version):
        raise HL7CommitHold("HL7_GOLD_TECHNICAL_EVIDENCE_OR_WRITER_INVALID")
    _verify_silver(read_silver_physical, context, scope,
                   patient_contract_bytes, encounter_contract_bytes)
    # No new Mapper, ID allocator or SQL DML. The same function that passed
    # FHIR real Gold handles Candidate/SQL twice, COMMIT and replay checking.
    return commit_verified_fhir_batch(
        connection=connection, independent_connection=independent_connection,
        single_writer_fence=single_writer_fence, release_gate=release_gate,
        scope=scope, handoff=handoff,
        read_candidate_physical=read_candidate_physical,
        read_warehouse_physical=read_warehouse_physical,
        mapping_version=mapping_version, writer_version=writer_version,
        technical_evidence_sha256=technical_evidence_sha256)

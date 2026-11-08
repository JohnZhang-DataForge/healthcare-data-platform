"""Pure HL7 dbt Candidate to shared Canonical v1 DQ handoff.

Consumes only already verified Candidate rows. Uses pinned Shared Contract
validation and existing Shared PK/FK reconciliation. No SparkSession, Delta,
Azure, OIE, OMOP, Silver approval, file I/O, persistence or writer calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import re
from typing import Any, Iterable, Mapping

from healthcare_data_engine.canonical.validation import (
    load_pinned_contract, validate_row,
)
from healthcare_data_engine.models.batch_context import BatchContext
from healthcare_data_engine.quality.result import Finding, TransformResult
from healthcare_data_engine.reconciliation.patient_encounter import (
    PatientEncounterReconciliation, reconcile_patient_encounter,
)

HL7_SOURCE = "johns-creek-hl7"
HL7_HOSPITAL = "johns-creek-hospital-b"
HL7_FEED = "johns-creek-hospital-b-hl7-v2"
HL7_ADAPTER = "hl7apy"
HL7_ADAPTER_VERSION = "1.3.5"
HL7_SOURCE_VERSION = "HL7v2.5.1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_RAW_EVENT_NAME = re.compile(r"[A-Za-z0-9-]+-(?:A01|A03)[.]hl7")


class HL7HandoffHold(ValueError):
    """Source/processing identity mismatch; never publish any row."""


@dataclass(frozen=True)
class HL7CanonicalHandoff:
    status: str
    patient: TransformResult
    encounter: TransformResult

    @property
    def metrics(self) -> dict[str, int]:
        return PatientEncounterReconciliation(
            patient=self.patient, encounter=self.encounter).metrics


def _as_utc(value: object, *, spark_timestamp_timezone: str | None) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("TIMESTAMP_TYPE")
    if value.tzinfo is None:
        # A naive local Spark TIMESTAMP can only be interpreted when the
        # caller independently verified spark.sql.session.timeZone == UTC.
        if spark_timestamp_timezone != "UTC":
            raise HL7HandoffHold("NAIVE_TIMESTAMP_WITHOUT_VERIFIED_SPARK_UTC")
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _verified_candidate_metadata(
    row: Mapping[str, Any], context: BatchContext, *,
    spark_timestamp_timezone: str | None,
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise HL7HandoffHold("INVALID_CANDIDATE_ROW")
    identity = {
        "source_system": HL7_SOURCE,
        "source_batch_id": context.request_id,
        "source_version": HL7_SOURCE_VERSION,
        "adapter_name": HL7_ADAPTER,
        "adapter_version": HL7_ADAPTER_VERSION,
        "canonical_version": context.canonical_version,
        "processing_run_id": context.processing_run_id,
        "source_ingest_date": context.source_ingest_date,
    }
    if any(row.get(k) != v for k, v in identity.items()):
        raise HL7HandoffHold("LEGACY_HL7_SOURCE_OR_PROCESSING_SCOPE_DRIFT")
    prefix = (
        f"clinical/v1/{context.hospital_id}/{context.feed_id}/"
        f"{context.request_id}/HL7_V2/hl7/"
    )
    source_file = row.get("source_file")
    sha = row.get("source_file_sha256")
    if (not isinstance(source_file, str) or not source_file.startswith(prefix)
            or not _RAW_EVENT_NAME.fullmatch(source_file[len(prefix):])
            or not isinstance(sha, str) or not _SHA256.fullmatch(sha)
            or type(row.get("source_file_size_bytes")) is not int
            or row["source_file_size_bytes"] <= 0):
        raise HL7HandoffHold("UNVERIFIED_HL7_PROVENANCE")
    try:
        processed = _as_utc(row.get("processed_at"),
                            spark_timestamp_timezone=spark_timestamp_timezone)
    except (TypeError, ValueError) as exc:
        raise HL7HandoffHold("PROCESSING_TIMESTAMP_UNVERIFIED") from exc
    if processed != context.processed_at.astimezone(timezone.utc):
        raise HL7HandoffHold("PROCESSING_TIME_DRIFT")

    output = dict(row)  # do not mutate physical Candidate rows
    output["source_system"] = context.namespaced_source_system
    output["source_batch_id"] = context.source_batch_id
    output["processed_at"] = processed
    for col in ("start_datetime", "end_datetime"):
        if col in output and output[col] is not None:
            try:
                output[col] = _as_utc(
                    output[col], spark_timestamp_timezone=spark_timestamp_timezone)
            except ValueError:
                # Canonical v1 validation quarantines malformed clinical facts.
                pass
    return output


def _validate_entity(
    rows: Iterable[Mapping[str, Any]], entity: str, contract: Mapping[str, Any],
    context: BatchContext, *, spark_timestamp_timezone: str | None,
) -> TransformResult:
    accepted: list[dict[str, Any]] = []
    quarantined: list[Finding] = []
    key = "source_record_id" if entity == "patient" else "source_encounter_id"
    for original in rows:
        row = _verified_candidate_metadata(original, context,
                     spark_timestamp_timezone=spark_timestamp_timezone)
        reasons = list(validate_row(row, contract))
        if entity == "patient":
            if (isinstance(row.get("birth_date"), date)
                    and isinstance(row.get("death_date"), date)
                    and row["death_date"] < row["birth_date"]):
                reasons.append("DEATH_BEFORE_BIRTH")
        else:
            start, end = row.get("start_datetime"), row.get("end_datetime")
            if isinstance(start, datetime) and isinstance(end, datetime) and end < start:
                reasons.append("ENCOUNTER_END_BEFORE_START")
            if row.get("encounter_class") not in contract["allowed_encounter_classes"]:
                reasons.append("INVALID_ENCOUNTER_CLASS")
        if reasons:
            quarantined.append(Finding(
                "QUARANTINED", "HL7_CANONICAL_V1_DQ_FAILED",
                ";".join(reasons), entity.title(),
                str(row.get(key, "")), str(row.get("source_file", "")),
            ))
        else:
            accepted.append(row)
    return TransformResult(tuple(accepted), tuple(quarantined), ())


def prepare_hl7_canonical_handoff(
    patients: Iterable[Mapping[str, Any]],
    encounters: Iterable[Mapping[str, Any]], *,
    context: BatchContext,
    patient_contract_bytes: bytes,
    encounter_contract_bytes: bytes,
    spark_timestamp_timezone: str | None = None,
) -> HL7CanonicalHandoff:
    """Only plans a DQ handoff; cannot create a Silver Approval or publication.

    Caller must independently read back physical Candidate Delta and must
    explicitly pass spark_timestamp_timezone="UTC" for naive Spark timestamps
    only when that SparkSession is configured with UTC session timeZone.
    """
    if (context.hospital_id, context.feed_id, context.source_system) != (
            HL7_HOSPITAL, HL7_FEED, HL7_SOURCE):
        raise HL7HandoffHold("UNREVIEWED_HOSPITAL_OR_SOURCE_PROFILE")
    if (context.canonical_version != "v1"
            or context.adapter_version != HL7_ADAPTER_VERSION):
        raise HL7HandoffHold("UNREVIEWED_ADAPTER_OR_CANONICAL_VERSION")
    if context.processed_at.utcoffset() != timezone.utc.utcoffset(None):
        raise HL7HandoffHold("PROCESSING_CONTEXT_NOT_UTC")
    # Existing shared engine validates the exact authoritative original bytes.
    patient_contract = load_pinned_contract(patient_contract_bytes, "patient")
    encounter_contract = load_pinned_contract(encounter_contract_bytes, "encounter")
    patient = _validate_entity(patients, "patient", patient_contract, context,
                spark_timestamp_timezone=spark_timestamp_timezone)
    encounter = _validate_entity(encounters, "encounter", encounter_contract, context,
                spark_timestamp_timezone=spark_timestamp_timezone)
    result = reconcile_patient_encounter(patient, encounter, context)
    m = result.metrics
    status = ("CANDIDATE_DQ_PASS_NOT_SILVER_APPROVED"
              if m["patient_accepted"] > 0 and m["encounter_accepted"] > 0
              and not any(m[k] for k in (
                  "patient_rejected", "encounter_rejected",
                  "patient_quarantined", "encounter_quarantined"))
              else "HOLD_DQ_NO_SILVER_APPROVAL")
    return HL7CanonicalHandoff(status, result.patient, result.encounter)

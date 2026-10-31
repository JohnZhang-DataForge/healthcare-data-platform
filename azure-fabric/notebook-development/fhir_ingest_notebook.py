"""P2 offline candidate for Fabric Notebook nb_fhir_ingest.

NOT a deployable Native Notebook Item: .platform, logicalId and actual workspace
bindings must be exported from healthcare-omop before authoring a Git Item.
This file is one Notebook application's visible ETL, not a second Python package,
I/O framework, scheduler or Fabric Spark Job Definition.

Production execution is explicitly disabled by default. Offline tests only
exercise synthetic Spark DataFrames and pure data/manifest checks.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
from typing import Iterable, Mapping, Any

from healthcare_data_engine import (
    __version__ as engine_version,
    BatchContext, SourceObject, PublicationRecord, decide_replay,
    parse_fhir_resources, normalize_fhir_patient, normalize_fhir_encounter,
    reconcile_patient_encounter, load_pinned_contract,
)
from healthcare_data_engine.canonical.validation import accepted_dataframe
from healthcare_data_engine.quality.result import Finding


@dataclass(frozen=True)
class PreparedBatch:
    patient_df: Any
    encounter_df: Any
    patient_count: int
    encounter_count: int
    findings: tuple[Finding, ...]
    source_batch_id: str
    processing_version: str
    publication_id: str
    manifest_sha256: str
    source_receipts: tuple[dict, ...]

    @property
    def acceptable(self) -> bool:
        return self.patient_count > 0 and not self.findings


@dataclass(frozen=True)
class NotebookOutcome:
    status: str
    source_batch_id: str
    processing_version: str
    publication_id: str | None
    metrics: dict[str, int]
    reasons: tuple[str, ...]


def _manifest_objects(manifest_bytes: bytes, context: BatchContext) -> tuple[dict, ...]:
    """Validate exact signed-by-hash Manifest bytes and source enumeration."""
    if not isinstance(manifest_bytes, bytes) or hashlib.sha256(manifest_bytes).hexdigest() != (
            context.manifest_sha256.lower()):
        raise ValueError("MANIFEST_SHA256_CONFLICT_HOLD")
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("INVALID_MANIFEST_JSON") from exc
    if not isinstance(manifest, dict):
        raise ValueError("INVALID_MANIFEST_SCHEMA")
    required_context = ("hospital_id", "feed_id", "source_system", "request_id")
    if any(manifest.get(key) != getattr(context, key) for key in required_context):
        raise ValueError("MANIFEST_SOURCE_NAMESPACE_CONFLICT")
    objects = manifest.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError("EMPTY_OR_INVALID_MANIFEST_OBJECTS")
    seen: set[str] = set()
    result = []
    for entry in objects:
        if not isinstance(entry, dict):
            raise ValueError("INVALID_MANIFEST_OBJECT")
        name, sha, size = entry.get("path"), entry.get("sha256"), entry.get("size_bytes")
        if not isinstance(name, str) or not name or name.startswith(("/", "\\")) or "\\" in name:
            raise ValueError("MANIFEST_OBJECT_PATH_INVALID")
        parts = PurePosixPath(name).parts
        if ".." in parts or "." in parts or ":" in name or "*" in name or "?" in name:
            raise ValueError("MANIFEST_OBJECT_PATH_INVALID")
        if name in seen:
            raise ValueError("DUPLICATE_MANIFEST_OBJECT_PATH")
        seen.add(name)
        if not isinstance(sha, str) or len(sha) != 64 or any(
                c not in "0123456789abcdefABCDEF" for c in sha):
            raise ValueError("INVALID_MANIFEST_OBJECT_SHA256")
        if not isinstance(size, int) or isinstance(size, bool) or size < 1:
            raise ValueError("INVALID_MANIFEST_OBJECT_SIZE")
        result.append({"path": name, "sha256": sha.lower(), "size_bytes": size})
    return tuple(result)


def verify_source_objects(manifest_bytes: bytes, objects: Iterable[SourceObject],
                          context: BatchContext) -> tuple[dict, ...]:
    specs = _manifest_objects(manifest_bytes, context)
    provided = tuple(objects)
    if len(provided) != len(specs):
        raise ValueError("MANIFEST_SOURCE_OBJECT_COUNT_MISMATCH")
    by_name: dict[str, SourceObject] = {}
    for obj in provided:
        if obj.source_file in by_name:
            raise ValueError("DUPLICATE_SOURCE_OBJECT_NAME")
        by_name[obj.source_file] = obj
    if set(by_name) != {x["path"] for x in specs}:
        raise ValueError("MANIFEST_SOURCE_PATH_SET_MISMATCH")
    receipts = []
    for expected in specs:
        obj = by_name[expected["path"]]
        if obj.sha256.lower() != expected["sha256"] or obj.size_bytes != expected["size_bytes"]:
            raise ValueError("SOURCE_MANIFEST_SHA_OR_SIZE_MISMATCH")
        issue = obj.verify(context)
        if issue:
            raise ValueError(issue)
        receipts.append(dict(expected))
    return tuple(receipts)


def read_source_objects_native(spark, *, source_root: str, manifest_bytes: bytes,
                               context: BatchContext) -> tuple[SourceObject, ...]:
    """Actual Fabric native Spark binaryFile read; caller selects approved Shortcut/Copy root.

    No custom cloud SDK. This is NOT run by offline CI or without future live grant.
    """
    if not source_root or ".." in source_root or any(c in source_root for c in "*?"):
        raise ValueError("UNVERIFIED_SOURCE_ROOT")
    result = []
    for spec in _manifest_objects(manifest_bytes, context):
        uri = source_root.rstrip("/") + "/" + spec["path"]
        rows = spark.read.format("binaryFile").load(uri).select("content").collect()
        if len(rows) != 1:
            raise ValueError("SOURCE_READ_COUNT_MISMATCH:" + spec["path"])
        result.append(SourceObject(
            source_file=spec["path"], payload=bytes(rows[0].content),
            sha256=spec["sha256"], size_bytes=spec["size_bytes"],
            hospital_id=context.hospital_id, feed_id=context.feed_id,
            source_system=context.source_system))
    verify_source_objects(manifest_bytes, result, context)
    return tuple(result)


def _content_publication_id(context: BatchContext, patient_rows: tuple[dict, ...],
                            encounter_rows: tuple[dict, ...]) -> str:
    """Separate deterministic content digest; never confuse with source batch identity."""
    fingerprint = json.dumps({
        "source_batch": context.source_batch_id,
        "processing_version": context.processing_version,
        "patient": sorted(patient_rows, key=lambda r: r["source_record_id"]),
        "encounter": sorted(encounter_rows, key=lambda r: r["source_encounter_id"]),
    }, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(fingerprint).hexdigest()


def prepare_batch(spark, *, context: BatchContext, manifest_bytes: bytes,
                  source_objects: Iterable[SourceObject],
                  patient_contract_bytes: bytes, encounter_contract_bytes: bytes) -> PreparedBatch:
    """Offline-executable conversion using injected SparkSession, no persisted output."""
    if engine_version != "0.1.0":
        raise ValueError("SHARED_WHEEL_EFFECTIVE_VERSION_MISMATCH")
    receipts = verify_source_objects(manifest_bytes, source_objects, context)
    patient_contract = load_pinned_contract(patient_contract_bytes, "patient")
    encounter_contract = load_pinned_contract(encounter_contract_bytes, "encounter")
    # Parser and converter are owned solely by the installed Shared Engine.
    objects = tuple(source_objects)
    parsed = parse_fhir_resources(objects, context)
    patient = normalize_fhir_patient(parsed, patient_contract, context)
    encounter = normalize_fhir_encounter(parsed, encounter_contract, context)
    reconcile = reconcile_patient_encounter(patient, encounter, context)
    p, e = reconcile.patient, reconcile.encounter
    findings = tuple((*p.quarantined, *p.rejected, *e.quarantined, *e.rejected))
    publication_id = _content_publication_id(context, p.accepted, e.accepted)
    return PreparedBatch(
        patient_df=accepted_dataframe(spark, p.accepted, patient_contract),
        encounter_df=accepted_dataframe(spark, e.accepted, encounter_contract),
        patient_count=len(p.accepted), encounter_count=len(e.accepted),
        findings=findings, source_batch_id=context.source_batch_id,
        processing_version=context.processing_version,
        publication_id=publication_id, manifest_sha256=context.manifest_sha256.lower(),
        source_receipts=receipts)


def validate_silver_readback(patient_df, encounter_df, batch: PreparedBatch,
                             context: BatchContext) -> None:
    """Validate independently read Spark/Delta outputs (real or synthetic DataFrames)."""
    from pyspark.sql import functions as F
    if patient_df.count() != batch.patient_count or encounter_df.count() != batch.encounter_count:
        raise ValueError("SILVER_READBACK_ROW_COUNT_MISMATCH")
    if patient_df.select("source_system", "source_record_id").distinct().count() != batch.patient_count:
        raise ValueError("SILVER_READBACK_PATIENT_PK_DUPLICATE")
    if encounter_df.select("source_system", "source_encounter_id").distinct().count() != batch.encounter_count:
        raise ValueError("SILVER_READBACK_ENCOUNTER_PK_DUPLICATE")
    for table, df in (("patient", patient_df), ("encounter", encounter_df)):
        invalid = df.filter(
            (F.col("source_batch_id") != context.source_batch_id)
            | (F.col("source_system") != context.namespaced_source_system)
            | (F.col("canonical_version") != "v1")
            | (F.col("adapter_version") != "0.1.0")
        ).count()
        if invalid:
            raise ValueError("SILVER_READBACK_VERSION_OR_NAMESPACE:" + table)
    pk = patient_df.select(
        "source_system", F.col("source_record_id").alias("source_person_id"))
    orphans = encounter_df.select(
        "source_system", "source_person_id").join(
        pk, ["source_system", "source_person_id"], "left_anti").count()
    if orphans:
        raise ValueError("SILVER_READBACK_PATIENT_ENCOUNTER_FK")


def _metrics(batch: PreparedBatch) -> dict[str, int]:
    return {"patient": batch.patient_count, "encounter": batch.encounter_count,
            "quarantine_or_reject": len(batch.findings), "source_objects": len(batch.source_receipts)}


def _paths(silver_root: str, batch: PreparedBatch) -> dict[str, str]:
    if not silver_root or ".." in silver_root or any(c in silver_root for c in "*?"):
        raise ValueError("UNVERIFIED_SILVER_ROOT")
    # Both records are staged under immutable source+processing scope.
    version_key = hashlib.sha256(batch.processing_version.encode("utf-8")).hexdigest()
    prefix = silver_root.rstrip("/") + "/source_batch=" + batch.source_batch_id + "/processing=" + version_key
    return {
        "patient": prefix + "/canonical_patient",
        "encounter": prefix + "/canonical_encounter",
        "bronze": prefix + "/bronze_source_receipt",
        "quarantine": prefix + "/quarantine",
        "approval": prefix + "/silver_approval",
    }


def _write_delta(df, path: str) -> None:
    """Native DataFrame/Delta I/O in Notebook only, never in Shared Engine."""
    df.write.format("delta").mode("errorifexists").save(path)


def execute_native_notebook(spark, *, context: BatchContext, manifest_bytes: bytes,
                            patient_contract_bytes: bytes, encounter_contract_bytes: bytes,
                            source_root: str, silver_root: str,
                            approved_records: Iterable[PublicationRecord] = (),
                            unknown_ack: bool = False,
                            retention_preflight_verified: bool = False,
                            write_authorized: bool = False) -> NotebookOutcome:
    """Future Fabric Notebook entrypoint; read/write/publish forbidden by default.

    Only a separately granted Fabric authorization may set both guards true.
    Offline CI MUST NOT call this with write_authorized=True.
    """
    empty = {"patient": 0, "encounter": 0, "quarantine_or_reject": 0, "source_objects": 0}
    if not write_authorized:
        return NotebookOutcome("HOLD_NO_CLOUD_WRITE_AUTHORIZATION", context.source_batch_id,
                               context.processing_version, None, empty, ("write not authorized",))
    if not retention_preflight_verified:
        return NotebookOutcome("HOLD_BRONZE_RETENTION_UNVERIFIED", context.source_batch_id,
                               context.processing_version, None, empty, ("Shortcut/Copy retention needs verified preflight",))
    # No source read until conflict, unknown ACK and replay were considered.
    _manifest_objects(manifest_bytes, context)
    decision = decide_replay(context, approved_records, unknown_ack=unknown_ack)
    if decision not in ("NEW", "SKIP"):
        return NotebookOutcome(decision, context.source_batch_id, context.processing_version,
                               None, empty, ("no blind retry; inspect published evidence read-only",))

    sources = read_source_objects_native(spark, source_root=source_root,
                                         manifest_bytes=manifest_bytes, context=context)
    batch = prepare_batch(spark, context=context, manifest_bytes=manifest_bytes,
                          source_objects=sources, patient_contract_bytes=patient_contract_bytes,
                          encounter_contract_bytes=encounter_contract_bytes)
    paths = _paths(silver_root, batch)
    if decision == "SKIP":
        # Even an approved ledger match is not enough without physical independent readback.
        try:
            pat = spark.read.format("delta").load(paths["patient"])
            enc = spark.read.format("delta").load(paths["encounter"])
            validate_silver_readback(pat, enc, batch, context)
            proof = spark.read.format("delta").load(paths["approval"]).collect()
            if len(proof) != 1 or proof[0].publication_id != batch.publication_id:
                raise ValueError("APPROVAL_PUBLISH_ID_MISMATCH")
        except Exception as exc:
            return NotebookOutcome("VERIFY_READONLY", batch.source_batch_id,
                                   batch.processing_version, None, _metrics(batch),
                                   ("existing Silver approval/readback not verified: " + type(exc).__name__,))
        return NotebookOutcome("SKIP_VERIFIED", batch.source_batch_id, batch.processing_version,
                               batch.publication_id, _metrics(batch), ())

    if batch.findings:
        # Rejected/Quarantined reason codes are retained without hiding partial source failures.
        evidence_rows = [
            (x.classification, x.reason, x.detail, x.resource_type,
             x.resource_id, x.source_file, batch.source_batch_id, batch.processing_version)
            for x in batch.findings
        ]
        try:
            quarantine_df = spark.createDataFrame(
                evidence_rows,
                "classification string, reason string, detail string, resource_type string, "
                "resource_id string, source_file string, source_batch_id string, processing_version string")
            _write_delta(quarantine_df, paths["quarantine"])
            if spark.read.format("delta").load(paths["quarantine"]).count() != len(evidence_rows):
                raise ValueError("QUARANTINE_READBACK_MISMATCH")
        except Exception as exc:
            return NotebookOutcome("VERIFY_READONLY", batch.source_batch_id,
                                   batch.processing_version, None, _metrics(batch),
                                   ("quarantine ACK/readback uncertain: " + type(exc).__name__,))
        return NotebookOutcome("HOLD_DQ", batch.source_batch_id, batch.processing_version,
                               None, _metrics(batch),
                               tuple(f"{x.classification}:{x.resource_type}/{x.resource_id}:{x.reason}:{x.detail}"
                                     for x in batch.findings))

    if not batch.acceptable:
        return NotebookOutcome("HOLD_EMPTY_ACCEPTED_PATIENT", batch.source_batch_id,
                               batch.processing_version, None, _metrics(batch), ("zero accepted Patient",))
    try:
        # Bronze raw bytes are independently verified from approved native source.
        # Receipt records original path/SHA/size; immutability requires separate live proof.
        bronze = spark.createDataFrame([
            (r["path"], r["sha256"], r["size_bytes"], batch.source_batch_id,
             batch.manifest_sha256, batch.processing_version)
            for r in batch.source_receipts
        ], "source_path string, source_sha256 string, source_size_bytes long, "
           "source_batch_id string, manifest_sha256 string, processing_version string")
        _write_delta(bronze, paths["bronze"])
        if spark.read.format("delta").load(paths["bronze"]).count() != len(batch.source_receipts):
            raise ValueError("BRONZE_RECEIPT_READBACK_MISMATCH")
        # Immutable versioned staging; NO append or overwrite on conflicts/unknown ACK.
        _write_delta(batch.patient_df, paths["patient"])
        _write_delta(batch.encounter_df, paths["encounter"])
        # Independent Delta reads, not in-memory transformed DataFrames.
        rp = spark.read.format("delta").load(paths["patient"])
        re = spark.read.format("delta").load(paths["encounter"])
        validate_silver_readback(rp, re, batch, context)
        approval = spark.createDataFrame([(
            batch.source_batch_id, batch.manifest_sha256, batch.processing_version,
            batch.publication_id, batch.patient_count, batch.encounter_count,
            "SILVER_APPROVED",
        )], "source_batch_id string, manifest_sha256 string, processing_version string, "
            "publication_id string, patient_count long, encounter_count long, status string")
        _write_delta(approval, paths["approval"])
        proof = spark.read.format("delta").load(paths["approval"]).collect()
        if len(proof) != 1 or proof[0].publication_id != batch.publication_id or proof[0].status != "SILVER_APPROVED":
            raise ValueError("SILVER_APPROVAL_READBACK_MISMATCH")
    except Exception as exc:
        # Some writes may have committed before an unknown ACK: never retry blindly.
        return NotebookOutcome("VERIFY_READONLY", batch.source_batch_id,
                               batch.processing_version, None, _metrics(batch),
                               ("partial Delta/approval ACK or readback unknown: " + type(exc).__name__,))
    return NotebookOutcome("SILVER_APPROVED", batch.source_batch_id,
                           batch.processing_version, batch.publication_id, _metrics(batch), ())

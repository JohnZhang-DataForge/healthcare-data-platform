# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "e67c42ee-5ab2-4bc8-a013-7bdf9741ef68",
# META       "default_lakehouse_name": "lh_omop_analytics",
# META       "default_lakehouse_workspace_id": "745ce03b-15b6-4870-b0e5-8c5750aa18dc",
# META       "known_lakehouses": [
# META         {
# META           "id": "e67c42ee-5ab2-4bc8-a013-7bdf9741ef68"
# META         }
# META       ]
# META     },
# META     "environment": {
# META       "environmentId": "ed219dd5-b5ec-8517-46ed-8da0d85a4218",
# META       "workspaceId": "00000000-0000-0000-0000-000000000000"
# META     }
# META   }
# META }

# CELL ********************

"""Git-native P2 FHIR Notebook; staged, not released for cloud writes."""
from __future__ import annotations

# Git-to-Fabric transport smoke marker (2026-11-01): no runtime/write authorization.
# Event-triggered sync smoke (2026-11-01): inert comment, no runtime behavior change.
from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
from typing import Iterable, Mapping, Any, Callable

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
    def _unique_json_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("DUPLICATE_MANIFEST_JSON_KEY")
            result[key] = value
        return result

    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"),
                              object_pairs_hook=_unique_json_pairs)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("INVALID_MANIFEST_JSON") from exc
    if not isinstance(manifest, dict):
        raise ValueError("INVALID_MANIFEST_SCHEMA")

    # The real Azure Publisher v1 emits blob_key (full container-relative URI),
    # not the old isolated P2 test shape with relative 'path' / source_system.
    # NEVER infer that source_manifest_sha256 is this delivered Manifest's hash:
    # it names the upstream Generator manifest, whereas context.manifest_sha256
    # has already been checked against the actual published Azure Manifest bytes.
    publisher_v1 = manifest.get("schema_version") == "healthcare-azure-blob-landing-manifest-v1"
    if "schema_version" in manifest and not publisher_v1:
        raise ValueError("UNSUPPORTED_LANDING_MANIFEST_VERSION")
    required_context = (("hospital_id", "feed_id", "request_id")
                        if publisher_v1 else
                        ("hospital_id", "feed_id", "source_system", "request_id"))
    if any(manifest.get(key) != getattr(context, key) for key in required_context):
        raise ValueError("MANIFEST_SOURCE_NAMESPACE_CONFLICT")
    if publisher_v1:
        required_keys = {
            "schema_version", "hospital_id", "feed_id", "request_id",
            "source_manifest_sha256", "target_format",
            "skipped_non_admissions", "objects",
        }
        upstream_sha = manifest.get("source_manifest_sha256")
        if (set(manifest) != required_keys or manifest.get("target_format") != "FHIR_R4"
                or context.source_version != "FHIR_R4"
                or type(manifest.get("skipped_non_admissions")) is not int
                or manifest["skipped_non_admissions"] != 0
                or not isinstance(upstream_sha, str) or len(upstream_sha) != 64
                or any(c not in "0123456789abcdef" for c in upstream_sha)):
            raise ValueError("PUBLISHER_FHIR_MANIFEST_CONTRACT_MISMATCH")
    objects = manifest.get("objects")
    if not isinstance(objects, list) or not objects or len(objects) > 5000:
        raise ValueError("EMPTY_OR_INVALID_MANIFEST_OBJECTS")
    seen: set[str] = set()
    result = []
    for entry in objects:
        if not isinstance(entry, dict):
            raise ValueError("INVALID_MANIFEST_OBJECT")
        if publisher_v1:
            if set(entry) != {
                    "blob_key", "sha256", "size_bytes", "source_event_id",
                    "etag", "version_id",
                } or entry.get("source_event_id") is not None:
                raise ValueError("PUBLISHER_FHIR_OBJECT_CONTRACT_MISMATCH")
            etag, version_id = entry.get("etag"), entry.get("version_id")
            if (not isinstance(etag, str) or not etag
                    or (version_id is not None and
                        (not isinstance(version_id, str) or not version_id))):
                raise ValueError("PUBLISHER_SOURCE_VERSION_OR_ETAG_INVALID")
        name = entry.get("blob_key" if publisher_v1 else "path")
        sha, size = entry.get("sha256"), entry.get("size_bytes")
        if not isinstance(name, str) or not name or name.startswith(("/", "\\")) or "\\" in name:
            raise ValueError("MANIFEST_OBJECT_PATH_INVALID")
        parts = PurePosixPath(name).parts
        if (str(PurePosixPath(name)) != name or ".." in parts or "." in parts
                or any(c in name for c in (":", "*", "?", "#", "%"))):
            raise ValueError("MANIFEST_OBJECT_PATH_INVALID")
        if publisher_v1:
            expected = ("clinical", "v1", context.hospital_id, context.feed_id,
                        context.request_id, "FHIR_R4", "fhir")
            if (len(parts) != 8 or tuple(parts[:7]) != expected
                    or not parts[-1].endswith(".json") or len(parts[-1]) > 160):
                raise ValueError("PUBLISHER_FHIR_BLOB_PREFIX_CONFLICT")
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
    # Run ID and processed_at change on safe replay; neither defines published
    # business content. Exclude these volatile provenance fields from identity.
    stable = lambda rows: [
        {k: v for k, v in row.items() if k not in ("processing_run_id", "processed_at")}
        for row in rows
    ]
    fingerprint = json.dumps({
        "source_batch": context.source_batch_id,
        "processing_version": context.processing_version,
        "patient": sorted(stable(patient_rows), key=lambda r: r["source_record_id"]),
        "encounter": sorted(stable(encounter_rows), key=lambda r: r["source_encounter_id"]),
    }, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(fingerprint).hexdigest()


def prepare_batch(spark, *, context: BatchContext, manifest_bytes: bytes,
                  source_objects: Iterable[SourceObject],
                  patient_contract_bytes: bytes, encounter_contract_bytes: bytes) -> PreparedBatch:
    """Offline-executable conversion using injected SparkSession, no persisted output."""
    # New G5 source-only readback may reproduce Canonical bytes with 0.1.13.
    # All historical G3/G4 entrypoints still independently pin GA 0.1.7.
    if engine_version not in ("0.1.7", "0.1.13"):
        raise ValueError("SHARED_WHEEL_EFFECTIVE_VERSION_MISMATCH")
    objects = tuple(source_objects)
    receipts = verify_source_objects(manifest_bytes, objects, context)
    patient_contract = load_pinned_contract(patient_contract_bytes, "patient")
    encounter_contract = load_pinned_contract(encounter_contract_bytes, "encounter")
    # Parser and converter are owned solely by the installed Shared Engine.
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



# G3: one request-scoped immutable-mode RAW BYTE snapshot + receipt,
# not a Silver publication or proof of Azure container-level WORM.
# The exact source bytes and provenance commit atomically into Lakehouse Delta.
_FHIR_SOURCE_LANDING_ROOT = "Files/fhir_landing"
_FHIR_BRONZE_SNAPSHOT_ROOT = "Files/bronze/fhir_r4"
_FHIR_SOURCE_HOSPITAL_ID = "atlanta-hospital-a"
_FHIR_SOURCE_FEED_ID = "atlanta-hospital-a-fhir-r4"
_FHIR_BRONZE_PROCESSING_VERSION = "fhir-bronze-raw-snapshot-v1:engine-0.1.1"


def _bronze_source_receipt_path(request: str) -> str:
    import re
    if not isinstance(request, str) or not re.fullmatch(r"atlanta-fhir-gh-[0-9]{8,14}", request):
        raise RuntimeError("HOLD_G3_UNAPPROVED_REQUEST_NAMESPACE")
    return (f"{_FHIR_BRONZE_SNAPSHOT_ROOT}/{_FHIR_SOURCE_HOSPITAL_ID}/{_FHIR_SOURCE_FEED_ID}/"
            f"{request}/bronze_source_snapshot")


def _expected_bronze_source_receipts(context: BatchContext, specs: tuple[dict, ...]) -> list[dict]:
    return [
        {"source_path": x["path"], "source_sha256": x["sha256"],
         "source_size_bytes": x["size_bytes"],
         "source_batch_id": context.source_batch_id,
         "manifest_sha256": context.manifest_sha256.lower(),
         "processing_version": context.processing_version,
         "request_id": context.request_id}
        for x in specs
    ]


def _delta_snapshot_exists(spark, path: str) -> bool:
    # False is not permission to overwrite a corrupt or partial directory:
    # errorifexists below remains the last line of defense.
    from delta.tables import DeltaTable
    return DeltaTable.isDeltaTable(spark, path)


def _verify_bronze_receipt_readback(spark, path: str, expected: list[dict]) -> bool:
    """Reopen durable Delta and verify every saved original byte, not memory."""
    rows = spark.read.format("delta").load(path).collect()
    actual = [r.asDict(recursive=True) for r in rows]
    if (len(actual) != len(expected)
            or len({r.get("source_path") for r in actual}) != len(actual)):
        return False
    by_path = {r["source_path"]: r for r in expected}
    import hashlib
    for row in actual:
        name = row.get("source_path")
        if name not in by_path:
            return False
        stored = row.get("source_payload")
        if not isinstance(stored, (bytes, bytearray, memoryview)):
            return False
        raw = bytes(stored)
        if (len(raw) != row.get("source_size_bytes")
                or hashlib.sha256(raw).hexdigest() != row.get("source_sha256")):
            return False
        advertised = by_path[name]
        metadata = {k: v for k, v in row.items() if k != "source_payload"}
        required = {k: v for k, v in advertised.items() if k != "source_payload"}
        if metadata != required:
            return False
        if ("source_payload" in advertised
                and raw != bytes(advertised["source_payload"])):
            return False
    return True


def verify_fhir_g3_bronze(spark, *, request: str, manifest_sha: str,
                          mode: str, allow_write: bool, retention_ok: bool,
                          manifest_override: str, source_override: str,
                          target_override: str, strategy: str) -> NotebookOutcome:
    """G3 path-pinned raw FHIR Delta snapshot, replay and separate readback.

    The external Azure container did NOT show locked WORM/Legal Hold (G0 HOLD).
    The approved dev alternative *atomically stores original verified bytes*
    and all receipt metadata in immutable-mode Delta with errorifexists.
    Retention preflight means this explicit snapshot strategy was authorized,
    NOT that Azure WORM is enabled. Real independent stored byte readback
    is required before release. Unknown ACK always needs read-only recovery.
    """
    if (mode not in ("BRONZE_RECEIPT", "BRONZE_READBACK_ONLY")
            or strategy != "DELTA_RAW_SNAPSHOT_V1"
            or any(x != "" for x in (manifest_override, source_override, target_override))):
        raise RuntimeError("HOLD_G3_UNSAFE_PATH_OR_MODE")
    path = _bronze_source_receipt_path(request)
    if (mode == "BRONZE_RECEIPT" and
            (allow_write is not True or retention_ok is not True)):
        raise RuntimeError("HOLD_G3_WRITE_OR_RETENTION_NOT_VERIFIED")
    if (mode == "BRONZE_READBACK_ONLY" and
            (allow_write is not False or retention_ok is not False)):
        raise RuntimeError("HOLD_G3_READBACK_FLAGS_NOT_READONLY")
    if (engine_version != "0.1.7" or not isinstance(manifest_sha, str)
            or len(manifest_sha) != 64 or
            any(c not in "0123456789abcdef" for c in manifest_sha)):
        raise RuntimeError("HOLD_G3_ENGINE_OR_MANIFEST_PIN_INVALID")

    from datetime import date, datetime, timezone
    context = BatchContext(
        hospital_id=_FHIR_SOURCE_HOSPITAL_ID, feed_id=_FHIR_SOURCE_FEED_ID,
        source_system="synthea-fhir", request_id=request,
        manifest_sha256=manifest_sha, processing_version=_FHIR_BRONZE_PROCESSING_VERSION,
        processing_run_id="g3:" + request, source_version="FHIR_R4",
        source_ingest_date=date(2026, 11, 2),
        processed_at=datetime.now(timezone.utc))
    root = (f"{_FHIR_SOURCE_LANDING_ROOT}/clinical/v1/{_FHIR_SOURCE_HOSPITAL_ID}/"
            f"{_FHIR_SOURCE_FEED_ID}/{request}/landing-manifest.json")
    manifest_rows = spark.read.format("binaryFile").load(root).select("content").collect()
    if len(manifest_rows) != 1:
        raise RuntimeError("HOLD_G3_MANIFEST_NOT_ONE_FILE")
    raw = bytes(manifest_rows[0].content)
    specs = _manifest_objects(raw, context)   # validates delivered manifest SHA
    if not 5 <= len(specs) <= 10:
        raise RuntimeError("HOLD_G3_NOT_A_5_TO_10_OBJECT_BATCH")
    expected = _expected_bronze_source_receipts(context, specs)
    metrics = {"patient": 0, "encounter": 0, "quarantine_or_reject": 0,
               "source_objects": len(specs)}
    try:
        exists = _delta_snapshot_exists(spark, path)
    except Exception:
        return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                               context.processing_version, None, metrics,
                               ("Delta existence check uncertain",))
    if exists:
        try:
            correct = _verify_bronze_receipt_readback(spark, path, expected)
        except Exception:
            return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                                   context.processing_version, None, metrics,
                                   ("existing receipt unreadable",))
        return NotebookOutcome(
            "BRONZE_SKIP_VERIFIED" if correct else "HOLD_REQUEST_DRIFT",
            context.source_batch_id, context.processing_version, None, metrics,
            () if correct else ("request has different persisted source/version",))
    if mode == "BRONZE_READBACK_ONLY":
        return NotebookOutcome("HOLD_BRONZE_NOT_FOUND", context.source_batch_id,
                               context.processing_version, None, metrics, ())
    try:
        # This reads each original source object and verifies exact object SHA/size.
        sources = read_source_objects_native(
            spark, source_root=_FHIR_SOURCE_LANDING_ROOT, manifest_bytes=raw, context=context)
        verified = verify_source_objects(raw, sources, context)
        if verified != tuple(specs):
            raise ValueError("G3_SOURCE_RECEIPTS_CHANGED")
        by_path = {obj.source_file: obj.payload for obj in sources}
        if set(by_path) != {r["source_path"] for r in expected}:
            raise ValueError("G3_RAW_SNAPSHOT_SOURCE_PATHS_CHANGED")
        complete = [{**row, "source_payload": by_path[row["source_path"]]}
                    for row in expected]
        columns = ("source_path string, source_sha256 string, source_size_bytes long, "
                   "source_batch_id string, manifest_sha256 string, "
                   "processing_version string, request_id string, source_payload binary")
        values = [tuple(row[k] for k in (
            "source_path", "source_sha256", "source_size_bytes", "source_batch_id",
            "manifest_sha256", "processing_version", "request_id", "source_payload"))
            for row in complete]
        bronze_df = spark.createDataFrame(values, columns)
        _write_delta(bronze_df, path)  # one atomic raw+receipt Delta commit, errorifexists
        if not _verify_bronze_receipt_readback(spark, path, complete):
            raise ValueError("G3_POSTWRITE_RAW_BYTE_READBACK_MISMATCH")
    except Exception:
        # A write may have committed before a timeout or exception.
        # A new write is forbidden until an independent READBACK_ONLY Job.
        return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                               context.processing_version, None, metrics,
                               ("source/write ACK or Delta readback uncertain",))
    return NotebookOutcome("BRONZE_WRITTEN", context.source_batch_id,
                           context.processing_version, None, metrics, ())



# G4: reuse Shared Engine's canonical transform, existing G3 raw-byte snapshot
# verification and native Delta writing. Only this publication coordinator is new.
_G4_PROCESSING = "fhir-silver-canonical-v1:engine-0.1.1"
_FHIR_SILVER_PUBLICATION_ROOT = "Files/silver/fhir_r4"


def _silver_publication_paths(request: str) -> dict[str, str]:
    _bronze_source_receipt_path(request)  # namespace/path traversal validation
    digest = hashlib.sha256(_G4_PROCESSING.encode("utf-8")).hexdigest()
    prefix = (f"{_FHIR_SILVER_PUBLICATION_ROOT}/{_FHIR_SOURCE_HOSPITAL_ID}/{_FHIR_SOURCE_FEED_ID}/"
              f"{request}/processing={digest}")
    return {"bronze": _bronze_source_receipt_path(request),
            "patient": prefix + "/canonical_patient",
            "encounter": prefix + "/canonical_encounter",
            "approval": prefix + "/silver_approval",
            "quarantine": prefix + "/quarantine"}


def _canonical_silver_approval_row(
        batch: PreparedBatch, patient_contract_bytes: bytes,
        encounter_contract_bytes: bytes, *,
        source_preservation_strategy: str) -> dict:
    """One approval schema for FHIR and future verified HL7 source adapters."""
    if source_preservation_strategy not in (
            "DELTA_RAW_SNAPSHOT_V1", "VERIFIED_HL7_CANDIDATE_V1"):
        raise ValueError("HOLD_UNREVIEWED_SILVER_SOURCE_PRESERVATION")
    return {
        "source_batch_id": batch.source_batch_id,
        "manifest_sha256": batch.manifest_sha256,
        "processing_version": batch.processing_version,
        "publication_id": batch.publication_id,
        "patient_count": batch.patient_count,
        "encounter_count": batch.encounter_count,
        "quarantine_count": 0,
        "patient_contract_sha256": hashlib.sha256(patient_contract_bytes).hexdigest(),
        "encounter_contract_sha256": hashlib.sha256(encounter_contract_bytes).hexdigest(),
        "source_preservation_strategy": source_preservation_strategy,
        "status": "SILVER_APPROVED",
    }


def _silver_approval_row(context: BatchContext, batch: PreparedBatch,
                     patient_contract_bytes: bytes,
                     encounter_contract_bytes: bytes) -> dict:
    """Retain the exact historical FHIR G4 approval payload."""
    return _canonical_silver_approval_row(
        batch, patient_contract_bytes, encounter_contract_bytes,
        source_preservation_strategy="DELTA_RAW_SNAPSHOT_V1")


def _snapshot_silver_source_objects(spark, path: str,
                                expected: list[dict],
                                context: BatchContext) -> tuple[SourceObject, ...]:
    if not _verify_bronze_receipt_readback(spark, path, expected):
        raise ValueError("G4_BRONZE_SOURCE_BYTES_OR_RECEIPTS_CHANGED")
    # This is a NEW physical Delta scan, not reuse of the source input DataFrame.
    rows = spark.read.format("delta").load(path).collect()
    return tuple(SourceObject(
        source_file=r.source_path, payload=bytes(r.source_payload),
        sha256=r.source_sha256, size_bytes=r.source_size_bytes,
        hospital_id=context.hospital_id, feed_id=context.feed_id,
        source_system=context.source_system) for r in rows)


def _validate_silver_delta_contents(expected, actual, name: str) -> None:
    """Bidirectional canonical content check, ignoring volatile run timestamps.

    Replay transforms run at a different time and must not falsify content
    drift just because processed_at/processing_run_id changed.
    """
    if set(expected.columns) != set(actual.columns):
        raise ValueError("G4_DELTA_CANONICAL_SCHEMA_CHANGED:" + name)
    columns = [c for c in expected.columns
               if c not in ("processed_at", "processing_run_id")]
    if (expected.select(*columns).exceptAll(actual.select(*columns)).count()
            or actual.select(*columns).exceptAll(expected.select(*columns)).count()):
        raise ValueError("G4_DELTA_CANONICAL_CONTENT_MISMATCH:" + name)


def _write_verified_canonical_silver(
        spark, *, context: BatchContext, batch: PreparedBatch,
        paths: dict[str, str], patient_contract_bytes: bytes,
        encounter_contract_bytes: bytes, source_preservation_strategy: str,
        validate_persisted_canonical) -> dict:
    """Single create-only Patient/Encounter/Approval-LAST Delta writer.

    This is an internal physical I/O primitive, NOT a source authorization
    endpoint. Callers must independently pin/read back immutable source,
    establish exclusive publication ownership and DQ-pass before invoking.
    FHIR G4 retains its source-specific guards and replay recovery; HL7 has
    no cloud dispatcher/authorization in this source-only change.
    """
    if (not isinstance(context, BatchContext)
            or not isinstance(batch, PreparedBatch)
            or batch.findings or batch.patient_count < 1
            or batch.encounter_count < 1
            or batch.source_batch_id != context.source_batch_id
            or batch.processing_version != context.processing_version
            or batch.manifest_sha256 != context.manifest_sha256
            or context.canonical_version != "v1"):
        raise ValueError("HOLD_SILVER_UNVERIFIED_BATCH_OR_DQ")
    if (not isinstance(batch.publication_id, str)
            or len(batch.publication_id) != 64
            or any(c not in "0123456789abcdef"
                   for c in batch.publication_id)):
        raise ValueError("HOLD_SILVER_PUBLICATION_ID")
    # Pin original contract bytes before the first physical mutation.
    load_pinned_contract(patient_contract_bytes, "patient")
    load_pinned_contract(encounter_contract_bytes, "encounter")
    if not callable(validate_persisted_canonical):
        raise ValueError("HOLD_SILVER_MISSING_INDEPENDENT_DQ")
    required = ("patient", "encounter", "approval")
    if (not isinstance(paths, dict) or
            any(not isinstance(paths.get(k), str) for k in required)):
        raise ValueError("HOLD_SILVER_TARGET_PATHS")
    prefix = paths["patient"].removesuffix("/canonical_patient")
    if (not prefix or paths["patient"] != prefix + "/canonical_patient"
            or paths["encounter"] != prefix + "/canonical_encounter"
            or paths["approval"] != prefix + "/silver_approval"
            or any(part in ("", ".", "..") for part in prefix.split("/"))
            or any(c in prefix for c in "*?\\")
            or not (prefix.startswith("Files/silver/")
                    or prefix.startswith("file:/"))):
        raise ValueError("HOLD_SILVER_TARGET_NAMESPACE")
    # Recheck immediately before write. A partial/unknown ACK must never
    # enter an append/overwrite or generate an Approval on retry.
    if any(_delta_snapshot_exists(spark, paths[k]) for k in required):
        raise ValueError("HOLD_SILVER_EXISTING_OR_PARTIAL_DELTA")
    approval_row = _canonical_silver_approval_row(
        batch, patient_contract_bytes, encounter_contract_bytes,
        source_preservation_strategy=source_preservation_strategy)
    _write_delta(batch.patient_df, paths["patient"])
    _write_delta(batch.encounter_df, paths["encounter"])
    p = spark.read.format("delta").load(paths["patient"])
    e = spark.read.format("delta").load(paths["encounter"])
    validate_persisted_canonical(p, e, batch, context)
    _validate_silver_delta_contents(batch.patient_df, p, "patient")
    _validate_silver_delta_contents(batch.encounter_df, e, "encounter")
    fields = ("source_batch_id string, manifest_sha256 string, "
              "processing_version string, publication_id string, "
              "patient_count long, encounter_count long, quarantine_count long, "
              "patient_contract_sha256 string, encounter_contract_sha256 string, "
              "source_preservation_strategy string, status string")
    keys = [x.split()[0] for x in fields.split(", ")]
    approval = spark.createDataFrame(
        [tuple(approval_row[k] for k in keys)], fields)
    _write_delta(approval, paths["approval"])  # approval fence LAST
    persisted = spark.read.format("delta").load(paths["approval"]).collect()
    if (len(persisted) != 1 or
            persisted[0].asDict(recursive=True) != approval_row):
        raise ValueError("HOLD_SILVER_APPROVAL_INDEPENDENT_READBACK")
    return approval_row


def prepare_hl7_candidate_bundle_for_silver(
        spark, *, bundle: Mapping[str, bytes], bundle_manifest_sha256: str,
        context: BatchContext, patient_contract_bytes: bytes,
        encounter_contract_bytes: bytes,
        source_evidence_verified: bool = False) -> PreparedBatch:
    """Offline-verifiable HL7 Candidate transport admission, NO Silver write.

    The independent trusted caller supplies the manifest SHA out of band,
    proves original Raw/Manifest, retention, authorized transport and exclusive
    Writer window separately. This function only checks supplied bytes; there
    is deliberately NO HL7 Notebook run_mode or cloud transport in this PR.
    """
    from datetime import date, datetime, timezone
    from decimal import Decimal, InvalidOperation
    import re
    from healthcare_data_engine.canonical.validation import validate_row
    from healthcare_data_engine.quality.result import TransformResult

    schema = "healthcare-hl7-canonical-transport-v1"
    files = {"canonical_patient.json", "canonical_encounter.json",
             "candidate_manifest.json"}
    if (source_evidence_verified is not True
            or not isinstance(bundle, Mapping) or set(bundle) != files
            or not isinstance(bundle_manifest_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", bundle_manifest_sha256)
            or not isinstance(context, BatchContext)
            or (context.hospital_id, context.feed_id, context.source_system) != (
                "johns-creek-hospital-b", "johns-creek-hospital-b-hl7-v2",
                "johns-creek-hl7")
            or context.canonical_version != "v1"
            or context.adapter_version != "1.3.5"
            or context.source_version != "HL7v2.5.1"):
        raise ValueError("HOLD_HL7_BUNDLE_UNREVIEWED_SOURCE_OR_APPROVAL")
    for name in files:
        value = bundle[name]
        limit = 16384 if name == "candidate_manifest.json" else 16 * 1024 * 1024
        if not isinstance(value, bytes) or len(value) > limit or not value:
            raise ValueError("HOLD_HL7_BUNDLE_BYTES")
    if hashlib.sha256(bundle["candidate_manifest.json"]).hexdigest() != bundle_manifest_sha256:
        raise ValueError("HOLD_HL7_BUNDLE_MANIFEST_PIN_CHANGED")

    def load_exact(raw):
        try:
            parsed = json.loads(raw.decode("utf-8"))
            encoded = json.dumps(parsed, sort_keys=True, ensure_ascii=True,
                                 separators=(",", ":"), allow_nan=False).encode()
            if encoded != raw:
                raise ValueError("noncanonical")
            return parsed
        except (ValueError, UnicodeError, TypeError, OverflowError) as exc:
            raise ValueError("HOLD_HL7_BUNDLE_NONCANONICAL_JSON") from exc

    manifest = load_exact(bundle["candidate_manifest.json"])
    names = {
        "schema", "hospital_id", "feed_id", "source_system",
        "request_id", "source_batch_id", "source_manifest_sha256",
        "processing_version", "source_version", "adapter_version",
        "canonical_version", "patient_contract_sha256",
        "encounter_contract_sha256", "publication_id", "entities", "status"}
    if not isinstance(manifest, dict) or set(manifest) != names:
        raise ValueError("HOLD_HL7_BUNDLE_MANIFEST_FIELDS")
    expected = {
        "schema": schema, "hospital_id": context.hospital_id,
        "feed_id": context.feed_id, "source_system": context.source_system,
        "request_id": context.request_id,
        "source_batch_id": context.source_batch_id,
        "source_manifest_sha256": context.manifest_sha256.lower(),
        "processing_version": context.processing_version,
        "source_version": context.source_version,
        "adapter_version": context.adapter_version,
        "canonical_version": "v1",
        "patient_contract_sha256": hashlib.sha256(patient_contract_bytes).hexdigest(),
        "encounter_contract_sha256": hashlib.sha256(encounter_contract_bytes).hexdigest(),
        "status": "CANDIDATE_ONLY_NOT_SILVER_APPROVED",
    }
    if any(manifest[k] != val for k, val in expected.items()):
        raise ValueError("HOLD_HL7_BUNDLE_CONTEXT_CONTRACT_DRIFT")
    if (not isinstance(manifest["entities"], dict)
            or set(manifest["entities"]) != {"patient", "encounter"}):
        raise ValueError("HOLD_HL7_BUNDLE_ENTITY_SET")
    contracts = {
        "patient": load_pinned_contract(patient_contract_bytes, "patient"),
        "encounter": load_pinned_contract(encounter_contract_bytes, "encounter"),
    }
    provenance_prefix = (f"clinical/v1/{context.hospital_id}/{context.feed_id}/"
                         f"{context.request_id}/HL7_V2/hl7/")
    accepted = {}
    for entity, key in (("patient", "source_record_id"),
                        ("encounter", "source_encounter_id")):
        filename = "canonical_" + entity + ".json"
        data = bundle[filename]
        descriptor = manifest["entities"][entity]
        if (not isinstance(descriptor, dict)
                or set(descriptor) != {"file", "sha256", "bytes", "rows"}
                or descriptor["file"] != filename
                or descriptor["sha256"] != hashlib.sha256(data).hexdigest()
                or type(descriptor["bytes"]) is not int
                or descriptor["bytes"] != len(data)
                or type(descriptor["rows"]) is not int
                or not 1 <= descriptor["rows"] <= 50000):
            raise ValueError("HOLD_HL7_BUNDLE_ENTITY_HASH_OR_COUNTS")
        payload = load_exact(data)
        if (not isinstance(payload, dict)
                or set(payload) != {"schema", "entity", "rows"}
                or payload["schema"] != schema or payload["entity"] != entity
                or not isinstance(payload["rows"], list)
                or len(payload["rows"]) != descriptor["rows"]):
            raise ValueError("HOLD_HL7_BUNDLE_ENTITY_PAYLOAD")
        records = []
        field_types = {f["name"]: f["type"] for f in contracts[entity]["fields"]}
        for original in payload["rows"]:
            if not isinstance(original, dict) or set(original) != set(field_types):
                raise ValueError("HOLD_HL7_BUNDLE_ROW_FIELDS")
            row = dict(original)
            for col, kind in field_types.items():
                value = row[col]
                if value is None:
                    continue
                if kind == "date":
                    if not isinstance(value, str):
                        raise ValueError("HOLD_HL7_BUNDLE_DATE")
                    try:
                        row[col] = date.fromisoformat(value)
                        if row[col].isoformat() != value:
                            raise ValueError("noncanonical date")
                    except ValueError as exc:
                        raise ValueError("HOLD_HL7_BUNDLE_DATE") from exc
                elif kind == "timestamp":
                    if (not isinstance(value, str) or
                            not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", value)):
                        raise ValueError("HOLD_HL7_BUNDLE_TIMESTAMP")
                    try:
                        row[col] = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                    except ValueError as exc:
                        raise ValueError("HOLD_HL7_BUNDLE_TIMESTAMP") from exc
                elif kind.startswith("decimal("):
                    if not isinstance(value, str):
                        raise ValueError("HOLD_HL7_BUNDLE_DECIMAL")
                    try:
                        number = Decimal(value)
                        if not number.is_finite() or str(number) != value:
                            raise ValueError("noncanonical decimal")
                        row[col] = number
                    except (InvalidOperation, ValueError) as exc:
                        raise ValueError("HOLD_HL7_BUNDLE_DECIMAL") from exc
            if (validate_row(row, contracts[entity])
                    or row["source_system"] != context.namespaced_source_system
                    or row["source_batch_id"] != context.source_batch_id
                    or row["source_version"] != context.source_version
                    or row["adapter_name"] != "hl7apy"
                    or row["adapter_version"] != context.adapter_version
                    or row["canonical_version"] != "v1"
                    or row["source_ingest_date"] != context.source_ingest_date
                    or row["processing_run_id"] != context.processing_run_id
                    or row["processed_at"] != context.processed_at.astimezone(timezone.utc)
                    or not row["source_file"].startswith(provenance_prefix)
                    or not re.fullmatch(r"[A-Za-z0-9-]+-(A01|A03)\.hl7",
                                        row["source_file"][len(provenance_prefix):])
                    or not re.fullmatch(r"[0-9a-f]{64}", row["source_file_sha256"])
                    or type(row["source_file_size_bytes"]) is not int
                    or row["source_file_size_bytes"] < 1):
                raise ValueError("HOLD_HL7_BUNDLE_ROW_PROVENANCE_OR_DQ")
            records.append(row)
        if [r[key] for r in records] != sorted(r[key] for r in records):
            raise ValueError("HOLD_HL7_BUNDLE_ORDER_DRIFT")
        accepted[entity] = tuple(records)
    identity = hashlib.sha256(json.dumps({
        "source_batch_id": context.source_batch_id,
        "processing_version": context.processing_version,
        "patient_sha256": manifest["entities"]["patient"]["sha256"],
        "encounter_sha256": manifest["entities"]["encounter"]["sha256"],
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    if manifest["publication_id"] != identity:
        raise ValueError("HOLD_HL7_BUNDLE_PUBLICATION_DRIFT")
    reconciled = reconcile_patient_encounter(
        TransformResult(accepted["patient"], (), ()),
        TransformResult(accepted["encounter"], (), ()), context)
    metrics = reconciled.metrics
    if any(metrics[k] for k in (
            "patient_rejected", "encounter_rejected",
            "patient_quarantined", "encounter_quarantined")):
        raise ValueError("HOLD_HL7_BUNDLE_SHARED_PK_FK")
    return PreparedBatch(
        patient_df=accepted_dataframe(spark, reconciled.patient.accepted,
                                      contracts["patient"]),
        encounter_df=accepted_dataframe(spark, reconciled.encounter.accepted,
                                        contracts["encounter"]),
        patient_count=metrics["patient_accepted"],
        encounter_count=metrics["encounter_accepted"],
        findings=(), source_batch_id=context.source_batch_id,
        processing_version=context.processing_version,
        publication_id=identity,
        manifest_sha256=context.manifest_sha256.lower(),
        source_receipts=())


def _verify_silver_publication_readback(spark, paths: dict[str, str],
                                    context: BatchContext,
                                    manifest_bytes: bytes,
                                    expected_receipts: list[dict],
                                    patient_contract_bytes: bytes,
                                    encounter_contract_bytes: bytes) -> PreparedBatch:
    sources = _snapshot_silver_source_objects(
        spark, paths["bronze"], expected_receipts, context)
    # Shared Engine owns ALL canonical conversion, no duplicate ETL engine.
    batch = prepare_batch(
        spark, context=context, manifest_bytes=manifest_bytes,
        source_objects=sources, patient_contract_bytes=patient_contract_bytes,
        encounter_contract_bytes=encounter_contract_bytes)
    if (batch.findings or batch.patient_count != 100
            or batch.encounter_count < 100):
        raise ValueError("G4_SILVER_RECOMPUTED_DQ_HOLD")
    patient = spark.read.format("delta").load(paths["patient"])
    encounter = spark.read.format("delta").load(paths["encounter"])
    validate_silver_readback(patient, encounter, batch, context)
    _validate_silver_delta_contents(batch.patient_df, patient, "patient")
    _validate_silver_delta_contents(batch.encounter_df, encounter, "encounter")
    approvals = spark.read.format("delta").load(paths["approval"]).collect()
    expected_approval = _silver_approval_row(
        context, batch, patient_contract_bytes, encounter_contract_bytes)
    if (len(approvals) != 1 or
            approvals[0].asDict(recursive=True) != expected_approval):
        raise ValueError("G4_SILVER_APPROVAL_FENCE_INVALID")
    return batch



# G4.c physical Delta rejection of isolated synthetic missing-DOB source.
# Transform/conversion remains wholly inside Shared Engine 0.1.7.
def verify_fhir_g4_dq_negative(spark, *, request: str, manifest_sha: str,
                               derivation_sha: str, mode: str,
                               allow_write: bool, retention_ok: bool,
                               strategy: str, manifest_override: str,
                               source_override: str, target_override: str,
                               patient_contract_json: str,
                               encounter_contract_json: str) -> NotebookOutcome:
    if (mode not in ("SILVER_DQ_QUARANTINE_WRITE", "SILVER_DQ_READBACK_ONLY")
            or strategy != "DELTA_RAW_SNAPSHOT_V1"
            or request in ("atlanta-fhir-gh-41552666929",
                           "atlanta-fhir-gh-41539769718")
            or any(x != "" for x in (
                manifest_override, source_override, target_override))):
        raise RuntimeError("HOLD_G4_DQ_MODE_NAMESPACE_OR_OVERRIDE")
    paths = _silver_publication_paths(request)
    writable = mode == "SILVER_DQ_QUARANTINE_WRITE"
    if (allow_write is not writable or retention_ok is not writable
            or engine_version != "0.1.7"
            or not isinstance(manifest_sha, str)
            or not isinstance(derivation_sha, str)
            or len(manifest_sha) != 64 or len(derivation_sha) != 64
            or any(c not in "0123456789abcdef"
                   for c in manifest_sha + derivation_sha)):
        raise RuntimeError("HOLD_G4_DQ_SHA_AND_BOOLEAN_GATES")
    if (not isinstance(patient_contract_json, str)
            or not isinstance(encounter_contract_json, str)
            or not 0 < len(patient_contract_json) <= 5000
            or not 0 < len(encounter_contract_json) <= 5000):
        raise RuntimeError("HOLD_G4_DQ_CONTRACT_PARAMETERS")
    pb, eb = patient_contract_json.encode(), encounter_contract_json.encode()
    load_pinned_contract(pb, "patient")
    load_pinned_contract(eb, "encounter")
    from datetime import datetime, date, timezone
    context = BatchContext(
        hospital_id=_FHIR_SOURCE_HOSPITAL_ID, feed_id=_FHIR_SOURCE_FEED_ID,
        source_system="synthea-fhir", request_id=request,
        manifest_sha256=manifest_sha, processing_version=_G4_PROCESSING,
        processing_run_id="g4:" + request, source_version="FHIR_R4",
        source_ingest_date=date(2026, 11, 2),
        processed_at=datetime.now(timezone.utc))
    source_file = (f"{_FHIR_SOURCE_LANDING_ROOT}/clinical/v1/{_FHIR_SOURCE_HOSPITAL_ID}/"
                   f"{_FHIR_SOURCE_FEED_ID}/{request}/landing-manifest.json")
    raw = spark.read.format("binaryFile").load(
        source_file).select("content").collect()
    if len(raw) != 1:
        raise RuntimeError("HOLD_G4_DQ_SOURCE_MANIFEST_MISSING")
    manifest_bytes = bytes(raw[0].content)
    specs = _manifest_objects(manifest_bytes, context)
    if len(specs) != 100 or json.loads(
            manifest_bytes).get("source_manifest_sha256") != derivation_sha:
        raise RuntimeError("HOLD_G4_DQ_100_SOURCE_OR_RECIPE_SHA")
    zeros = {"patient": 0, "encounter": 0, "quarantine_or_reject": 0,
             "source_objects": 100}
    try:
        exists = {key: _delta_snapshot_exists(spark, value)
                  for key, value in paths.items()}
    except Exception:
        return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                               context.processing_version, None, zeros,
                               ("DQ Delta state uncertain",))
    if any(exists[k] for k in ("bronze", "patient", "encounter", "approval")):
        return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                               context.processing_version, None, zeros,
                               ("unapproved DQ request has partial Silver data",))
    if not exists["quarantine"] and not writable:
        return NotebookOutcome("HOLD_DQ_NOT_PERSISTED",
                               context.source_batch_id, context.processing_version,
                               None, zeros, ())
    if not exists["quarantine"]:
        # Invoke EXISTING native Silver writer, not a second converter/writer.
        # That writer persists only Quarantine when any DQ finding exists.
        result = verify_fhir_g4_silver(
            spark, request=request, manifest_sha=manifest_sha,
            mode="SILVER_WRITE", allow_write=True, retention_ok=True,
            strategy=strategy, manifest_override="", source_override="",
            target_override="", patient_contract_json=patient_contract_json,
            encounter_contract_json=encounter_contract_json)
        if result.status != "HOLD_DQ":
            return NotebookOutcome("HOLD_DQ_NEGATIVE_NOT_PROVEN",
                                   context.source_batch_id, context.processing_version,
                                   None, result.metrics, ())
    try:
        # Separate Spark reads and independent Shared Engine recomputation.
        sources = read_source_objects_native(
            spark, source_root=_FHIR_SOURCE_LANDING_ROOT,
            manifest_bytes=manifest_bytes, context=context)
        batch = prepare_batch(
            spark, context=context, manifest_bytes=manifest_bytes,
            source_objects=sources, patient_contract_bytes=pb,
            encounter_contract_bytes=eb)
        found = [f for f in batch.findings
                 if f.reason == "PATIENT_CANONICAL_V1_INCOMPATIBLE"
                 and f.resource_type == "Patient"
                 and "FHIR_DATE_REQUIRED" in f.detail]
        if (batch.patient_count != 99 or len(found) != 1
                or not batch.findings or len(batch.source_receipts) != 100):
            raise ValueError("G4_DQ_MISSING_ONE_BIRTHDATE_NOT_CONFIRMED")
        cols = ("classification", "reason", "detail", "resource_type",
                "resource_id", "source_file", "source_batch_id",
                "processing_version")
        expected = sorted((
            x.classification, x.reason, x.detail, x.resource_type,
            x.resource_id, x.source_file, batch.source_batch_id,
            batch.processing_version) for x in batch.findings)
        rows = spark.read.format("delta").load(
            paths["quarantine"]).select(*cols).collect()
        actual = sorted(tuple(getattr(row, k) for k in cols) for row in rows)
        if actual != expected:
            raise ValueError("G4_DQ_QUARANTINE_PHYSICAL_ROWS_OR_REASON_CHANGED")
        for k in ("bronze", "patient", "encounter", "approval"):
            if _delta_snapshot_exists(spark, paths[k]):
                raise ValueError("G4_DQ_FORBIDDEN_APPROVAL_OR_SILVER_EXISTS")
    except Exception:
        return NotebookOutcome("VERIFY_READONLY",
                               context.source_batch_id,
                               context.processing_version, None, zeros,
                               ("stored Quarantine mismatch or Approval exists",))
    status = ("DQ_QUARANTINED" if writable and not exists["quarantine"]
              else "DQ_SKIP_VERIFIED" if writable
              else "DQ_READBACK_VERIFIED")
    return NotebookOutcome(status, batch.source_batch_id,
                           batch.processing_version, None, _metrics(batch), ())



def verify_fhir_g4_silver(spark, *, request: str, manifest_sha: str,
                          mode: str, allow_write: bool, retention_ok: bool,
                          strategy: str, manifest_override: str,
                          source_override: str, target_override: str,
                          patient_contract_json: str,
                          encounter_contract_json: str) -> NotebookOutcome:
    """100-object real Silver staged Delta publisher, approval last, never overwrite.

    Existing raw Delta snapshot, Shared Engine and Canonical validators are
    reused. Azure Blob's WORM HOLD is NOT bypassed or relabeled compliance.
    """
    if (mode not in ("SILVER_WRITE", "SILVER_READBACK_ONLY")
            or strategy != "DELTA_RAW_SNAPSHOT_V1"
            or any(x != "" for x in (
                manifest_override, source_override, target_override))):
        raise RuntimeError("HOLD_G4_MODE_STRATEGY_OR_ROOT_NOT_AUTHORIZED")
    paths = _silver_publication_paths(request)
    if ((mode == "SILVER_WRITE" and
         (allow_write is not True or retention_ok is not True))
            or (mode == "SILVER_READBACK_ONLY" and
                (allow_write is not False or retention_ok is not False))):
        raise RuntimeError("HOLD_G4_BOOLEAN_WRITE_GATES")
    if (engine_version != "0.1.7" or not isinstance(manifest_sha, str)
            or len(manifest_sha) != 64 or
            any(c not in "0123456789abcdef" for c in manifest_sha)):
        raise RuntimeError("HOLD_G4_ENGINE_OR_MANIFEST_PIN")
    if (not isinstance(patient_contract_json, str)
            or not isinstance(encounter_contract_json, str)
            or not 0 < len(patient_contract_json) <= 5000
            or not 0 < len(encounter_contract_json) <= 5000):
        raise RuntimeError("HOLD_G4_CONTRACT_INPUT_INVALID")
    pb = patient_contract_json.encode("utf-8")
    eb = encounter_contract_json.encode("utf-8")
    load_pinned_contract(pb, "patient")
    load_pinned_contract(eb, "encounter")  # verify both RAW SHA pins before source read
    from datetime import date, datetime, timezone
    context = BatchContext(
        hospital_id=_FHIR_SOURCE_HOSPITAL_ID, feed_id=_FHIR_SOURCE_FEED_ID,
        source_system="synthea-fhir", request_id=request,
        manifest_sha256=manifest_sha, processing_version=_G4_PROCESSING,
        processing_run_id="g4:" + request, source_version="FHIR_R4",
        source_ingest_date=date(2026, 11, 2),
        processed_at=datetime.now(timezone.utc))
    metrics = {"patient": 0, "encounter": 0, "source_objects": 100,
               "quarantine_or_reject": 0}
    root = (f"{_FHIR_SOURCE_LANDING_ROOT}/clinical/v1/{_FHIR_SOURCE_HOSPITAL_ID}/"
            f"{_FHIR_SOURCE_FEED_ID}/{request}/landing-manifest.json")
    data = spark.read.format("binaryFile").load(root).select("content").collect()
    if len(data) != 1:
        raise RuntimeError("HOLD_G4_MANIFEST_SOURCE_NOT_ONE")
    manifest_raw = bytes(data[0].content)
    # Manifest changed => fail before any Delta read/write, not a new batch path.
    specs = _manifest_objects(manifest_raw, context)
    if len(specs) != 100:
        raise RuntimeError("HOLD_G4_SOURCE_NOT_100_OBJECTS")
    expected = _expected_bronze_source_receipts(context, specs)
    try:
        exists = {k: _delta_snapshot_exists(spark, v) for k, v in paths.items()}
    except Exception:
        return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                               context.processing_version, None, metrics,
                               ("G4 Delta path status uncertain",))
    if any(exists.values()):
        if exists["bronze"]:
            try:
                valid = _verify_bronze_receipt_readback(
                    spark, paths["bronze"], expected)
            except Exception:
                return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                                       context.processing_version, None, metrics,
                                       ("G4 persisted source readback uncertain",))
            if not valid:
                return NotebookOutcome("HOLD_REQUEST_DRIFT", context.source_batch_id,
                                       context.processing_version, None, metrics,
                                       ("same request, changed source or processing SHA",))
        if not all(exists[k] for k in (
                "bronze", "patient", "encounter", "approval")) or exists["quarantine"]:
            return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                                   context.processing_version, None, metrics,
                                   ("partial Silver/Quarantine Delta state",))
        try:
            batch = _verify_silver_publication_readback(
                spark, paths, context, manifest_raw, expected, pb, eb)
        except Exception:
            return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                                   context.processing_version, None, metrics,
                                   ("persisted Silver data or approval invalid",))
        return NotebookOutcome("SILVER_SKIP_VERIFIED", batch.source_batch_id,
                               batch.processing_version, batch.publication_id,
                               _metrics(batch), ())
    if mode == "SILVER_READBACK_ONLY":
        return NotebookOutcome("HOLD_SILVER_NOT_FOUND", context.source_batch_id,
                               context.processing_version, None, metrics, ())
    # First write only: all other output paths verified EMPTY and trusted.
    sources = read_source_objects_native(
        spark, source_root=_FHIR_SOURCE_LANDING_ROOT,
        manifest_bytes=manifest_raw, context=context)
    batch = prepare_batch(
        spark, context=context, manifest_bytes=manifest_raw,
        source_objects=sources, patient_contract_bytes=pb,
        encounter_contract_bytes=eb)
    metrics = _metrics(batch)
    if (batch.findings or batch.patient_count != 100
            or batch.encounter_count < 100):
        # Fail closed. Real DQ reason codes are preserved; no approval possible.
        reasons = [(
            f.classification, f.reason, f.detail, f.resource_type,
            f.resource_id, f.source_file, context.source_batch_id,
            context.processing_version) for f in batch.findings]
        if not reasons:
            reasons = [("HOLD", "G4_POPULATION_OR_ENCOUNTER_COUNT",
                        "100 Patient and >=100 Encounter required", "", "",
                        "", context.source_batch_id, context.processing_version)]
        try:
            quarantine = spark.createDataFrame(
                reasons,
                "classification string, reason string, detail string, "
                "resource_type string, resource_id string, source_file string, "
                "source_batch_id string, processing_version string")
            _write_delta(quarantine, paths["quarantine"])
            if spark.read.format("delta").load(paths["quarantine"]).count() != len(reasons):
                raise ValueError("G4_QUARANTINE_READBACK_INVALID")
        except Exception:
            return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                                   context.processing_version, None, metrics,
                                   ("G4 quarantine ACK/readback uncertain",))
        return NotebookOutcome("HOLD_DQ", batch.source_batch_id,
                               batch.processing_version, None, metrics,
                               tuple(f"{x[0]}:{x[1]}" for x in reasons))
    # Validate in-memory PK/FK/source/version BEFORE first irreversible write.
    validate_silver_readback(batch.patient_df, batch.encounter_df, batch, context)
    try:
        by_path = {o.source_file: o.payload for o in sources}
        if set(by_path) != {x["source_path"] for x in expected}:
            raise ValueError("G4_SOURCE_FILE_SET_CHANGED")
        raw_records = [{**row, "source_payload": by_path[row["source_path"]]}
                       for row in expected]
        column_schema = (
            "source_path string, source_sha256 string, source_size_bytes long, "
            "source_batch_id string, manifest_sha256 string, "
            "processing_version string, request_id string, source_payload binary")
        columns = [x.split()[0] for x in column_schema.split(", ")]
        raw_df = spark.createDataFrame(
            [tuple(r[k] for k in columns) for r in raw_records], column_schema)
        _write_delta(raw_df, paths["bronze"])
        if not _verify_bronze_receipt_readback(
                spark, paths["bronze"], raw_records):
            raise ValueError("G4_POSTWRITE_RAW_SNAPSHOT_MISMATCH")
        _write_verified_canonical_silver(
            spark, context=context, batch=batch, paths=paths,
            patient_contract_bytes=pb, encounter_contract_bytes=eb,
            source_preservation_strategy="DELTA_RAW_SNAPSHOT_V1",
            validate_persisted_canonical=validate_silver_readback)
        _verify_silver_publication_readback(
            spark, paths, context, manifest_raw, expected, pb, eb)
    except Exception:
        return NotebookOutcome("VERIFY_READONLY", batch.source_batch_id,
                               batch.processing_version, None, metrics,
                               ("partial write/unknown ACK: independent READBACK_ONLY required",))
    return NotebookOutcome("SILVER_APPROVED", batch.source_batch_id,
                           batch.processing_version, batch.publication_id,
                           metrics, ())



# HL7 P2.3: approved bounded source scopes, one verified candidate transport,
# same physical Silver Delta writer as G4. Never an independent Writer/Mapper.
_HL7_REAL_REQUEST = "johnscreek-hl7-gh-42410482514"
_HL7_REAL_MANIFEST_SHA = "dfb9895554470b0cb31536a041cd38aef5aaedd11ff762f491ce54e6dd1df114"
_HL7_REAL_SOURCE_SHA = "3999e773321a76a5d8421d62af23d24d833261a65812ea24e14e7e828f960a93"
_HL7_REAL_PROCESSING = "hl7-canonical-v1-real-p2.3:engine-0.1.7"
_HL7_REAL_SOURCE_ROOT = "Files/fhir_landing"
_HL7_REAL_TRANSFER_ROOT = "Files/fhir_landing/__hl7_candidate_handoff/v1"

# A separate, immutable NEW source, published from 10 actual Synthea patients.
# Run 42535807666 audited 8 A01/8 A03; OIE GET proof 42539430903;
# Azure 16 Blob GET/HEAD/manifest-last/replay Run 42540024573.
# The old 42-source scope remains byte-for-byte unchanged and independent.
_HL7_TEN_REQUEST = "johnscreek-hl7-gh-42535807666"
_HL7_TEN_MANIFEST_SHA = "5c2f506af86861a4bc539159f26db8077dcc10a27ad872738b19da2443832c81"
_HL7_TEN_SOURCE_SHA = "a68c7aa7d9fed1b1dcb6d8bb63162a87a98751dfbcfb187df214824de24a5e2f"
_HL7_TEN_PROCESSING = "hl7-canonical-v1-real-ten-20261108:engine-0.1.7"
_HL7_SOURCE_SCOPES = {
    _HL7_REAL_REQUEST: {
        "manifest_sha": _HL7_REAL_MANIFEST_SHA,
        "source_sha": _HL7_REAL_SOURCE_SHA,
        "processing": _HL7_REAL_PROCESSING,
        "processing_run_id": "hl7-real-get-42410482514",
        "processed_at": (2026, 11, 8, 9, 0),
        "source_ingest_date": (2026, 11, 8),
        "raw_count": 42,
    },
    _HL7_TEN_REQUEST: {
        "manifest_sha": _HL7_TEN_MANIFEST_SHA,
        "source_sha": _HL7_TEN_SOURCE_SHA,
        "processing": _HL7_TEN_PROCESSING,
        "processing_run_id": "hl7-real-get-42535807666",
        "processed_at": (2026, 11, 9, 0, 30),
        "source_ingest_date": (2026, 11, 8),
        "raw_count": 16,
    },
}


def _hl7_approved_scope(request: str) -> dict:
    # Never derive a new target or accept arbitrary request/manifest overrides.
    if request not in _HL7_SOURCE_SCOPES:
        raise ValueError("HOLD_HL7_UNAPPROVED_SOURCE_REQUEST")
    return _HL7_SOURCE_SCOPES[request]


def _hl7_source_context(request: str = _HL7_REAL_REQUEST) -> BatchContext:
    from datetime import datetime, date, timezone
    scoped = _hl7_approved_scope(request)
    return BatchContext(
        hospital_id="johns-creek-hospital-b",
        feed_id="johns-creek-hospital-b-hl7-v2",
        source_system="johns-creek-hl7",
        request_id=request,
        manifest_sha256=scoped["manifest_sha"],
        processing_version=scoped["processing"],
        processing_run_id=scoped["processing_run_id"],
        source_version="HL7v2.5.1",
        source_ingest_date=date(*scoped["source_ingest_date"]),
        processed_at=datetime(*scoped["processed_at"], tzinfo=timezone.utc),
        adapter_version="1.3.5",
    )


def _hl7_real_paths(context: BatchContext) -> dict[str, str]:
    if context != _hl7_source_context(context.request_id):
        raise ValueError("HOLD_HL7_REAL_CONTEXT_DRIFT")
    suffix = ("/" + context.hospital_id + "/" + context.feed_id + "/"
              + context.request_id + "/processing="
              + hashlib.sha256(context.processing_version.encode()).hexdigest())
    prefix = "Files/silver/hl7_v2" + suffix
    return {
        "patient": prefix + "/canonical_patient",
        "encounter": prefix + "/canonical_encounter",
        "approval": prefix + "/silver_approval",
        "quarantine": prefix + "/quarantine",
    }


def _hl7_transfer_root(context: BatchContext) -> str:
    if context != _hl7_source_context(context.request_id):
        raise ValueError("HOLD_HL7_REAL_CONTEXT_DRIFT")
    return (_HL7_REAL_TRANSFER_ROOT + "/" + context.source_batch_id
            + "/processing="
            + hashlib.sha256(context.processing_version.encode()).hexdigest())


def _hl7_binary_exact(spark, path: str, *, limit: int) -> bytes:
    if (not path.startswith("Files/fhir_landing/")
            or ".." in path or any(c in path for c in "*?\\")
            or limit < 1):
        raise ValueError("HOLD_HL7_UNAPPROVED_SOURCE_PATH")
    rows = spark.read.format("binaryFile").load(path).select("content").collect()
    if len(rows) != 1:
        raise ValueError("HOLD_HL7_SOURCE_NOT_EXACT_ONE")
    content = bytes(rows[0].content)
    if not 0 < len(content) <= limit:
        raise ValueError("HOLD_HL7_SOURCE_BYTES_LIMIT")
    return content


def _hl7_verified_original_raw(spark, context: BatchContext) -> dict:
    """Fresh GET-only, exact 42/16 Raw SHA/size fence through the existing shortcut."""
    if context != _hl7_source_context(context.request_id):
        raise ValueError("HOLD_HL7_SOURCE_CONTEXT")
    base = (f"{_HL7_REAL_SOURCE_ROOT}/clinical/v1/{context.hospital_id}/"
            f"{context.feed_id}/{context.request_id}")
    manifest_bytes = _hl7_binary_exact(
        spark, base + "/landing-manifest.json", limit=2 * 1024 * 1024)
    scope = _hl7_approved_scope(context.request_id)
    if hashlib.sha256(manifest_bytes).hexdigest() != scope["manifest_sha"]:
        raise ValueError("HOLD_HL7_REAL_SOURCE_MANIFEST_SHA")
    doc = json.loads(manifest_bytes)
    if (not isinstance(doc, dict)
            or doc.get("hospital_id") != context.hospital_id
            or doc.get("feed_id") != context.feed_id
            or doc.get("request_id") != context.request_id
            or doc.get("source_manifest_sha256") != scope["source_sha"]
            or not isinstance(doc.get("objects"), list)
            or len(doc["objects"]) != scope["raw_count"]):
        raise ValueError("HOLD_HL7_SOURCE_MANIFEST_FIELDS")
    seen = {}
    for o in doc["objects"]:
        if not isinstance(o, dict) or not all(
                k in o for k in ("blob_key", "sha256", "size_bytes")):
            raise ValueError("HOLD_HL7_SOURCE_OBJECT_ENVELOPE")
        key = o["blob_key"]
        prefix = (f"clinical/v1/{context.hospital_id}/{context.feed_id}/"
                  f"{context.request_id}/HL7_V2/hl7/")
        import re
        if (not isinstance(key, str) or not key.startswith(prefix)
                or not re.fullmatch(
                    r"[A-Za-z0-9-]+-(A01|A03)\.hl7", key[len(prefix):])
                or key in seen or type(o["size_bytes"]) is not int
                or not 0 < o["size_bytes"] <= 1024 * 1024
                or not isinstance(o["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", o["sha256"])):
            raise ValueError("HOLD_HL7_RAW_OBJECT_IDENTITY")
        raw = _hl7_binary_exact(
            spark, _HL7_REAL_SOURCE_ROOT + "/" + key, limit=1024 * 1024)
        if (len(raw) != o["size_bytes"]
                or hashlib.sha256(raw).hexdigest() != o["sha256"]):
            raise ValueError("HOLD_HL7_RAW_OBJECT_DRIFT")
        seen[key] = (o["sha256"], o["size_bytes"])
    return seen


def _hl7_reopened_dq(patient_delta, encounter_delta,
                     expected: PreparedBatch, context: BatchContext,
                     patient_contract_bytes: bytes,
                     encounter_contract_bytes: bytes) -> None:
    """Source-neutral physical readback: pinned Shared v1 Contract + PK/FK."""
    from datetime import datetime, timezone
    from healthcare_data_engine.canonical.validation import validate_row
    from healthcare_data_engine.quality.result import TransformResult
    contracts = {
        "patient": load_pinned_contract(patient_contract_bytes, "patient"),
        "encounter": load_pinned_contract(encounter_contract_bytes, "encounter"),
    }
    records = {}
    for entity, frame in (("patient", patient_delta),
                          ("encounter", encounter_delta)):
        actual = []
        for item in frame.collect():
            row = item.asDict(recursive=True)
            for key, val in row.items():
                if isinstance(val, datetime) and val.tzinfo is None:
                    row[key] = val.replace(tzinfo=timezone.utc)
            if validate_row(row, contracts[entity]):
                raise ValueError("HOLD_HL7_REOPENED_CONTRACT_" + entity)
            actual.append(row)
        records[entity] = tuple(actual)
    checked = reconcile_patient_encounter(
        TransformResult(records["patient"], (), ()),
        TransformResult(records["encounter"], (), ()), context)
    metrics = checked.metrics
    if (metrics["patient_accepted"] != expected.patient_count
            or metrics["encounter_accepted"] != expected.encounter_count
            or any(metrics[k] for k in (
                "patient_rejected", "encounter_rejected",
                "patient_quarantined", "encounter_quarantined"))):
        raise ValueError("HOLD_HL7_REOPENED_SHARED_DQ")
    _validate_silver_delta_contents(expected.patient_df, patient_delta, "patient")
    _validate_silver_delta_contents(expected.encounter_df, encounter_delta, "encounter")



def _hl7_recompute_persisted_approval(
        spark, paths: dict[str, str], context: BatchContext,
        patient_contract_bytes: bytes, encounter_contract_bytes: bytes,
        original_provenance: dict, expected_transport_sha256: str) -> PreparedBatch:
    """Transport-independent future Silver readback, after temp Blob cleanup.

    Canonical rows are retyped from physically persisted Delta, the original
    Raw hashes of the explicitly approved Request are freshly proven; transport
    fingerprint is recomputed. Approval MUST equal the original exact bytes'
    fingerprint; no local candidate or original staging persists.
    """
    from datetime import datetime, date, timezone
    from decimal import Decimal
    from healthcare_data_engine.canonical.validation import validate_row
    from healthcare_data_engine.quality.result import TransformResult
    contracts = {
        "patient": load_pinned_contract(patient_contract_bytes, "patient"),
        "encounter": load_pinned_contract(encounter_contract_bytes, "encounter"),
    }
    frames = {
        "patient": spark.read.format("delta").load(paths["patient"]),
        "encounter": spark.read.format("delta").load(paths["encounter"]),
    }
    accepted, digests, byte_sizes = {}, {}, {}
    for entity, key in (("patient", "source_record_id"),
                        ("encounter", "source_encounter_id")):
        records, wire = [], []
        fields = contracts[entity]["fields"]
        for item in frames[entity].collect():
            row = item.asDict(recursive=True)
            for k, v in row.items():
                if isinstance(v, datetime) and v.tzinfo is None:
                    row[k] = v.replace(tzinfo=timezone.utc)
            if (validate_row(row, contracts[entity])
                    or row["source_batch_id"] != context.source_batch_id
                    or row["source_system"] != context.namespaced_source_system
                    or row["processing_run_id"] != context.processing_run_id
                    or row["processed_at"] != context.processed_at
                    or row["source_version"] != context.source_version
                    or row["source_ingest_date"] != context.source_ingest_date
                    or row["adapter_version"] != context.adapter_version
                    or row["adapter_name"] != "hl7apy"
                    or row["canonical_version"] != "v1"
                    or original_provenance.get(row["source_file"]) != (
                        row["source_file_sha256"], row["source_file_size_bytes"])):
                raise ValueError("HOLD_HL7_PERSISTED_ROW_CONTEXT")
            typed = {}
            for field in fields:
                name, value, kind = field["name"], row[field["name"]], field["type"]
                if isinstance(value, datetime):
                    value = value.astimezone(timezone.utc).isoformat(
                        timespec="microseconds").replace("+00:00", "Z")
                elif isinstance(value, date):
                    value = value.isoformat()
                elif isinstance(value, Decimal):
                    value = str(value)
                typed[name] = value
            records.append(row)
            wire.append(typed)
        if not 0 < len(wire) <= 50000:
            raise ValueError("HOLD_HL7_PERSISTED_COUNT")
        accepted[entity] = tuple(records)
        wire.sort(key=lambda item: item[key])
        raw = json.dumps({"entity": entity, "rows": wire,
                          "schema": "healthcare-hl7-canonical-transport-v1"},
                         sort_keys=True, ensure_ascii=True,
                         separators=(",", ":"), allow_nan=False).encode()
        digests[entity] = hashlib.sha256(raw).hexdigest()
        byte_sizes[entity] = len(raw)
    reconciliation = reconcile_patient_encounter(
        TransformResult(accepted["patient"], (), ()),
        TransformResult(accepted["encounter"], (), ()), context)
    metrics = reconciliation.metrics
    if any(metrics[k] for k in (
            "patient_quarantined", "encounter_quarantined",
            "patient_rejected", "encounter_rejected")):
        raise ValueError("HOLD_HL7_PERSISTED_PK_FK")
    pubid = hashlib.sha256(json.dumps({
        "source_batch_id": context.source_batch_id,
        "processing_version": context.processing_version,
        "patient_sha256": digests["patient"],
        "encounter_sha256": digests["encounter"],
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    batch = PreparedBatch(
        patient_df=frames["patient"], encounter_df=frames["encounter"],
        patient_count=len(accepted["patient"]),
        encounter_count=len(accepted["encounter"]),
        findings=(), source_batch_id=context.source_batch_id,
        processing_version=context.processing_version,
        publication_id=pubid, manifest_sha256=context.manifest_sha256.lower(),
        source_receipts=())
    # Reconstruct exactly the manifest-last Candidate bytes using persisted
    # canonical rows. This allows recovery after the short-lived transfer is
    # removed without trusting a self-reported manifest digest.
    entity_receipts = {
        name: {
            "file": "canonical_" + name + ".json",
            "sha256": digests[name],
            "bytes": byte_sizes[name],
            "rows": len(accepted[name]),
        }
        for name in ("patient", "encounter")
    }
    sealed_manifest = {
        "schema": "healthcare-hl7-canonical-transport-v1",
        "hospital_id": context.hospital_id,
        "feed_id": context.feed_id,
        "source_system": context.source_system,
        "request_id": context.request_id,
        "source_batch_id": context.source_batch_id,
        "source_manifest_sha256": context.manifest_sha256.lower(),
        "processing_version": context.processing_version,
        "source_version": context.source_version,
        "adapter_version": context.adapter_version,
        "canonical_version": context.canonical_version,
        "patient_contract_sha256": hashlib.sha256(patient_contract_bytes).hexdigest(),
        "encounter_contract_sha256": hashlib.sha256(encounter_contract_bytes).hexdigest(),
        "publication_id": pubid,
        "entities": entity_receipts,
        "status": "CANDIDATE_ONLY_NOT_SILVER_APPROVED",
    }
    sealed_sha = hashlib.sha256(json.dumps(
        sealed_manifest, sort_keys=True, ensure_ascii=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    if sealed_sha != expected_transport_sha256:
        raise ValueError("HOLD_HL7_PERSISTED_TRANSPORT_PIN_CHANGED")
    expected_approval = _canonical_silver_approval_row(
        batch, patient_contract_bytes, encounter_contract_bytes,
        source_preservation_strategy="VERIFIED_HL7_CANDIDATE_V1")
    approved = spark.read.format("delta").load(paths["approval"]).collect()
    if (len(approved) != 1
            or approved[0].asDict(recursive=True) != expected_approval):
        raise ValueError("HOLD_HL7_PERSISTED_APPROVAL_OR_CONTENT_CHANGED")
    return batch


def verify_hl7_real_silver(spark, *, request: str, manifest_sha: str,
                           mode: str, allow_write: bool, retention_ok: bool,
                           strategy: str, manifest_override: str,
                           source_override: str, target_override: str,
                           patient_contract_json: str,
                           encounter_contract_json: str) -> NotebookOutcome:
    """One approved source per call (old42 or new16); partial state stays read-only HOLD."""
    import re
    if (mode not in ("HL7_SILVER_WRITE", "HL7_SILVER_READBACK_ONLY")
            or request not in _HL7_SOURCE_SCOPES
            or strategy != "VERIFIED_HL7_CANDIDATE_V1"
            or any(x != "" for x in (
                manifest_override, source_override, target_override))
            or (mode == "HL7_SILVER_WRITE" and
                (allow_write is not True or retention_ok is not True))
            or (mode == "HL7_SILVER_READBACK_ONLY" and
                (allow_write is not False or retention_ok is not False))
            or engine_version != "0.1.7"
            or not isinstance(manifest_sha, str)
            or not re.fullmatch(r"[0-9a-f]{64}", manifest_sha)):
        raise RuntimeError("HOLD_HL7_RELEASE_MODE_OR_SOURCE_FENCE")
    if (not isinstance(patient_contract_json, str)
            or not isinstance(encounter_contract_json, str)
            or len(patient_contract_json) > 5000
            or len(encounter_contract_json) > 5000):
        raise RuntimeError("HOLD_HL7_CONTRACT_INPUT")
    pb, eb = patient_contract_json.encode(), encounter_contract_json.encode()
    load_pinned_contract(pb, "patient")
    load_pinned_contract(eb, "encounter")
    context = _hl7_source_context(request)
    paths = _hl7_real_paths(context)
    metrics = {"patient": 0, "encounter": 0,
               "quarantine_or_reject": 0,
               "source_objects": _hl7_approved_scope(request)["raw_count"]}
    # Source proof MUST be fresh; a stale historical P2 run is not evidence.
    raw_provenance = _hl7_verified_original_raw(spark, context)
    try:
        exists = {k: _delta_snapshot_exists(spark, path)
                  for k, path in paths.items()}
    except Exception:
        return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                               context.processing_version, None, metrics,
                               ("Silver Delta state unknown",))
    if any(exists.values()):
        if (not all(exists[k] for k in ("patient", "encounter", "approval"))
                or exists["quarantine"]):
            return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                                   context.processing_version, None, metrics,
                                   ("partial/unknown Silver state",))
        try:
            persisted = _hl7_recompute_persisted_approval(
                spark, paths, context, pb, eb, raw_provenance, manifest_sha)
        except Exception:
            return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                                   context.processing_version, None, metrics,
                                   ("persisted source/content/approval mismatch",))
        return NotebookOutcome(
            "SILVER_SKIP_VERIFIED",
            context.source_batch_id, context.processing_version,
            persisted.publication_id,
            {**metrics, "patient": persisted.patient_count,
             "encounter": persisted.encounter_count}, ())
    # The transient Candidate is needed ONLY on first creation, not to
    # independently verify already-approved durable Silver after cleanup.
    if mode == "HL7_SILVER_READBACK_ONLY":
        return NotebookOutcome("HOLD_SILVER_NOT_FOUND", context.source_batch_id,
                               context.processing_version, None, metrics, ())
    # Candidate transfer is short-lived; load only when target is fully absent.
    root = _hl7_transfer_root(context)
    bundle = {
        k: _hl7_binary_exact(
            spark, root + "/" + k,
            limit=(16384 if k == "candidate_manifest.json" else 16 * 1024 * 1024))
        for k in ("canonical_patient.json", "canonical_encounter.json",
                  "candidate_manifest.json")
    }
    prepared = prepare_hl7_candidate_bundle_for_silver(
        spark, bundle=bundle, bundle_manifest_sha256=manifest_sha,
        context=context, patient_contract_bytes=pb,
        encounter_contract_bytes=eb, source_evidence_verified=True)
    for frame in (prepared.patient_df, prepared.encounter_df):
        for row in frame.select("source_file", "source_file_sha256",
                                "source_file_size_bytes").distinct().collect():
            if raw_provenance.get(row["source_file"]) != (
                    row["source_file_sha256"], row["source_file_size_bytes"]):
                raise ValueError("HOLD_HL7_CANDIDATE_RAW_PROVENANCE")
    def validate_reopened(p, e, batch, scope):
        _hl7_reopened_dq(p, e, batch, scope, pb, eb)
    # No existing Delta: the single physical Writer owns all Silver writes.
    try:
        _write_verified_canonical_silver(
            spark, context=context, batch=prepared, paths=paths,
            patient_contract_bytes=pb, encounter_contract_bytes=eb,
            source_preservation_strategy="VERIFIED_HL7_CANDIDATE_V1",
            validate_persisted_canonical=validate_reopened)
    except Exception:
        return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                               context.processing_version, None, metrics,
                               ("partial/unknown ACK requires independent physical readback",))
    return NotebookOutcome("SILVER_APPROVED",
                           context.source_batch_id, context.processing_version,
                           prepared.publication_id,
                           {**metrics, "patient": prepared.patient_count,
                            "encounter": prepared.encounter_count}, ())


# G5 source boundary only. This does NOT query an OMOP identity map, map
# clinical Concepts, persist Candidate Delta or authorize Warehouse Gold.
# Historical G4 processing=engine-0.1.1 MUST stay pinned for existing Delta.
_G5_APPROVED_REQUEST = "atlanta-fhir-gh-41552666929"
_G5_APPROVED_MANIFEST_SHA = (
    "425a25a6337e86a2df39c1f7993d46fd0555cfed9107dde415521fde755ff2f1")
_G5_APPROVED_PATIENTS = 100
_G5_APPROVED_ENCOUNTERS = 5918


def _g5_candidate_paths(scope) -> dict[str, str]:
    _bronze_source_receipt_path(scope.request_id)  # no traversal or unapproved request
    if (scope.request_id != _G5_APPROVED_REQUEST
            or scope.manifest_sha256 != _G5_APPROVED_MANIFEST_SHA
            or scope.silver_processing_version != _G4_PROCESSING
            or scope.patient_count != _G5_APPROVED_PATIENTS
            or scope.encounter_count != _G5_APPROVED_ENCOUNTERS
            or scope.hospital_id != _FHIR_SOURCE_HOSPITAL_ID
            or scope.feed_id != _FHIR_SOURCE_FEED_ID
            or scope.source_system != "synthea-fhir:" + _FHIR_SOURCE_HOSPITAL_ID + ":" + _FHIR_SOURCE_FEED_ID):
        raise RuntimeError("HOLD_G5_CANDIDATE_SOURCE_SCOPE")
    prefix = (f"Files/omop_candidate/fhir_r4/{scope.hospital_id}/"
              f"{scope.feed_id}/{scope.request_id}/mapping={scope.mapping_sha256}")
    return {"person": prefix + "/person_candidate",
            "visit": prefix + "/visit_candidate",
            "approval": prefix + "/candidate_approval"}


def _g5_dynamic_fhir_candidate_paths_source_only(scope, *, trusted_scope) -> dict[str, str]:
    """Plan a NEW FHIR Candidate path bound to independently pinned v3 scope.

    SOURCE_ONLY: deriving deterministic output paths is never a publication
    approval, Stage release token, proof of Silver, or Delta write capability.
    The protected controller must later verify the physical Silver, F1/F2,
    source Manifest and Blob Claim before invoking any Native Writer.
    Existing frozen P100/E5918 readback and Candidate paths stay unchanged.
    """
    # The published Fabric 0.1.7 Wheel cannot validate the v3 contract.
    # Reject before importing newer APIs and before any Spark/Blob activity.
    if engine_version != "0.1.13":
        raise RuntimeError("HOLD_G5_DYNAMIC_0113_WHEEL_NOT_PUBLISHED")
    from healthcare_data_engine.mapping.omop.candidate_publication import (
        FrozenCandidateScope,
    )
    from healthcare_data_engine.security.provider_attestation import (
        TrustedTechnicalScope, TransportHold,
    )
    if (type(scope) is not FrozenCandidateScope
            or type(trusted_scope) is not TrustedTechnicalScope):
        raise RuntimeError("HOLD_G5_DYNAMIC_TRUSTED_SCOPE_TYPE")
    try:
        trusted_scope.validate()
    except TransportHold:
        raise RuntimeError("HOLD_G5_DYNAMIC_TRUSTED_SCOPE_INVALID") from None
    if (trusted_scope.source_format != "FHIR_R4"
            or trusted_scope.stage != "CANDIDATE_APPROVED"
            or scope.request_id != trusted_scope.request_id
            or scope.source_system != trusted_scope.source_system
            or scope.source_batch_id != trusted_scope.source_batch_id
            or scope.manifest_sha256 != trusted_scope.manifest_sha256
            or scope.mapping_sha256 != trusted_scope.mapping_profile_sha256
            or scope.identity_snapshot_fingerprint
                != trusted_scope.f2_identity_snapshot_fingerprint):
        raise RuntimeError("HOLD_G5_DYNAMIC_STAGE_BATCH_OR_EVIDENCE_DRIFT")
    # The existing small-batch physical content verifier caps each table at
    # 10k rows. Larger batches require a separately reviewed chunked writer.
    if scope.patient_count > 10000 or scope.encounter_count > 10000:
        raise RuntimeError("HOLD_G5_DYNAMIC_UNSUPPORTED_LARGE_BATCH")
    # These are safe, validated path components (FrozenCandidateScope + v3
    # TrustedTechnicalScope each enforce strict grammar, no slash/traversal).
    prefix = (
        f"Files/omop_candidate/fhir_r4/{scope.hospital_id}/"
        f"{scope.feed_id}/{scope.request_id}/"
        f"stage={trusted_scope.stage_scope_version}/"
        f"source_batch={scope.source_batch_id}/"
        f"mapping={scope.mapping_sha256}"
    )
    return {
        "person": prefix + "/person_candidate",
        "visit": prefix + "/visit_candidate",
        "approval": prefix + "/candidate_approval",
    }


def verify_fhir_g5_dynamic_silver_source_readonly(
    spark, *, scope, trusted_scope, source_ingest_date,
    patient_contract_json: str, encounter_contract_json: str,
) -> str:
    """Reopen and independently recompute NEW FHIR G4 Silver, SOURCE_ONLY.

    The trusted controller must supply exact previously persisted Stage/Batch
    identity and original source-ingest date. All actual source objects are
    reread from durable Bronze bytes and reprocessed through the SINGLE
    existing Shared FHIR adapter and Canonical engine. Persisted Patient,
    Encounter, Quarantine absence and exact Approval-LAST are independently
    reopened and checked. This function does NOT verify F1/F2 Gold authority,
    Azure external Blob WORM, Stage Claim/Lease or receipt; NO Writer dispatch.
    """
    # Fail before even touching Spark: the published Fabric wheel is still
    # 0.1.7, and Notebook/Pipeline must retain a separate HALT fence.
    if engine_version != "0.1.13":
        raise RuntimeError("HOLD_G5_DYNAMIC_0113_WHEEL_NOT_PUBLISHED")
    if run_mode != "HALT" or write_authorized is not False:
        raise RuntimeError("HOLD_G5_DYNAMIC_SILVER_NONHALT_OR_WRITE_FLAG")
    from datetime import date, datetime, timezone
    if (type(source_ingest_date) is not date
            or scope is None
            or scope.hospital_id != _FHIR_SOURCE_HOSPITAL_ID
            or scope.feed_id != _FHIR_SOURCE_FEED_ID
            or scope.silver_processing_version != _G4_PROCESSING):
        raise RuntimeError("HOLD_G5_DYNAMIC_G4_SOURCE_VERSION_OR_DATE")
    # This planner is a pure, typed v3 trust-scope/batch boundary. It never
    # returns authority to publish and is deliberately not the Writer path.
    _g5_dynamic_fhir_candidate_paths_source_only(
        scope, trusted_scope=trusted_scope)
    if (not isinstance(patient_contract_json, str)
            or not isinstance(encounter_contract_json, str)
            or not 0 < len(patient_contract_json) <= 5000
            or not 0 < len(encounter_contract_json) <= 5000):
        raise RuntimeError("HOLD_G5_DYNAMIC_CANONICAL_CONTRACT_BYTES")
    pb = patient_contract_json.encode("utf-8")
    eb = encounter_contract_json.encode("utf-8")
    load_pinned_contract(pb, "patient")
    load_pinned_contract(eb, "encounter")
    context = BatchContext(
        hospital_id=scope.hospital_id,
        feed_id=scope.feed_id,
        source_system="synthea-fhir", request_id=scope.request_id,
        manifest_sha256=scope.manifest_sha256,
        processing_version=_G4_PROCESSING,
        processing_run_id="g4:" + scope.request_id,
        source_version="FHIR_R4",
        source_ingest_date=source_ingest_date,
        processed_at=datetime.now(timezone.utc),
    )
    if context.source_batch_id != scope.source_batch_id:
        raise RuntimeError("HOLD_G5_DYNAMIC_DERIVED_BATCH_SHA_DRIFT")
    # Read original, fixed Landing Manifest bytes from the existing approved
    # hospital/feed namespace, never from an arbitrary path or query argument.
    original_manifest = (
        f"{_FHIR_SOURCE_LANDING_ROOT}/clinical/v1/{_FHIR_SOURCE_HOSPITAL_ID}/"
        f"{_FHIR_SOURCE_FEED_ID}/{scope.request_id}/landing-manifest.json")
    rows = spark.read.format("binaryFile").load(
        original_manifest).select("content").collect()
    if (len(rows) != 1
            or not isinstance(rows[0].content,
                              (bytes, bytearray, memoryview))):
        raise RuntimeError("HOLD_G5_DYNAMIC_LANDING_MANIFEST_NOT_ONE")
    manifest_bytes = bytes(rows[0].content)
    if hashlib.sha256(manifest_bytes).hexdigest() != scope.manifest_sha256:
        raise RuntimeError("HOLD_G5_DYNAMIC_LANDING_MANIFEST_SHA_DRIFT")
    specs = _manifest_objects(manifest_bytes, context)
    if not 1 <= len(specs) <= 5000:
        raise RuntimeError("HOLD_G5_DYNAMIC_SOURCE_OBJECT_COUNT")
    expected = _expected_bronze_source_receipts(context, specs)
    paths = _silver_publication_paths(scope.request_id)
    exists = {key: _delta_snapshot_exists(spark, path)
              for key, path in paths.items()}
    if (not all(exists[k] for k in
                ("bronze", "patient", "encounter", "approval"))
            or exists["quarantine"]):
        raise RuntimeError("HOLD_G5_DYNAMIC_SILVER_PARTIAL_OR_QUARANTINED")
    # Reopen original raw Bronze bytes, and then re-run only the existing
    # Shared FHIR normalizers and the canonical DQ/reconciliation logic.
    sources = _snapshot_silver_source_objects(
        spark, paths["bronze"], expected, context)
    batch = prepare_batch(
        spark, context=context, manifest_bytes=manifest_bytes,
        source_objects=sources, patient_contract_bytes=pb,
        encounter_contract_bytes=eb)
    if (batch.findings or batch.patient_count != scope.patient_count
            or batch.encounter_count != scope.encounter_count
            or batch.source_batch_id != scope.source_batch_id
            or batch.manifest_sha256 != scope.manifest_sha256
            or batch.processing_version != scope.silver_processing_version
            or batch.publication_id != scope.silver_publication_id):
        raise RuntimeError("HOLD_G5_DYNAMIC_RECOMPUTED_DQ_OR_PUBLICATION")
    # Two fresh Silver Delta reads, full-row multiset comparison, PK/FK,
    # source namespace, canonical version and bounded exact Stage counts.
    patient = spark.read.format("delta").load(paths["patient"])
    encounter = spark.read.format("delta").load(paths["encounter"])
    validate_silver_readback(patient, encounter, batch, context)
    _validate_silver_delta_contents(batch.patient_df, patient, "patient")
    _validate_silver_delta_contents(batch.encounter_df, encounter, "encounter")
    approved = spark.read.format("delta").load(paths["approval"]).collect()
    expected_approval = _silver_approval_row(context, batch, pb, eb)
    if (len(approved) != 1
            or approved[0].asDict(recursive=True) != expected_approval):
        raise RuntimeError("HOLD_G5_DYNAMIC_APPROVAL_LAST_FENCE_DRIFT")
    return "G5_DYNAMIC_FHIR_SILVER_PHYSICAL_RECOMPUTE_PASS_SOURCE_ONLY_NO_RELEASE"


def _candidate_delta_content(frame, *, key: str, expected: int) -> tuple[str, list[dict]]:
    """Bounded deterministic full-row digest; never log protected row values."""
    if (type(expected) is not int or not 0 < expected <= 10000
            or key not in frame.columns
            or len(frame.columns) != len(set(frame.columns))):
        raise RuntimeError("HOLD_G5_CANDIDATE_SCHEMA_OR_BOUNDS")
    rows = [r.asDict(recursive=True) for r in frame.collect()]
    if len(rows) != expected:
        raise RuntimeError("HOLD_G5_CANDIDATE_COUNT")
    if len({r.get(key) for r in rows}) != expected or any(
            type(r.get(key)) is not int or r[key] <= 0 for r in rows):
        raise RuntimeError("HOLD_G5_CANDIDATE_DUPLICATE_OR_INVALID_ID")
    import datetime
    import decimal
    def encode(value):
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        if isinstance(value, decimal.Decimal):
            return str(value)
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).hex()
        raise TypeError("G5_UNSUPPORTED_CANDIDATE_DATATYPE")
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda x: x[key]):
        if set(row) != set(frame.columns):
            raise RuntimeError("HOLD_G5_CANDIDATE_ROW_SCHEMA")
        raw = json.dumps(row, sort_keys=True, separators=(",", ":"),
                         default=encode, allow_nan=False).encode("utf-8")
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return digest.hexdigest(), rows


def _validate_candidate_rows(person_rows, visit_rows, handoff) -> None:
    """Strict source/identity contract; do not infer any clinical Concept."""
    persons = {(r.get("person_id"), r.get("person_source_value"),
                r.get("identity_state")) for r in person_rows}
    expected_person = {(p.person_id, p.source_business_key, p.state)
                       for p in handoff.batch_persons}
    visits = {(r.get("visit_occurrence_id"), r.get("person_id"),
               r.get("source_encounter_id"), r.get("source_person_id"),
               r.get("identity_state"), r.get("parent_identity_state"))
              for r in visit_rows}
    expected_visit = {(v.visit_occurrence_id, v.person_id,
                       v.source_encounter_id, v.source_person_id,
                       v.state, v.parent_state) for v in handoff.batch_visits}
    if (len(persons) != len(person_rows) or persons != expected_person
            or len(visits) != len(visit_rows) or visits != expected_visit):
        raise RuntimeError("HOLD_G5_CANDIDATE_IDENTITY_OR_FK_DRIFT")
    # Candidate is allowed provisional INT IDs; Gold is NOT.
    if any(p.state not in ("PROVISIONAL", "PERSISTED") for p in handoff.batch_persons):
        raise RuntimeError("HOLD_G5_CANDIDATE_ID_STATE")
    if any(v.state not in ("PROVISIONAL", "PERSISTED") or
           v.parent_state not in ("PROVISIONAL", "PERSISTED")
           for v in handoff.batch_visits):
        raise RuntimeError("HOLD_G5_CANDIDATE_ID_STATE")



def _verify_candidate_mapper_payload(mapper_result, person_candidate,
                                        visit_candidate, scope) -> None:
    """Require every proposed Delta payload field to equal the sole F1 Mapper.

    Identity proposal adds ONLY explicitly declared provisional state/Visit ID
    columns; it must never replace a mapped Concept, date, source value, or
    other OMOP property with hand-authored Notebook values. Full multiset
    comparison uses Spark exceptAll on all mapped columns, NOT a sample.
    """
    p_base = mapper_result.person
    v_base = mapper_result.visit
    p_columns = set(p_base.columns)
    v_columns = set(v_base.columns)
    if (p_columns != set(person_candidate.columns) - {"identity_state"}
            or v_columns != set(visit_candidate.columns) - {
                "visit_occurrence_id", "identity_state", "parent_identity_state"}
            or "person_id" not in p_columns
            or {"source_encounter_id", "source_person_id", "person_id"} - v_columns
            or p_base.count() != scope.patient_count
            or v_base.count() != scope.encounter_count):
        raise RuntimeError("HOLD_G5_MAPPER_CANDIDATE_SCHEMA_OR_COUNT")
    for mapped, candidate, columns in (
        (p_base, person_candidate, sorted(p_columns)),
        (v_base, visit_candidate, sorted(v_columns)),
    ):
        source = mapped.select(*columns)
        target = candidate.select(*columns)
        if (target.exceptAll(source).limit(1).count()
                or source.exceptAll(target).limit(1).count()):
            raise RuntimeError("HOLD_G5_MAPPER_CANDIDATE_PAYLOAD_CHANGED")


def plan_and_write_g5_candidate_delta(
    spark, *, scope, handoff, mapper_result, person_candidate, visit_candidate,
    mode: str, write_authorized: bool,
    clinically_reviewed: bool = False, license_reviewed: bool = False,
    warehouse_snapshot_verified: bool,
    clinical_review_sha256: str | None = None,
    license_review_sha256: str | None = None,
    warehouse_snapshot_sha256: str,
    patient_contract_json: str, encounter_contract_json: str,
    technical_evidence_sha256: str | None = None,
    trusted_technical_release_gate: Callable | None = None,
) -> str:
    """Real G5 Delta writer, never a Notebook/Pipeline parameter entrypoint.

    The current route binds ONE externally authenticated technical witness,
    without Clinical/License human signoffs. Legacy signed-v1 remains optional
    for historical test/replay. A technical SHA ALONE does not permit writing:
    a protected trusted controller must recheck the exact Stage and witness
    via trusted_technical_release_gate, plus physical Warehouse/Silver proofs.
    The actual Fabric Pipeline still defaults to HALT.
    """
    from healthcare_data_engine.mapping.omop.candidate_publication import (
        FrozenCandidateScope, PersonVisitCandidateHandoff as _Unused,
        decide_candidate_publication, ObservedCandidate,
    )
    from healthcare_data_engine.mapping.omop.candidates import OmopCandidates
    if (not isinstance(scope, FrozenCandidateScope)
            or not isinstance(handoff, _Unused)
            or not isinstance(mapper_result, OmopCandidates)
            or mapper_result.status != "OMOP_CANDIDATE_ONLY_NOT_PUBLISHED"
            or mapper_result.mapping_sha256 != scope.mapping_sha256
            or mapper_result.person_count != scope.patient_count
            or mapper_result.visit_count != scope.encounter_count
            or scope.hospital_id != handoff.hospital_id
            or scope.source_system != handoff.source_system
            or scope.source_batch_id != handoff.source_batch_id
            or scope.manifest_sha256 != handoff.manifest_sha256
            or scope.mapping_sha256 is None
            or scope.identity_snapshot_fingerprint != handoff.snapshot_fingerprint
            or scope.silver_publication_id != handoff.silver_publication_id
            or scope.patient_count != len(handoff.batch_persons)
            or scope.encounter_count != len(handoff.batch_visits)
            or scope.provisional_person_count != sum(
                p.state == "PROVISIONAL" for p in handoff.batch_persons)
            or scope.provisional_visit_count != sum(
                visit.state == "PROVISIONAL" for visit in handoff.batch_visits)):
        raise RuntimeError("HOLD_G5_CANDIDATE_F2_SCOPE_DRIFT")
    from re import fullmatch
    if (mode not in ("G5_CANDIDATE_WRITE", "G5_CANDIDATE_READBACK_ONLY")
            or type(write_authorized) is not bool
            or type(clinically_reviewed) is not bool
            or type(license_reviewed) is not bool
            or type(warehouse_snapshot_verified) is not bool):
        raise RuntimeError("HOLD_G5_CANDIDATE_MODE_OR_FLAGS")
    technical = technical_evidence_sha256 is not None
    if technical and (clinically_reviewed or license_reviewed
                      or clinical_review_sha256 is not None
                      or license_review_sha256 is not None):
        raise RuntimeError("HOLD_G5_TECHNICAL_EVIDENCE_CANNOT_FORGE_REVIEWS")
    if mode == "G5_CANDIDATE_READBACK_ONLY" and (
            write_authorized or clinically_reviewed or license_reviewed):
        raise RuntimeError("HOLD_G5_CANDIDATE_READBACK_FLAGS")
    digests = (
        (technical_evidence_sha256, warehouse_snapshot_sha256)
        if technical else
        (clinical_review_sha256, license_review_sha256,
         warehouse_snapshot_sha256)
    )
    if any(not isinstance(x, str) or not fullmatch(r"[0-9a-f]{64}", x)
           for x in digests):
        raise RuntimeError("HOLD_G5_CANDIDATE_EVIDENCE_SHA_NOT_PINNED")
    if warehouse_snapshot_sha256 != scope.identity_snapshot_fingerprint:
        raise RuntimeError("HOLD_G5_CANDIDATE_WAREHOUSE_SNAPSHOT_DRIFT")
    if mode == "G5_CANDIDATE_WRITE":
        if not (write_authorized and warehouse_snapshot_verified):
            raise RuntimeError("HOLD_G5_CANDIDATE_TECHNICAL_RELEASE_MISSING")
        if technical:
            # The trusted callback is code from the protected Stage controller,
            # not a value supplied by Notebook/Pipeline user parameters.
            if (not callable(trusted_technical_release_gate)
                    or trusted_technical_release_gate(
                        scope, technical_evidence_sha256) is not True):
                raise RuntimeError("HOLD_G5_TECHNICAL_STAGE_RELEASE_UNTRUSTED")
        elif not (clinically_reviewed and license_reviewed):
            raise RuntimeError("HOLD_G5_LEGACY_SIGNED_RELEASE_INCOMPLETE")
    paths = _g5_candidate_paths(scope)
    source = verify_fhir_g5_candidate_source_readonly(
        spark, request=scope.request_id, manifest_sha=scope.manifest_sha256,
        allow_write=False, retention_ok=False,
        strategy="DELTA_RAW_SNAPSHOT_V1",
        manifest_override="", source_override="", target_override="",
        patient_contract_json=patient_contract_json,
        encounter_contract_json=encounter_contract_json)
    if source != ("FHIR_G5_CANDIDATE_SOURCE_READONLY_P100_E5918_Q0_"
                  "APPROVAL_DELTA_PASS_20261104"):
        raise RuntimeError("HOLD_G5_CANDIDATE_G4_NOT_APPROVED")

    # Strict source Mapper + F2 preview already produced these frames. We
    # deliberately DO NOT invent missing clinical values or durable IDs.
    psha, p_rows = _candidate_delta_content(
        person_candidate, key="person_id", expected=scope.patient_count)
    vsha, v_rows = _candidate_delta_content(
        visit_candidate, key="visit_occurrence_id", expected=scope.encounter_count)
    _validate_candidate_rows(p_rows, v_rows, handoff)
    _verify_candidate_mapper_payload(
        mapper_result, person_candidate, visit_candidate, scope)
    exists = {key: _delta_snapshot_exists(spark, path) for key, path in paths.items()}
    if any(exists.values()) and not all(exists.values()):
        return "G5_CANDIDATE_VERIFY_READONLY_PARTIAL_OUTPUT"

    def reopened():
        person = spark.read.format("delta").load(paths["person"])
        visit = spark.read.format("delta").load(paths["visit"])
        # Same strict frame/DQ checks on independently persisted rows.
        if set(person.columns) != set(person_candidate.columns) or (
                set(visit.columns) != set(visit_candidate.columns)):
            raise RuntimeError("HOLD_G5_CANDIDATE_READBACK_SCHEMA_DRIFT")
        saved_p, rows_p = _candidate_delta_content(
            person, key="person_id", expected=scope.patient_count)
        saved_v, rows_v = _candidate_delta_content(
            visit, key="visit_occurrence_id", expected=scope.encounter_count)
        _validate_candidate_rows(rows_p, rows_v, handoff)
        if (saved_p != psha or saved_v != vsha):
            raise RuntimeError("HOLD_G5_CANDIDATE_DATA_BYTES_DRIFT")
        return saved_p, saved_v

    def approved():
        proof = spark.read.format("delta").load(paths["approval"]).collect()
        if len(proof) != 1:
            raise RuntimeError("HOLD_G5_CANDIDATE_APPROVAL_CARDINALITY")
        record = proof[0].asDict(recursive=True)
        required = {
            "scope_receipt_key": scope.receipt_key,
            "source_batch_id": scope.source_batch_id,
            "mapping_sha256": scope.mapping_sha256,
            "snapshot_fingerprint": scope.identity_snapshot_fingerprint,
            "person_count": scope.patient_count,
            "visit_count": scope.encounter_count,
            "person_sha256": psha,
            "visit_sha256": vsha,
            "status": "CANDIDATE_APPROVED",
        }
        if technical:
            required.update({
                "evidence_contract": "G5_TECHNICAL_F1F2_V1",
                "technical_evidence_sha256": technical_evidence_sha256,
            })
        else:
            required.update({
                "clinical_review_sha256": clinical_review_sha256,
                "license_review_sha256": license_review_sha256,
            })
        if record != required:
            raise RuntimeError("HOLD_G5_CANDIDATE_APPROVAL_DRIFT")
        return record

    if all(exists.values()):
        try:
            saved_p, saved_v = reopened()
            approved()
        except Exception:
            return "G5_CANDIDATE_HOLD_READBACK_OR_APPROVAL_CONFLICT"
        observation = ObservedCandidate(
            scope=scope, person_delta_exists=True, visit_delta_exists=True,
            approval_exists=True, person_count=scope.patient_count,
            visit_count=scope.encounter_count,
            person_content_sha256=saved_p, visit_content_sha256=saved_v,
            approval_status="CANDIDATE_APPROVED", independently_reopened=True,
            schema_keys_fk_verified=True,
        )
        choice = decide_candidate_publication(
            scope, (observation,), expected_person_content_sha256=psha,
            expected_visit_content_sha256=vsha)
        return ("G5_CANDIDATE_SKIP_VERIFIED_NOT_GOLD" if
                choice.decision == "SKIP_VERIFIED_CANDIDATE_ONLY" else
                "G5_CANDIDATE_HOLD_REPLAY_CONFLICT")

    if mode != "G5_CANDIDATE_WRITE":
        return "G5_CANDIDATE_HOLD_NOT_FOUND_READONLY"
    if (decide_candidate_publication(scope, ()).decision
            != "PLAN_NEW_OFFLINE_ONLY"):
        return "G5_CANDIDATE_HOLD_PUBLICATION_PLAN"
    # The coordinator's review and authorization are still a separate
    # security gate; this code is not a dispatch entrypoint.
    try:
        _write_delta(person_candidate, paths["person"])
        _write_delta(visit_candidate, paths["visit"])
        reopened()  # independent physical two-Delta readback BEFORE approval
        if technical:
            receipt = (
                scope.receipt_key, scope.source_batch_id,
                scope.mapping_sha256, scope.identity_snapshot_fingerprint,
                "G5_TECHNICAL_F1F2_V1", technical_evidence_sha256,
                scope.patient_count, scope.encounter_count, psha, vsha,
                "CANDIDATE_APPROVED",
            )
            receipt_schema = (
                "scope_receipt_key string, source_batch_id string, "
                "mapping_sha256 string, snapshot_fingerprint string, "
                "evidence_contract string, technical_evidence_sha256 string, "
                "person_count long, visit_count long, person_sha256 string, "
                "visit_sha256 string, status string")
        else:
            # Historical signed-v1 readback stays byte/column compatible.
            receipt = (
                scope.receipt_key, scope.source_batch_id,
                scope.mapping_sha256, scope.identity_snapshot_fingerprint,
                clinical_review_sha256, license_review_sha256,
                scope.patient_count, scope.encounter_count, psha, vsha,
                "CANDIDATE_APPROVED",
            )
            receipt_schema = (
                "scope_receipt_key string, source_batch_id string, "
                "mapping_sha256 string, snapshot_fingerprint string, "
                "clinical_review_sha256 string, license_review_sha256 string, "
                "person_count long, visit_count long, person_sha256 string, "
                "visit_sha256 string, status string")
        approval = spark.createDataFrame([receipt], receipt_schema)
        _write_delta(approval, paths["approval"])  # LAST
        approved()  # second independent readback
    except Exception:
        # Prior Delta may have committed before an unknown ACK; no cleanup,
        # overwrite or retry. Operator must run independent READBACK first.
        return "G5_CANDIDATE_VERIFY_READONLY_UNKNOWN_ACK"
    return "G5_CANDIDATE_APPROVED_DELTA_ONLY_NOT_GOLD"



def execute_g5_candidate_from_trusted_controller(
    spark, *, provider=None, mode: str, attestation_bytes: bytes | None = None,
) -> str:
    """P3.20 fail-closed Native transport-only preflight, NOT a business entry.

    Legacy duck-typed provider calls for "verified" clinical/license and
    six-table string-receipt bridge were never an authenticated trust boundary:
    a caller could forge all returned dictionaries. No caller-supplied
    provider is EVER allowed here.

    P3.19 remains OPEN: technical F1 source audit, F2 fresh transaction
    fence, managed provider keys, durable atomic nonce claim, and native
    Wheel Publish have not been accepted. The only eventual positive result
    from this function is SOURCE-ONLY verification, not Candidate or Gold.
    This method is NOT connected to Notebook run_mode or Pipeline dispatch.
    """
    # Reject write *before* inspecting any source/provider/proof/Spark object.
    if mode != "G5_CANDIDATE_READBACK_ONLY":
        raise RuntimeError("HOLD_G5_NATIVE_CANDIDATE_WRITE_OR_MODE_DISABLED")
    if provider is not None or spark is not None:
        raise RuntimeError("HOLD_G5_NATIVE_CALLER_PROVIDER_OR_SPARK_UNTRUSTED")
    if run_mode != "HALT" or write_authorized is not False:
        raise RuntimeError("HOLD_G5_NATIVE_RUN_MODE_OR_WRITE_FLAG")
    # The live effective Wheel is 0.1.7; the cross-source v3 technical
    # transport is available only in source 0.1.13. A future isolated,
    # independently verified 0.1.13 publish is required before import.
    # This remains SOURCE-ONLY even after a verified runtime upgrade.
    if engine_version != "0.1.13":
        raise RuntimeError("HOLD_G5_NATIVE_0113_TRANSPORT_WHEEL_NOT_PUBLISHED")
    if (not isinstance(attestation_bytes, bytes)
            or not 0 < len(attestation_bytes) <= 8192):
        raise RuntimeError("HOLD_G5_NATIVE_SIGNED_ATTESTATION_BYTES_MISSING")
    try:
        from healthcare_data_engine.security.provider_attestation import (
            TransportHold, VerifiedTransport, VerifiedTechnicalTransport,
            verify_native_handoff_source_only,
        )
    except ImportError:
        raise RuntimeError("HOLD_G5_NATIVE_SIGNED_VERIFIER_NOT_PUBLISHED") from None
    try:
        verified = verify_native_handoff_source_only(attestation_bytes)
    except TransportHold:
        raise RuntimeError("HOLD_G5_NATIVE_SIGNED_TRANSPORT_OR_REPLAY") from None
    if (not isinstance(verified, (VerifiedTransport, VerifiedTechnicalTransport))
            or verified.status not in (
                "G5_TRANSPORT_VERIFIED_SOURCE_ONLY_NOT_RELEASE_AUTHORITY",
                "G5_TECHNICAL_TRANSPORT_VERIFIED_SOURCE_ONLY_NOT_RELEASE",
                "G5_DYNAMIC_TECHNICAL_TRANSPORT_VERIFIED_SOURCE_ONLY_NOT_RELEASE")
            or verified.candidate_write_authorized is not False
            or verified.gold_committed is not False
            or verified.provisional_ids_persisted is not False):
        raise RuntimeError("HOLD_G5_NATIVE_NON_SOURCE_ONLY_ATTESTATION")
    # No provider calls, no source Silver read, no Concept/F2 SQL, no Candidate
    # writer, and NO capability is returned to execute_g5_person_visit_business.
    return "G5_NATIVE_ATTESTATION_SOURCE_ONLY_VERIFIED_NOT_DISPATCHED"


def execute_g5_person_visit_business(
    spark, *, scope, handoff, concepts_from_verified_warehouse,
    mapping_profile_bytes: bytes, raw_publish_run_id: str,
    patient_contract_json: str, encounter_contract_json: str,
    mode: str, write_authorized: bool,
    clinically_reviewed: bool = False, license_reviewed: bool = False,
    warehouse_snapshot_verified: bool,
    clinical_review_sha256: str | None = None,
    license_review_sha256: str | None = None,
    warehouse_snapshot_sha256: str,
    technical_evidence_sha256: str | None = None,
    trusted_technical_release_gate: Callable | None = None,
) -> str:
    """P3 physical Silver -> the ONE Shared Mapper -> technical Candidate Delta.

    Current path uses verified technical F1/F2 source evidence, not two human
    Clinical/License signatures. An untrusted SHA/Boolean from Notebook
    parameters still cannot grant writes: the protected Stage owner must
    supply an independent release gate; __main__/Pipeline remain HALT.
    """
    from healthcare_data_engine.mapping.omop.candidates import (
        build_omop_candidates, load_omop_mapping_profile)
    from healthcare_data_engine.mapping.omop.candidate_publication import (
        FrozenCandidateScope, PersonVisitCandidateHandoff,
        freeze_candidate_scope)
    if (engine_version != "0.1.7"
            or not isinstance(scope, FrozenCandidateScope)
            or not isinstance(handoff, PersonVisitCandidateHandoff)
            or scope.source_batch_id != handoff.source_batch_id
            or scope.identity_snapshot_fingerprint != handoff.snapshot_fingerprint
            or scope.mapping_sha256 is None
            or mode not in ("G5_CANDIDATE_WRITE", "G5_CANDIDATE_READBACK_ONLY")):
        raise RuntimeError("HOLD_G5_BUSINESS_RELEASE_OR_F2_SCOPE")
    # Preserve clinical data integrity but do not require two humans.
    # A digest by itself is NEVER a release; the actual Stage owner must
    # independently authenticate it and provide the protected callback.
    technical = technical_evidence_sha256 is not None
    if technical and (clinically_reviewed or license_reviewed
                      or clinical_review_sha256 is not None
                      or license_review_sha256 is not None):
        raise RuntimeError("HOLD_G5_BUSINESS_FAKE_REVIEW_IN_TECHNICAL_PATH")
    if technical and (not isinstance(technical_evidence_sha256, str)
                      or not __import__("re").fullmatch(
                          r"[0-9a-f]{64}", technical_evidence_sha256)):
        raise RuntimeError("HOLD_G5_BUSINESS_TECHNICAL_EVIDENCE_SHA_INVALID")
    if mode == "G5_CANDIDATE_WRITE" and not (
            write_authorized and warehouse_snapshot_verified
            and ((technical and callable(trusted_technical_release_gate))
                 or (not technical and clinically_reviewed and license_reviewed))):
        raise RuntimeError("HOLD_G5_BUSINESS_TECHNICAL_STAGE_RELEASE_MISSING")
    if (not isinstance(mapping_profile_bytes, bytes)
            or len(mapping_profile_bytes) > 65536
            or hashlib.sha256(mapping_profile_bytes).hexdigest()
                != scope.mapping_sha256):
        raise RuntimeError("HOLD_G5_BUSINESS_MAPPING_PROFILE_BYTES")
    # Strict existing Mapper validates the exact source namespace and all
    # mapped concept IDs. It never guesses unmatched Race/Ethnicity/Visit.
    load_omop_mapping_profile(
        mapping_profile_bytes, scope.mapping_sha256, scope.source_system)
    if (not isinstance(raw_publish_run_id, str)
            or not raw_publish_run_id
            or raw_publish_run_id != raw_publish_run_id.strip()):
        raise RuntimeError("HOLD_G5_BUSINESS_RAW_PUBLICATION_UNPINNED")
    # Only ever read the physical G4 DataFrames after rechecking exact
    # original Manifest, Approval, row counts, source keys and FK.
    verify_fhir_g5_candidate_source_readonly(
        spark, request=scope.request_id,
        manifest_sha=scope.manifest_sha256,
        allow_write=False, retention_ok=False,
        strategy="DELTA_RAW_SNAPSHOT_V1",
        manifest_override="", source_override="", target_override="",
        patient_contract_json=patient_contract_json,
        encounter_contract_json=encounter_contract_json)
    paths = _silver_publication_paths(scope.request_id)
    patient = spark.read.format("delta").load(paths["patient"])
    encounter = spark.read.format("delta").load(paths["encounter"])
    approval_rows = spark.read.format("delta").load(paths["approval"]).collect()
    if len(approval_rows) != 1:
        raise RuntimeError("HOLD_G5_BUSINESS_G4_APPROVAL_NOT_UNIQUE")
    approval = approval_rows[0].asDict(recursive=True)
    if (approval.get("status") != "SILVER_APPROVED"
            or approval.get("publication_id") != scope.silver_publication_id
            or approval.get("source_batch_id") != scope.source_batch_id
            or approval.get("manifest_sha256") != scope.manifest_sha256
            or approval.get("processing_version") != scope.silver_processing_version
            or approval.get("patient_count") != scope.patient_count
            or approval.get("encounter_count") != scope.encounter_count
            or approval.get("quarantine_count") != 0):
        raise RuntimeError("HOLD_G5_BUSINESS_G4_APPROVAL_DRIFT")
    if (concepts_from_verified_warehouse is None
            or not hasattr(concepts_from_verified_warehouse, "columns")):
        raise RuntimeError("HOLD_G5_BUSINESS_F1_CONCEPT_SNAPSHOT_MISSING")
    # F2 provisional IDs stay explicit and are never persisted as Warehouse
    # Gold or treated as existing committed etl.identity_map records.
    if not handoff.person_lookup or not handoff.batch_visits:
        raise RuntimeError("HOLD_G5_BUSINESS_F2_ID_LOOKUP_EMPTY")
    for person_id in (r.person_id for r in handoff.person_lookup):
        if type(person_id) is not int or not 0 < person_id <= 2147483647:
            raise RuntimeError("HOLD_G5_BUSINESS_PERSON_INT_RANGE")
    for item in handoff.batch_visits:
        if type(item.visit_occurrence_id) is not int or not (
                0 < item.visit_occurrence_id <= 2147483647):
            raise RuntimeError("HOLD_G5_BUSINESS_VISIT_INT_RANGE")
    id_map = spark.createDataFrame(
        [("PERSON", p.hospital_id, p.source_system,
          p.source_business_key, p.person_id) for p in handoff.person_lookup],
        "entity_type string, hospital_id string, source_system string, "
        "source_business_key string, omop_id int")
    mapped = build_omop_candidates(
        patient, encounter, id_map, concepts_from_verified_warehouse,
        approval=approval, hospital_id=scope.hospital_id,
        source_system=scope.source_system,
        source_batch_id=scope.source_batch_id,
        manifest_sha256=scope.manifest_sha256,
        processing_version=scope.silver_processing_version,
        mapping_profile_bytes=mapping_profile_bytes,
        mapping_profile_sha256=scope.mapping_sha256,
        raw_publish_run_id=raw_publish_run_id)
    if freeze_candidate_scope(
            handoff, mapped, feed_id=scope.feed_id,
            request_id=scope.request_id) != scope:
        raise RuntimeError("HOLD_G5_BUSINESS_MAPPER_F2_SCOPE_CONFLICT")
    # F2 proposes IDs, Shared Mapper owns every OMOP clinical data column.
    # Never rewrite mapped output fields in this native coordinator.
    persons = spark.createDataFrame(
        [(p.person_id, p.state) for p in handoff.batch_persons],
        "person_id int, identity_state string")
    visits = spark.createDataFrame(
        [(v.source_system, v.source_encounter_id,
          v.visit_occurrence_id, v.state, v.parent_state)
         for v in handoff.batch_visits],
        "source_system string, source_encounter_id string, "
        "visit_occurrence_id int, identity_state string, "
        "parent_identity_state string")
    candidate_person = mapped.person.join(persons, "person_id", "inner")
    candidate_visit = mapped.visit.join(
        visits, ["source_system", "source_encounter_id"], "inner")
    return plan_and_write_g5_candidate_delta(
        spark, scope=scope, handoff=handoff, mapper_result=mapped,
        person_candidate=candidate_person,
        visit_candidate=candidate_visit, mode=mode,
        write_authorized=write_authorized,
        clinically_reviewed=clinically_reviewed,
        license_reviewed=license_reviewed,
        warehouse_snapshot_verified=warehouse_snapshot_verified,
        clinical_review_sha256=clinical_review_sha256,
        license_review_sha256=license_review_sha256,
        warehouse_snapshot_sha256=warehouse_snapshot_sha256,
        patient_contract_json=patient_contract_json,
        encounter_contract_json=encounter_contract_json,
        technical_evidence_sha256=technical_evidence_sha256,
        trusted_technical_release_gate=trusted_technical_release_gate)



def verify_fhir_g5_candidate_source_readonly(
    spark, *, request: str, manifest_sha: str, allow_write: bool,
    retention_ok: bool, strategy: str, manifest_override: str,
    source_override: str, target_override: str,
    patient_contract_json: str, encounter_contract_json: str,
) -> str:
    """Physically re-open G4 Approved Silver; NO Candidate/Gold permissions.

    G4's verified source-byte and independent Delta readback remain the
    single authoritative source of clinical approval. G5 *then* reopens
    all three persisted Delta tables to check this handoff's exact batch,
    namespace, counts, uniqueness and Encounter-to-Patient FK. The result
    means SOURCE_READONLY_PASS, not an OMOP mapping/commit receipt.
    """
    if (request != _G5_APPROVED_REQUEST
            or manifest_sha != _G5_APPROVED_MANIFEST_SHA
            or engine_version != "0.1.7"
            or strategy != "DELTA_RAW_SNAPSHOT_V1"
            or allow_write is not False
            or retention_ok is not False
            or any(x != "" for x in (
                manifest_override, source_override, target_override))):
        raise RuntimeError("HOLD_G5_SOURCE_PIN_OR_READONLY_GATE")
    # Only the supplied exact Local canonical original bytes are accepted.
    if (not isinstance(patient_contract_json, str)
            or not isinstance(encounter_contract_json, str)
            or not 0 < len(patient_contract_json) <= 5000
            or not 0 < len(encounter_contract_json) <= 5000):
        raise RuntimeError("HOLD_G5_CANONICAL_CONTRACTS_REQUIRED")
    patient_bytes = patient_contract_json.encode("utf-8")
    encounter_bytes = encounter_contract_json.encode("utf-8")
    load_pinned_contract(patient_bytes, "patient")
    load_pinned_contract(encounter_bytes, "encounter")

    # G4 independently verifies delivered manifest bytes, Bronze snapshot,
    # re-computed canonical data, persisted Approval and Quarantine fence.
    # Existing approved G4 physical data is NEVER written/overwritten.
    g4 = verify_fhir_g4_silver(
        spark, request=request, manifest_sha=manifest_sha,
        mode="SILVER_READBACK_ONLY", allow_write=False,
        retention_ok=False, strategy=strategy,
        manifest_override="", source_override="", target_override="",
        patient_contract_json=patient_contract_json,
        encounter_contract_json=encounter_contract_json)
    if (g4.status != "SILVER_SKIP_VERIFIED"
            or g4.processing_version != _G4_PROCESSING
            or g4.metrics.get("patient") != _G5_APPROVED_PATIENTS
            or g4.metrics.get("encounter") != _G5_APPROVED_ENCOUNTERS
            or g4.metrics.get("quarantine_or_reject") != 0
            or not isinstance(g4.publication_id, str)
            or not g4.publication_id):
        raise RuntimeError("HOLD_G5_G4_PHYSICAL_APPROVAL_NOT_VERIFIED")

    # Independent new Spark physical scans, not the G4 in-memory frames.
    from pyspark.sql import functions as F
    paths = _silver_publication_paths(request)
    patient = spark.read.format("delta").load(paths["patient"])
    encounter = spark.read.format("delta").load(paths["encounter"])
    approvals = spark.read.format("delta").load(paths["approval"]).collect()
    if len(approvals) != 1:
        raise RuntimeError("HOLD_G5_APPROVAL_ROW_CARDINALITY")
    approval = approvals[0].asDict(recursive=True)
    expected = {
        "status": "SILVER_APPROVED",
        "source_batch_id": g4.source_batch_id,
        "manifest_sha256": manifest_sha,
        "processing_version": _G4_PROCESSING,
        "publication_id": g4.publication_id,
        "patient_count": _G5_APPROVED_PATIENTS,
        "encounter_count": _G5_APPROVED_ENCOUNTERS,
        "quarantine_count": 0,
        "patient_contract_sha256": hashlib.sha256(patient_bytes).hexdigest(),
        "encounter_contract_sha256": hashlib.sha256(encounter_bytes).hexdigest(),
        "source_preservation_strategy": "DELTA_RAW_SNAPSHOT_V1",
    }
    if approval != expected:
        raise RuntimeError("HOLD_G5_APPROVAL_FENCE_CHANGED")
    required_patient = {"source_system", "source_batch_id", "source_record_id"}
    required_encounter = {"source_system", "source_batch_id",
                          "source_encounter_id", "source_person_id"}
    if (not required_patient.issubset(patient.columns)
            or not required_encounter.issubset(encounter.columns)):
        raise RuntimeError("HOLD_G5_CANONICAL_COLUMNS_DRIFT")
    if (patient.count() != _G5_APPROVED_PATIENTS
            or encounter.count() != _G5_APPROVED_ENCOUNTERS):
        raise RuntimeError("HOLD_G5_SILVER_COUNTS_DRIFT")
    source_system = "synthea-fhir:" + _FHIR_SOURCE_HOSPITAL_ID + ":" + _FHIR_SOURCE_FEED_ID
    for frame, key, name in (
        (patient, "source_record_id", "PATIENT"),
        (encounter, "source_encounter_id", "ENCOUNTER"),
    ):
        if frame.filter(
            F.col("source_system").isNull()
            | (F.col("source_system") != source_system)
            | F.col("source_batch_id").isNull()
            | (F.col("source_batch_id") != g4.source_batch_id)
            | F.col(key).isNull()
            | (F.trim(F.col(key)) == "")
        ).limit(1).count():
            raise RuntimeError("HOLD_G5_" + name + "_NAMESPACE_OR_KEY")
        if frame.groupBy("source_system", key).count().filter(
            "count != 1").limit(1).count():
            raise RuntimeError("HOLD_G5_" + name + "_DUPLICATE_SOURCE_KEY")
    if encounter.filter(
        F.col("source_person_id").isNull()
        | (F.trim(F.col("source_person_id")) == "")
    ).limit(1).count():
        raise RuntimeError("HOLD_G5_ENCOUNTER_PERSON_KEY_MISSING")
    if encounter.join(
        patient.select(
            F.col("source_system").alias("p_source_system"),
            F.col("source_record_id").alias("p_record_id")),
        (F.col("source_system") == F.col("p_source_system"))
        & (F.col("source_person_id") == F.col("p_record_id")),
        "left_anti"
    ).limit(1).count():
        raise RuntimeError("HOLD_G5_ENCOUNTER_PERSON_FK_ORPHAN")

    # Intentionally no Candidate Delta or Warehouse/ID/Concept access.
    return "FHIR_G5_CANDIDATE_SOURCE_READONLY_P100_E5918_Q0_APPROVAL_DELTA_PASS_20261104"



def verify_fhir_g5_concept_source_inventory_readonly(spark, **read_only_args) -> str:
    """P1 real G4 Silver code inventory; NEVER maps IDs, Concepts or writes.

    Only run AFTER the exact G5 source physical gate has independently verified
    the G4 Manifest, Delta Patient/Encounter, one Approval and P100/E5918/Q0.
    Raw patient/encounter identifiers are NOT returned. Source codes are
    synthetic G4 terminology data, with bounded output and no clinical IDs.
    """
    accepted = verify_fhir_g5_candidate_source_readonly(
        spark, **read_only_args)
    if accepted != (
        "FHIR_G5_CANDIDATE_SOURCE_READONLY_P100_E5918_Q0_"
        "APPROVAL_DELTA_PASS_20261104"
    ):
        raise RuntimeError("HOLD_P1_SOURCE_PHYSICAL_GATE_NOT_VERIFIED")
    from pyspark.sql import functions as F
    paths = _silver_publication_paths(read_only_args["request"])
    patient = spark.read.format("delta").load(paths["patient"])
    encounter = spark.read.format("delta").load(paths["encounter"])
    approvals = spark.read.format("delta").load(paths["approval"]).collect()
    if len(approvals) != 1:
        raise RuntimeError("HOLD_P1_APPROVAL_CHANGED")
    approval = approvals[0].asDict(recursive=True)
    if (approval.get("status") != "SILVER_APPROVED"
            or approval.get("manifest_sha256") != _G5_APPROVED_MANIFEST_SHA
            or approval.get("processing_version") != _G4_PROCESSING
            or approval.get("patient_count") != _G5_APPROVED_PATIENTS
            or approval.get("encounter_count") != _G5_APPROVED_ENCOUNTERS
            or approval.get("quarantine_count") != 0):
        raise RuntimeError("HOLD_P1_APPROVAL_CHANGED")
    if patient.count() != _G5_APPROVED_PATIENTS or (
            encounter.count() != _G5_APPROVED_ENCOUNTERS):
        raise RuntimeError("HOLD_P1_SOURCE_ROW_COUNT_CHANGED")

    if "source_record_id" not in patient.columns or patient.filter(
        F.col("source_record_id").isNull()
        | (F.length(F.col("source_record_id")) > 50)
    ).limit(1).count():
        # Person.person_source_value in official CDM 5.4 is VARCHAR(50).
        raise RuntimeError("HOLD_P1_PERSON_SOURCE_VALUE_TOO_LONG_OR_NULL")
    roles = (
        ("gender_code", patient, _G5_APPROVED_PATIENTS),
        ("race_code", patient, _G5_APPROVED_PATIENTS),
        ("ethnicity_code", patient, _G5_APPROVED_PATIENTS),
        ("encounter_class", encounter, _G5_APPROVED_ENCOUNTERS),
        ("source_code", encounter, _G5_APPROVED_ENCOUNTERS),
    )
    counts = {}
    for field, frame, expected in roles:
        if field not in frame.columns:
            raise RuntimeError("HOLD_P1_CANONICAL_CODE_COLUMN_MISSING")
        pairs = frame.groupBy(field).count().collect()
        if not pairs or len(pairs) > 128:
            raise RuntimeError("HOLD_P1_SOURCE_CODE_CARDINALITY_UNBOUNDED")
        values, total, folded = {}, 0, set()
        for row in pairs:
            code, frequency = row[field], row["count"]
            if (not isinstance(code, str) or not code or code != code.strip()
                    or len(code) > 50 or any(ord(ch) < 32 for ch in code)):
                raise RuntimeError("HOLD_P1_SOURCE_CODE_INVALID_OR_TOO_LONG")
            if code.casefold() in folded:
                raise RuntimeError("HOLD_P1_SOURCE_CODE_COLLATION_CONFLICT")
            folded.add(code.casefold())
            if type(frequency) is not int or frequency <= 0:
                raise RuntimeError("HOLD_P1_SOURCE_CODE_FREQUENCY_INVALID")
            values[code] = frequency
            total += frequency
        if total != expected:
            raise RuntimeError("HOLD_P1_SOURCE_CODE_FREQUENCY_COUNT_DRIFT")
        counts[field] = dict(sorted(values.items()))

    source_system = "synthea-fhir:" + _FHIR_SOURCE_HOSPITAL_ID + ":" + _FHIR_SOURCE_FEED_ID
    payload = json.dumps({
        "status": "P1_G4_CODE_INVENTORY_PHYSICAL_READONLY_ONLY",
        "request_id": read_only_args["request"],
        "delivered_manifest_sha256": _G5_APPROVED_MANIFEST_SHA,
        "source_batch_id": approval["source_batch_id"],
        "processing_version": _G4_PROCESSING,
        "source_system": source_system,
        "hospital_id": _FHIR_SOURCE_HOSPITAL_ID,
        "patient_count": _G5_APPROVED_PATIENTS,
        "encounter_count": _G5_APPROVED_ENCOUNTERS,
        "code_counts": counts,
    }, sort_keys=True, separators=(",", ":"))
    if len(payload.encode("utf-8")) > 16000:
        raise RuntimeError("HOLD_P1_SOURCE_INVENTORY_RECEIPT_TOO_LARGE")
    return "FHIR_G5_CONCEPT_SOURCE_INVENTORY_READONLY_PASS|" + payload

_G3_NEGATIVE_REQUEST = "atlanta-fhir-gh-41539769718"
_G3_NEGATIVE_MANIFEST_SHA = "2f9ef5a555f164464a79a5dc457a6d7f9ef79156edca11b2f1fb49789c785c35"


def verify_fhir_g3_negative_readonly(spark, *, request: str,
                                     manifest_sha: str, scenario: str,
                                     allow_write: bool, retention_ok: bool,
                                     strategy: str, manifest_override: str,
                                     source_override: str,
                                     target_override: str) -> str:
    """G3 synthetic counterfactual same-request drift and recovery probes.

    This does NOT mutate Azure Blob or Delta, nor claim actual Blob corruption.
    It applies a deliberately altered receipt to the ALREADY persisted real
    Fabric Delta path, after verifying the real original source bytes first.
    An independent readback after a hypothetical unknown ACK tests the
    recovery *mechanism*, not a real intercepted network ACK.
    """
    if (scenario not in ("BRONZE_DRIFT_PROBE", "BRONZE_ACK_RECOVERY_PROBE")
            or request != _G3_NEGATIVE_REQUEST
            or manifest_sha != _G3_NEGATIVE_MANIFEST_SHA
            or strategy != "DELTA_RAW_SNAPSHOT_V1"
            or allow_write is not False or retention_ok is not False
            or any(x != "" for x in (
                manifest_override, source_override, target_override))):
        raise RuntimeError("HOLD_G3_NEGATIVE_READONLY_GATES")
    original = verify_fhir_g3_bronze(
        spark, request=request, manifest_sha=manifest_sha,
        mode="BRONZE_READBACK_ONLY", allow_write=False,
        retention_ok=False, manifest_override="", source_override="",
        target_override="", strategy=strategy)
    if original.status != "BRONZE_SKIP_VERIFIED" or original.metrics["source_objects"] != 5:
        raise RuntimeError("HOLD_G3_NEGATIVE_BASELINE_DELTA_NOT_VERIFIED")
    path = _bronze_source_receipt_path(request)
    if scenario == "BRONZE_ACK_RECOVERY_PROBE":
        return "FHIR_G3_READONLY_ACK_RECOVERY_PATH_VERIFIED_5_DELTA_PASS_20261102"
    # Exercise the *physical* persisted row/byte comparison with an altered
    # receipt for this SAME request, not by mutating the Azure source object.
    rows = spark.read.format("delta").load(path).collect()
    expected = [{k: v for k, v in r.asDict(recursive=True).items()
                 if k != "source_payload"} for r in rows]
    altered = [{**r, "manifest_sha256": "f" * 64,
                "source_batch_id": "f" * 64} for r in expected]
    if _verify_bronze_receipt_readback(spark, path, altered):
        raise RuntimeError("HOLD_G3_DRIFT_WAS_NOT_REJECTED")
    return "FHIR_G3_COUNTERFACTUAL_REQUEST_DRIFT_HOLD_5_DELTA_PASS_20261102"


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

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# PARAMETERS CELL ********************

run_mode = "HALT"
manifest_sha256 = ""
source_preservation_strategy = "HALT"
write_authorized = False
retention_preflight_verified = False
request_id = ""
manifest_json = ""
source_root = ""
silver_root = ""
patient_contract_json = ""
encounter_contract_json = ""
dq_derivation_sha256 = ""

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark",
# META   "tags": [
# META     "parameters"
# META   ]
# META }

# CELL ********************

def validate_read_only_runtime_smoke(*, mode: str, allow_write: bool,
                                     retention_ok: bool, request: str,
                                     manifest: str, source: str,
                                     target: str) -> str:
    """Import-only Fabric smoke. No Spark action, Blob, Lakehouse or Delta I/O.

    This MUST remain distinct from the separately authorized ETL/write mode.
    HALT stays the default and every non-smoke mode is rejected.
    """
    if mode != "RUNTIME_SMOKE":
        raise RuntimeError("HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED")
    if (allow_write is not False or retention_ok is not False
            or any(value != "" for value in (request, manifest, source, target))):
        raise RuntimeError("HOLD_RUNTIME_SMOKE_UNSAFE_PARAMETERS")
    import pyspark
    if engine_version != "0.1.7":
        raise RuntimeError("HOLD_RUNTIME_SMOKE_WRONG_ENGINE_VERSION")
    if not pyspark.__version__.startswith("4.1."):
        raise RuntimeError("HOLD_RUNTIME_SMOKE_WRONG_SPARK_VERSION")
    if not callable(parse_fhir_resources) or not callable(normalize_fhir_patient):
        raise RuntimeError("HOLD_RUNTIME_SMOKE_ENGINE_IMPORT_INVALID")
    return "FHIR_BUSINESS_RUNTIME_SMOKE_ENGINE_017_SPARK41_PASS_20261107"


def _frozen_fhir_source_context(spark, request: str):
    """One pinned source-byte read for both independent read-only runtime modes."""
    from datetime import date, datetime, timezone

    frozen = {
        "atlanta-fhir-gh-40238053772":
            ("772bcc6bcce0ffc137df3af0602238f69db18f8418f62acbc865780957af6af7", 5),
        "atlanta-fhir-gh-40245591533":
            ("7f869bd9e9b9aefa4d6ddfebaf66ce011f53afa143d33b3731bc44dc53fa8c00", 100),
    }
    if not isinstance(request, str) or request not in frozen:
        raise RuntimeError("HOLD_FHIR_INTAKE_REQUEST_NOT_PINNED")
    if engine_version != "0.1.7":
        raise RuntimeError("HOLD_FHIR_INTAKE_WHEEL_MISMATCH")
    expected_manifest_sha, expected_objects = frozen[request]
    prefix = "Files/fhir_landing/clinical/v1/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/" + request
    raw_rows = spark.read.format("binaryFile").load(
        prefix + "/landing-manifest.json").select("content").collect()
    if len(raw_rows) != 1:
        raise RuntimeError("HOLD_FHIR_INTAKE_MANIFEST_NOT_ONE_FILE")
    raw_manifest = bytes(raw_rows[0].content)
    if hashlib.sha256(raw_manifest).hexdigest() != expected_manifest_sha:
        raise RuntimeError("HOLD_FHIR_INTAKE_REMOTE_MANIFEST_CHANGED")
    context = BatchContext(
        hospital_id="atlanta-hospital-a", feed_id="atlanta-hospital-a-fhir-r4",
        source_system="synthea-fhir", request_id=request,
        manifest_sha256=expected_manifest_sha,
        processing_version="fhir-intake-readonly-v1",
        processing_run_id="read-only:" + request,
        source_version="FHIR_R4",
        source_ingest_date=date(2026, 10, 25),
        processed_at=datetime.now(timezone.utc),
    )
    sources = read_source_objects_native(
        spark, source_root="Files/fhir_landing",
        manifest_bytes=raw_manifest, context=context)
    if len(sources) != expected_objects:
        raise RuntimeError("HOLD_FHIR_INTAKE_OBJECT_COUNT_MISMATCH")
    return context, raw_manifest, sources, expected_objects


def verify_fhir_intake_readonly(spark, *, request: str, allow_write: bool,
                                retention_ok: bool, manifest: str,
                                source: str, target: str) -> str:
    """Previously proven exact-byte, read-only FHIR source Intake."""
    if (allow_write is not False or retention_ok is not False
            or any(value != "" for value in (manifest, source, target))):
        raise RuntimeError("HOLD_FHIR_INTAKE_READONLY_PARAMETERS")
    context, _, sources, expected_objects = _frozen_fhir_source_context(spark, request)
    parsed = parse_fhir_resources(sources, context)
    patients = sum(r.resource_type == "Patient" for r in parsed.accepted)
    encounters = sum(r.resource_type == "Encounter" for r in parsed.accepted)
    if patients != expected_objects or encounters < expected_objects:
        raise RuntimeError("HOLD_FHIR_INTAKE_PATIENT_ENCOUNTER_COUNT")
    print("FHIR_INTAKE_OBJECTS_SHA_VERIFIED=" + str(len(sources)))
    print("FHIR_INTAKE_PATIENT_RESOURCES=" + str(patients))
    print("FHIR_INTAKE_ENCOUNTER_RESOURCES=" + str(encounters))
    print("FHIR_INTAKE_NONCANONICAL_OR_REJECTED=" + str(len(parsed.rejected)))
    return ("FHIR_INTAKE_READONLY_" + str(expected_objects)
            + "_SPARK_SOURCE_SHA_PASS_20261102")


def verify_fhir_canonical_readonly(spark, *, request: str, allow_write: bool,
                                   retention_ok: bool, manifest: str,
                                   source: str, target: str,
                                   patient_contract_json: str,
                                   encounter_contract_json: str) -> str:
    """Real native Spark Canonical/DQ probe; NO persistence, Delta, or approval.

    Contracts are supplied from the existing Git-authoritative Local v1 files
    as exact UTF-8 text, then verified by the Shared Wheel's frozen SHA pins.
    Never fetch a mutable contract, invent missing clinical fields, or write.
    """
    if (allow_write is not False or retention_ok is not False
            or any(value != "" for value in (manifest, source, target))):
        raise RuntimeError("HOLD_FHIR_CANONICAL_READONLY_UNSAFE_PARAMETERS")
    if (not isinstance(patient_contract_json, str)
            or not isinstance(encounter_contract_json, str)
            or not 0 < len(patient_contract_json) <= 5000
            or not 0 < len(encounter_contract_json) <= 5000):
        raise RuntimeError("HOLD_FHIR_CANONICAL_CONTRACT_INPUT_INVALID")
    # Verify hashes BEFORE any Blob/Shortcut reads.
    patient_bytes, encounter_bytes = (
        patient_contract_json.encode("utf-8"),
        encounter_contract_json.encode("utf-8"))
    load_pinned_contract(patient_bytes, "patient")
    load_pinned_contract(encounter_bytes, "encounter")

    from dataclasses import replace
    context, manifest_bytes, sources, expected_objects = _frozen_fhir_source_context(
        spark, request)
    context = replace(
        context, processing_version="fhir-canonical-readonly-v1",
        processing_run_id="canonical-readonly:" + request)
    batch = prepare_batch(
        spark, context=context, manifest_bytes=manifest_bytes,
        source_objects=sources, patient_contract_bytes=patient_bytes,
        encounter_contract_bytes=encounter_bytes)
    validate_silver_readback(batch.patient_df, batch.encounter_df, batch, context)
    summary = {}
    for finding in batch.findings:
        summary[finding.reason] = summary.get(finding.reason, 0) + 1
    print("FHIR_CANONICAL_READONLY_PATIENTS=" + str(batch.patient_count))
    print("FHIR_CANONICAL_READONLY_ENCOUNTERS=" + str(batch.encounter_count))
    print("FHIR_CANONICAL_READONLY_QUARANTINE_OR_REJECT=" + str(len(batch.findings)))
    print("FHIR_CANONICAL_READONLY_REASON_COUNTS="
          + json.dumps(summary, sort_keys=True, separators=(",", ":")))
    # DQ HOLD remains a Completed diagnostic, not an approved Silver release.
    if (batch.findings or batch.patient_count != expected_objects
            or batch.encounter_count < expected_objects):
        return (f"FHIR_CANONICAL_READONLY_{expected_objects}_DQ_HOLD_"
                f"P{batch.patient_count}_E{batch.encounter_count}_"
                f"Q{len(batch.findings)}_20261102")
    return f"FHIR_CANONICAL_READONLY_{expected_objects}_SPARK_PK_FK_PASS_20261102"


# Semantic public call sites. Keep the established legacy function objects
# callable under their historical names for fixed Workflow/Notebook consumers;
# alias identity preserves signatures, guards, Stage authority, and exceptions.
process_fhir_bronze_snapshot = verify_fhir_g3_bronze
process_fhir_silver_publication = verify_fhir_g4_silver
verify_fhir_dynamic_silver_source_readonly = verify_fhir_g5_dynamic_silver_source_readonly
plan_and_write_omop_candidate_delta = plan_and_write_g5_candidate_delta
verify_candidate_transport_source_only = execute_g5_candidate_from_trusted_controller
execute_person_visit_candidate_publication = execute_g5_person_visit_business
verify_fhir_candidate_source_readonly = verify_fhir_g5_candidate_source_readonly
verify_fhir_concept_source_inventory_readonly = verify_fhir_g5_concept_source_inventory_readonly
verify_fhir_bronze_negative_readonly = verify_fhir_g3_negative_readonly

if __name__ == "__main__":
    if run_mode == "RUNTIME_SMOKE":
        smoke_exit = validate_read_only_runtime_smoke(
            mode=run_mode, allow_write=write_authorized,
            retention_ok=retention_preflight_verified, request=request_id,
            manifest=manifest_json, source=source_root, target=silver_root,
        )
        notebookutils.notebook.exit(smoke_exit)
    elif run_mode == "INTAKE_READONLY":
        intake_exit = verify_fhir_intake_readonly(
            spark, request=request_id, allow_write=write_authorized,
            retention_ok=retention_preflight_verified,
            manifest=manifest_json, source=source_root, target=silver_root,
        )
        notebookutils.notebook.exit(intake_exit)
    elif run_mode in ("BRONZE_RECEIPT", "BRONZE_READBACK_ONLY"):
        g3 = verify_fhir_g3_bronze(
            spark, request=request_id, manifest_sha=manifest_sha256,
            mode=run_mode, allow_write=write_authorized,
            retention_ok=retention_preflight_verified,
            manifest_override=manifest_json, source_override=source_root,
            target_override=silver_root,
            strategy=source_preservation_strategy)
        print("FHIR_G3_BRONZE_STATUS=" + g3.status)
        print("FHIR_G3_BRONZE_SOURCE_BATCH_ID=" + g3.source_batch_id)
        print("FHIR_G3_BRONZE_SOURCE_OBJECTS=" + str(g3.metrics["source_objects"]))
        print("FHIR_G3_BRONZE_DELTA_PATH=" + _bronze_source_receipt_path(request_id))
        if g3.status in ("BRONZE_WRITTEN", "BRONZE_SKIP_VERIFIED"):
            notebookutils.notebook.exit(
                "FHIR_G3_" + g3.status + "_" +
                str(g3.metrics["source_objects"]) + "_DELTA_READBACK_PASS_20261102")
        raise RuntimeError("HOLD_FHIR_G3_" + g3.status)
    elif run_mode in ("SILVER_DQ_QUARANTINE_WRITE", "SILVER_DQ_READBACK_ONLY"):
        dq = verify_fhir_g4_dq_negative(
            spark, request=request_id, manifest_sha=manifest_sha256,
            derivation_sha=dq_derivation_sha256, mode=run_mode,
            allow_write=write_authorized,
            retention_ok=retention_preflight_verified,
            strategy=source_preservation_strategy,
            manifest_override=manifest_json, source_override=source_root,
            target_override=silver_root, patient_contract_json=patient_contract_json,
            encounter_contract_json=encounter_contract_json)
        print("FHIR_G4_DQ_STATUS=" + dq.status)
        print("FHIR_G4_DQ_PATIENTS=" + str(dq.metrics["patient"]))
        print("FHIR_G4_DQ_ENCOUNTERS=" + str(dq.metrics["encounter"]))
        print("FHIR_G4_DQ_QUARANTINED=" +
              str(dq.metrics["quarantine_or_reject"]))
        print("FHIR_G4_DQ_PHYSICAL_PATH=" + _silver_publication_paths(request_id)["quarantine"])
        if dq.status in ("DQ_QUARANTINED", "DQ_READBACK_VERIFIED",
                         "DQ_SKIP_VERIFIED"):
            notebookutils.notebook.exit(
                f"FHIR_G4_{dq.status}_P{dq.metrics['patient']}_"
                f"E{dq.metrics['encounter']}_Q{dq.metrics['quarantine_or_reject']}_"
                "APPROVAL_DENIED_DELTA_PASS_20261102")
        raise RuntimeError("HOLD_FHIR_G4_" + dq.status)
    elif run_mode in ("SILVER_WRITE", "SILVER_READBACK_ONLY"):
        g4 = verify_fhir_g4_silver(
            spark, request=request_id, manifest_sha=manifest_sha256,
            mode=run_mode, allow_write=write_authorized,
            retention_ok=retention_preflight_verified,
            strategy=source_preservation_strategy,
            manifest_override=manifest_json, source_override=source_root,
            target_override=silver_root,
            patient_contract_json=patient_contract_json,
            encounter_contract_json=encounter_contract_json)
        print("FHIR_G4_SILVER_STATUS=" + g4.status)
        print("FHIR_G4_SILVER_SOURCE_BATCH_ID=" + g4.source_batch_id)
        print("FHIR_G4_SILVER_PUBLICATION_ID=" + str(g4.publication_id))
        print("FHIR_G4_SILVER_PATIENTS=" + str(g4.metrics["patient"]))
        print("FHIR_G4_SILVER_ENCOUNTERS=" + str(g4.metrics["encounter"]))
        print("FHIR_G4_SILVER_QUARANTINE=" + str(g4.metrics["quarantine_or_reject"]))
        print("FHIR_G4_SILVER_DELTA_PATHS=" +
              json.dumps(_silver_publication_paths(request_id), sort_keys=True))
        if g4.status in ("SILVER_APPROVED", "SILVER_SKIP_VERIFIED"):
            notebookutils.notebook.exit(
                f"FHIR_G4_{g4.status}_P{g4.metrics['patient']}_"
                f"E{g4.metrics['encounter']}_"
                f"Q{g4.metrics['quarantine_or_reject']}_DELTA_PASS_20261102")
        raise RuntimeError("HOLD_FHIR_G4_" + g4.status)
    elif run_mode in ("HL7_SILVER_WRITE", "HL7_SILVER_READBACK_ONLY"):
        hl7 = verify_hl7_real_silver(
            spark, request=request_id, manifest_sha=manifest_sha256,
            mode=run_mode, allow_write=write_authorized,
            retention_ok=retention_preflight_verified,
            strategy=source_preservation_strategy,
            manifest_override=manifest_json, source_override=source_root,
            target_override=silver_root, patient_contract_json=patient_contract_json,
            encounter_contract_json=encounter_contract_json)
        print("HL7_SILVER_STATUS=" + hl7.status)
        print("HL7_SILVER_SOURCE_BATCH=" + hl7.source_batch_id)
        print("HL7_SILVER_PUBLICATION=" + str(hl7.publication_id))
        print("HL7_SILVER_PATIENTS=" + str(hl7.metrics["patient"]))
        print("HL7_SILVER_ENCOUNTERS=" + str(hl7.metrics["encounter"]))
        print("HL7_SILVER_QUARANTINE=" + str(hl7.metrics["quarantine_or_reject"]))
        if hl7.status in ("SILVER_APPROVED", "SILVER_SKIP_VERIFIED"):
            notebookutils.notebook.exit(
                f"HL7_{hl7.status}_P{hl7.metrics['patient']}_"
                f"E{hl7.metrics['encounter']}_"
                f"Q{hl7.metrics['quarantine_or_reject']}_DELTA_PASS_20261108")
        raise RuntimeError("HOLD_HL7_SILVER_" + hl7.status)
    elif run_mode == "G5_CANDIDATE_SOURCE_READONLY":
        candidate_source_result = verify_fhir_candidate_source_readonly(
            spark, request=request_id, manifest_sha=manifest_sha256,
            allow_write=write_authorized,
            retention_ok=retention_preflight_verified,
            strategy=source_preservation_strategy,
            manifest_override=manifest_json,
            source_override=source_root,
            target_override=silver_root,
            patient_contract_json=patient_contract_json,
            encounter_contract_json=encounter_contract_json)
        notebookutils.notebook.exit(candidate_source_result)
    elif run_mode == "G5_CONCEPT_SOURCE_INVENTORY_READONLY":
        inventory_exit = verify_fhir_concept_source_inventory_readonly(
            spark, request=request_id, manifest_sha=manifest_sha256,
            allow_write=write_authorized,
            retention_ok=retention_preflight_verified,
            strategy=source_preservation_strategy,
            manifest_override=manifest_json,
            source_override=source_root,
            target_override=silver_root,
            patient_contract_json=patient_contract_json,
            encounter_contract_json=encounter_contract_json)
        notebookutils.notebook.exit(inventory_exit)
    elif run_mode in ("BRONZE_DRIFT_PROBE", "BRONZE_ACK_RECOVERY_PROBE"):
        result = verify_fhir_bronze_negative_readonly(
            spark, request=request_id, manifest_sha=manifest_sha256,
            scenario=run_mode, allow_write=write_authorized,
            retention_ok=retention_preflight_verified,
            strategy=source_preservation_strategy,
            manifest_override=manifest_json, source_override=source_root,
            target_override=silver_root)
        notebookutils.notebook.exit(result)
    elif run_mode == "CANONICAL_READONLY":
        canonical_exit = verify_fhir_canonical_readonly(
            spark, request=request_id, allow_write=write_authorized,
            retention_ok=retention_preflight_verified,
            manifest=manifest_json, source=source_root, target=silver_root,
            patient_contract_json=patient_contract_json,
            encounter_contract_json=encounter_contract_json,
        )
        notebookutils.notebook.exit(canonical_exit)
    else:
        raise RuntimeError("HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

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
    if engine_version != "0.1.3":
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
_G3_SOURCE_ROOT = "Files/fhir_landing"
_G3_BRONZE_ROOT = "Files/bronze/fhir_r4"
_G3_HOSPITAL = "atlanta-hospital-a"
_G3_FEED = "atlanta-hospital-a-fhir-r4"
_G3_PROCESSING = "fhir-bronze-raw-snapshot-v1:engine-0.1.1"


def _g3_receipt_path(request: str) -> str:
    import re
    if not isinstance(request, str) or not re.fullmatch(r"atlanta-fhir-gh-[0-9]{8,14}", request):
        raise RuntimeError("HOLD_G3_UNAPPROVED_REQUEST_NAMESPACE")
    return (f"{_G3_BRONZE_ROOT}/{_G3_HOSPITAL}/{_G3_FEED}/"
            f"{request}/bronze_source_snapshot")


def _g3_expected_receipts(context: BatchContext, specs: tuple[dict, ...]) -> list[dict]:
    return [
        {"source_path": x["path"], "source_sha256": x["sha256"],
         "source_size_bytes": x["size_bytes"],
         "source_batch_id": context.source_batch_id,
         "manifest_sha256": context.manifest_sha256.lower(),
         "processing_version": context.processing_version,
         "request_id": context.request_id}
        for x in specs
    ]


def _g3_delta_exists(spark, path: str) -> bool:
    # False is not permission to overwrite a corrupt or partial directory:
    # errorifexists below remains the last line of defense.
    from delta.tables import DeltaTable
    return DeltaTable.isDeltaTable(spark, path)


def _g3_independent_receipt_readback(spark, path: str, expected: list[dict]) -> bool:
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
    path = _g3_receipt_path(request)
    if (mode == "BRONZE_RECEIPT" and
            (allow_write is not True or retention_ok is not True)):
        raise RuntimeError("HOLD_G3_WRITE_OR_RETENTION_NOT_VERIFIED")
    if (mode == "BRONZE_READBACK_ONLY" and
            (allow_write is not False or retention_ok is not False)):
        raise RuntimeError("HOLD_G3_READBACK_FLAGS_NOT_READONLY")
    if (engine_version != "0.1.3" or not isinstance(manifest_sha, str)
            or len(manifest_sha) != 64 or
            any(c not in "0123456789abcdef" for c in manifest_sha)):
        raise RuntimeError("HOLD_G3_ENGINE_OR_MANIFEST_PIN_INVALID")

    from datetime import date, datetime, timezone
    context = BatchContext(
        hospital_id=_G3_HOSPITAL, feed_id=_G3_FEED,
        source_system="synthea-fhir", request_id=request,
        manifest_sha256=manifest_sha, processing_version=_G3_PROCESSING,
        processing_run_id="g3:" + request, source_version="FHIR_R4",
        source_ingest_date=date(2026, 11, 2),
        processed_at=datetime.now(timezone.utc))
    root = (f"{_G3_SOURCE_ROOT}/clinical/v1/{_G3_HOSPITAL}/"
            f"{_G3_FEED}/{request}/landing-manifest.json")
    manifest_rows = spark.read.format("binaryFile").load(root).select("content").collect()
    if len(manifest_rows) != 1:
        raise RuntimeError("HOLD_G3_MANIFEST_NOT_ONE_FILE")
    raw = bytes(manifest_rows[0].content)
    specs = _manifest_objects(raw, context)   # validates delivered manifest SHA
    if not 5 <= len(specs) <= 10:
        raise RuntimeError("HOLD_G3_NOT_A_5_TO_10_OBJECT_BATCH")
    expected = _g3_expected_receipts(context, specs)
    metrics = {"patient": 0, "encounter": 0, "quarantine_or_reject": 0,
               "source_objects": len(specs)}
    try:
        exists = _g3_delta_exists(spark, path)
    except Exception:
        return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                               context.processing_version, None, metrics,
                               ("Delta existence check uncertain",))
    if exists:
        try:
            correct = _g3_independent_receipt_readback(spark, path, expected)
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
            spark, source_root=_G3_SOURCE_ROOT, manifest_bytes=raw, context=context)
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
        if not _g3_independent_receipt_readback(spark, path, complete):
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
_G4_SILVER_ROOT = "Files/silver/fhir_r4"


def _g4_paths(request: str) -> dict[str, str]:
    _g3_receipt_path(request)  # namespace/path traversal validation
    digest = hashlib.sha256(_G4_PROCESSING.encode("utf-8")).hexdigest()
    prefix = (f"{_G4_SILVER_ROOT}/{_G3_HOSPITAL}/{_G3_FEED}/"
              f"{request}/processing={digest}")
    return {"bronze": _g3_receipt_path(request),
            "patient": prefix + "/canonical_patient",
            "encounter": prefix + "/canonical_encounter",
            "approval": prefix + "/silver_approval",
            "quarantine": prefix + "/quarantine"}


def _g4_approval_row(context: BatchContext, batch: PreparedBatch,
                     patient_contract_bytes: bytes,
                     encounter_contract_bytes: bytes) -> dict:
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
        "source_preservation_strategy": "DELTA_RAW_SNAPSHOT_V1",
        "status": "SILVER_APPROVED",
    }


def _g4_snapshot_source_objects(spark, path: str,
                                expected: list[dict],
                                context: BatchContext) -> tuple[SourceObject, ...]:
    if not _g3_independent_receipt_readback(spark, path, expected):
        raise ValueError("G4_BRONZE_SOURCE_BYTES_OR_RECEIPTS_CHANGED")
    # This is a NEW physical Delta scan, not reuse of the source input DataFrame.
    rows = spark.read.format("delta").load(path).collect()
    return tuple(SourceObject(
        source_file=r.source_path, payload=bytes(r.source_payload),
        sha256=r.source_sha256, size_bytes=r.source_size_bytes,
        hospital_id=context.hospital_id, feed_id=context.feed_id,
        source_system=context.source_system) for r in rows)


def _g4_validate_full_delta(expected, actual, name: str) -> None:
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


def _g4_independent_silver_readback(spark, paths: dict[str, str],
                                    context: BatchContext,
                                    manifest_bytes: bytes,
                                    expected_receipts: list[dict],
                                    patient_contract_bytes: bytes,
                                    encounter_contract_bytes: bytes) -> PreparedBatch:
    sources = _g4_snapshot_source_objects(
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
    _g4_validate_full_delta(batch.patient_df, patient, "patient")
    _g4_validate_full_delta(batch.encounter_df, encounter, "encounter")
    approvals = spark.read.format("delta").load(paths["approval"]).collect()
    expected_approval = _g4_approval_row(
        context, batch, patient_contract_bytes, encounter_contract_bytes)
    if (len(approvals) != 1 or
            approvals[0].asDict(recursive=True) != expected_approval):
        raise ValueError("G4_SILVER_APPROVAL_FENCE_INVALID")
    return batch



# G4.c physical Delta rejection of isolated synthetic missing-DOB source.
# Transform/conversion remains wholly inside Shared Engine 0.1.3.
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
    paths = _g4_paths(request)
    writable = mode == "SILVER_DQ_QUARANTINE_WRITE"
    if (allow_write is not writable or retention_ok is not writable
            or engine_version != "0.1.3"
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
        hospital_id=_G3_HOSPITAL, feed_id=_G3_FEED,
        source_system="synthea-fhir", request_id=request,
        manifest_sha256=manifest_sha, processing_version=_G4_PROCESSING,
        processing_run_id="g4:" + request, source_version="FHIR_R4",
        source_ingest_date=date(2026, 11, 2),
        processed_at=datetime.now(timezone.utc))
    source_file = (f"{_G3_SOURCE_ROOT}/clinical/v1/{_G3_HOSPITAL}/"
                   f"{_G3_FEED}/{request}/landing-manifest.json")
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
        exists = {key: _g3_delta_exists(spark, value)
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
            spark, source_root=_G3_SOURCE_ROOT,
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
            if _g3_delta_exists(spark, paths[k]):
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
    paths = _g4_paths(request)
    if ((mode == "SILVER_WRITE" and
         (allow_write is not True or retention_ok is not True))
            or (mode == "SILVER_READBACK_ONLY" and
                (allow_write is not False or retention_ok is not False))):
        raise RuntimeError("HOLD_G4_BOOLEAN_WRITE_GATES")
    if (engine_version != "0.1.3" or not isinstance(manifest_sha, str)
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
        hospital_id=_G3_HOSPITAL, feed_id=_G3_FEED,
        source_system="synthea-fhir", request_id=request,
        manifest_sha256=manifest_sha, processing_version=_G4_PROCESSING,
        processing_run_id="g4:" + request, source_version="FHIR_R4",
        source_ingest_date=date(2026, 11, 2),
        processed_at=datetime.now(timezone.utc))
    metrics = {"patient": 0, "encounter": 0, "source_objects": 100,
               "quarantine_or_reject": 0}
    root = (f"{_G3_SOURCE_ROOT}/clinical/v1/{_G3_HOSPITAL}/"
            f"{_G3_FEED}/{request}/landing-manifest.json")
    data = spark.read.format("binaryFile").load(root).select("content").collect()
    if len(data) != 1:
        raise RuntimeError("HOLD_G4_MANIFEST_SOURCE_NOT_ONE")
    manifest_raw = bytes(data[0].content)
    # Manifest changed => fail before any Delta read/write, not a new batch path.
    specs = _manifest_objects(manifest_raw, context)
    if len(specs) != 100:
        raise RuntimeError("HOLD_G4_SOURCE_NOT_100_OBJECTS")
    expected = _g3_expected_receipts(context, specs)
    try:
        exists = {k: _g3_delta_exists(spark, v) for k, v in paths.items()}
    except Exception:
        return NotebookOutcome("VERIFY_READONLY", context.source_batch_id,
                               context.processing_version, None, metrics,
                               ("G4 Delta path status uncertain",))
    if any(exists.values()):
        if exists["bronze"]:
            try:
                valid = _g3_independent_receipt_readback(
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
            batch = _g4_independent_silver_readback(
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
        spark, source_root=_G3_SOURCE_ROOT,
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
        if not _g3_independent_receipt_readback(
                spark, paths["bronze"], raw_records):
            raise ValueError("G4_POSTWRITE_RAW_SNAPSHOT_MISMATCH")
        _write_delta(batch.patient_df, paths["patient"])
        _write_delta(batch.encounter_df, paths["encounter"])
        p = spark.read.format("delta").load(paths["patient"])
        e = spark.read.format("delta").load(paths["encounter"])
        validate_silver_readback(p, e, batch, context)
        _g4_validate_full_delta(batch.patient_df, p, "patient")
        _g4_validate_full_delta(batch.encounter_df, e, "encounter")
        approval_row = _g4_approval_row(context, batch, pb, eb)
        fields = ("source_batch_id string, manifest_sha256 string, "
                  "processing_version string, publication_id string, "
                  "patient_count long, encounter_count long, quarantine_count long, "
                  "patient_contract_sha256 string, encounter_contract_sha256 string, "
                  "source_preservation_strategy string, status string")
        keys = [x.split()[0] for x in fields.split(", ")]
        approval = spark.createDataFrame(
            [tuple(approval_row[k] for k in keys)], fields)
        _write_delta(approval, paths["approval"])  # approval fence LAST
        _g4_independent_silver_readback(
            spark, paths, context, manifest_raw, expected, pb, eb)
    except Exception:
        return NotebookOutcome("VERIFY_READONLY", batch.source_batch_id,
                               batch.processing_version, None, metrics,
                               ("partial write/unknown ACK: independent READBACK_ONLY required",))
    return NotebookOutcome("SILVER_APPROVED", batch.source_batch_id,
                           batch.processing_version, batch.publication_id,
                           metrics, ())



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
    path = _g3_receipt_path(request)
    if scenario == "BRONZE_ACK_RECOVERY_PROBE":
        return "FHIR_G3_READONLY_ACK_RECOVERY_PATH_VERIFIED_5_DELTA_PASS_20261102"
    # Exercise the *physical* persisted row/byte comparison with an altered
    # receipt for this SAME request, not by mutating the Azure source object.
    rows = spark.read.format("delta").load(path).collect()
    expected = [{k: v for k, v in r.asDict(recursive=True).items()
                 if k != "source_payload"} for r in rows]
    altered = [{**r, "manifest_sha256": "f" * 64,
                "source_batch_id": "f" * 64} for r in expected]
    if _g3_independent_receipt_readback(spark, path, altered):
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
    if engine_version != "0.1.3":
        raise RuntimeError("HOLD_RUNTIME_SMOKE_WRONG_ENGINE_VERSION")
    if not pyspark.__version__.startswith("4.1."):
        raise RuntimeError("HOLD_RUNTIME_SMOKE_WRONG_SPARK_VERSION")
    if not callable(parse_fhir_resources) or not callable(normalize_fhir_patient):
        raise RuntimeError("HOLD_RUNTIME_SMOKE_ENGINE_IMPORT_INVALID")
    return "FHIR_BUSINESS_RUNTIME_SMOKE_ENGINE_013_SPARK41_PASS_20261104"


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
    if engine_version != "0.1.3":
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
        print("FHIR_G3_BRONZE_DELTA_PATH=" + _g3_receipt_path(request_id))
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
        print("FHIR_G4_DQ_PHYSICAL_PATH=" + _g4_paths(request_id)["quarantine"])
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
              json.dumps(_g4_paths(request_id), sort_keys=True))
        if g4.status in ("SILVER_APPROVED", "SILVER_SKIP_VERIFIED"):
            notebookutils.notebook.exit(
                f"FHIR_G4_{g4.status}_P{g4.metrics['patient']}_"
                f"E{g4.metrics['encounter']}_"
                f"Q{g4.metrics['quarantine_or_reject']}_DELTA_PASS_20261102")
        raise RuntimeError("HOLD_FHIR_G4_" + g4.status)
    elif run_mode in ("BRONZE_DRIFT_PROBE", "BRONZE_ACK_RECOVERY_PROBE"):
        result = verify_fhir_g3_negative_readonly(
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

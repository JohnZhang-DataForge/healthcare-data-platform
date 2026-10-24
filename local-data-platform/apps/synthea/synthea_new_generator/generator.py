"""Independent Synthea CSV/FHIR source generation with immutable local artifacts."""
from __future__ import annotations

import contextlib
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess

from .request import (GenerationBlocked, canonical_bytes, fingerprint, normalize)

MANIFEST_VERSION = "synthea-new-generation-manifest-v1"
COMPLETED = "SOURCE_GENERATED_VALIDATED"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_once(path: Path, document: dict) -> dict:
    """Durably create a complete immutable JSON document without replacing existing bytes."""
    payload = canonical_bytes(document)
    if path.is_symlink():
        raise GenerationBlocked("UNSAFE_FROZEN_RECORD")
    tmp = path.with_name("." + path.name + "." + secrets.token_hex(12))
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            pass
    finally:
        tmp.unlink(missing_ok=True)
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GenerationBlocked("CORRUPT_FROZEN_RECORD") from exc
    if existing != document:
        raise GenerationBlocked("IMMUTABLE_RECORD_CONFLICT")
    return existing


def build_command(request: dict, jar: Path, output: Path) -> list[str]:
    """Use native Synthea exporters only; output format and geography are caller-selected."""
    args = [
        "java", "-jar", str(jar),
        "-s", str(request["seed"]), "-cs", str(request["clinician_seed"]),
        "-p", str(request["population"]),
        "-r", request["reference_date"], "-e", request["reference_date"],
        "-o", "false",
        f"--exporter.baseDirectory={output}",
        f"--exporter.csv.export={'true' if 'CSV' in request['output_formats'] else 'false'}",
        "--exporter.csv.append_mode=false",
        "--exporter.csv.folder_per_run=false",
        f"--exporter.fhir.export={'true' if 'FHIR_R4' in request['output_formats'] else 'false'}",
        "--exporter.fhir_stu3.export=false",
        "--exporter.fhir_dstu2.export=false",
        "--exporter.hospital.fhir.export=false",
        "--exporter.practitioner.fhir.export=false",
        "--exporter.metadata.export=false",
        "--exporter.ccda.export=false",
        "--exporter.json.export=false",
        "--generate.thread_pool_size=1",
        "--generate.log_patients.detail=none",
        request["state"],
    ]
    if request["city"] is not None:
        args.append(request["city"])
    return args


def _csv_rows(path: Path) -> tuple[list[str], list[dict]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, restkey="_extra", restval=None)
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise GenerationBlocked("INVALID_CSV_HEADER")
            values = list(reader)
    except (UnicodeError, csv.Error) as exc:
        raise GenerationBlocked("INVALID_CSV_FILE") from exc
    if any("_extra" in x or any(v is None for v in x.values()) for x in values):
        raise GenerationBlocked("INVALID_CSV_ROW_SHAPE")
    return reader.fieldnames, values


def validate_payload(payload: Path, request: dict) -> dict:
    """Validate actual local outputs and derive manifest inventory; no network calls."""
    allowed = set(request["output_formats"])
    file_records = []
    metrics = {"csv_patient_rows": 0, "csv_encounter_rows": 0,
               "fhir_bundles": 0, "fhir_patients": 0, "fhir_encounters": 0}
    if not payload.is_dir() or payload.is_symlink():
        raise GenerationBlocked("MISSING_OUTPUT_DIR")
    all_files = sorted(p for p in payload.rglob("*") if p.is_file() or p.is_symlink())
    if not all_files:
        raise GenerationBlocked("EMPTY_OUTPUT")
    for file in all_files:
        if file.is_symlink() or not file.is_file():
            raise GenerationBlocked("UNSAFE_OUTPUT_FILE")
        relative = file.relative_to(payload)
        if any(part in ("", ".", "..") for part in relative.parts):
            raise GenerationBlocked("UNSAFE_OUTPUT_PATH")
        fmt = "CSV" if relative.parts[0] == "csv" else (
            "FHIR_R4" if relative.parts[0] == "fhir" else None)
        if fmt not in allowed or file.suffix.lower() != (".csv" if fmt == "CSV" else ".json"):
            raise GenerationBlocked("UNEXPECTED_OUTPUT_FORMAT")
        if file.stat().st_size <= 0:
            raise GenerationBlocked("EMPTY_OUTPUT_FILE")
        file_records.append({"path":relative.as_posix(), "format":fmt,
                             "size_bytes":file.stat().st_size, "sha256":sha256(file)})
    if "CSV" in allowed:
        patients = payload / "csv" / "patients.csv"
        encounters = payload / "csv" / "encounters.csv"
        if not patients.is_file() or not encounters.is_file():
            raise GenerationBlocked("MISSING_REQUIRED_CSV")
        p_header, p_rows = _csv_rows(patients)
        e_header, e_rows = _csv_rows(encounters)
        if "Id" not in p_header or "Id" not in e_header or "PATIENT" not in e_header:
            raise GenerationBlocked("MISSING_CSV_ID_COLUMNS")
        ids = [x["Id"] for x in p_rows]
        if not ids or any(not v for v in ids) or len(ids) != len(set(ids)):
            raise GenerationBlocked("INVALID_CSV_PATIENT_IDENTITIES")
        if any(not x["Id"] or x["PATIENT"] not in set(ids) for x in e_rows):
            raise GenerationBlocked("INVALID_CSV_ENCOUNTER_IDENTITIES")
        metrics["csv_patient_rows"] = len(p_rows)
        metrics["csv_encounter_rows"] = len(e_rows)
        # Check CSV row shape in optional files too.
        for file in all_files:
            if file.parent == payload / "csv" and file.suffix == ".csv":
                _csv_rows(file)
    if "FHIR_R4" in allowed:
        fhir_files = [f for f in all_files if f.relative_to(payload).parts[0] == "fhir"]
        if not fhir_files:
            raise GenerationBlocked("MISSING_FHIR_BUNDLES")
        for file in fhir_files:
            try:
                bundle = json.loads(file.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise GenerationBlocked("INVALID_FHIR_JSON") from exc
            if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
                raise GenerationBlocked("NOT_FHIR_BUNDLE")
            entries = bundle.get("entry")
            if not isinstance(entries, list):
                raise GenerationBlocked("INVALID_FHIR_ENTRIES")
            patients = set()
            encounters = []
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("resource"), dict):
                    raise GenerationBlocked("INVALID_FHIR_ENTRY")
                resource = entry["resource"]
                if resource.get("resourceType") == "Patient":
                    patients.add(entry.get("fullUrl"))
                    if resource.get("id"):
                        patients.add("Patient/" + resource["id"])
                    metrics["fhir_patients"] += 1
                elif resource.get("resourceType") == "Encounter":
                    encounters.append(resource)
                    metrics["fhir_encounters"] += 1
            if not patients:
                raise GenerationBlocked("FHIR_BUNDLE_WITHOUT_PATIENT")
            for encounter in encounters:
                subject = encounter.get("subject")
                if (not isinstance(subject, dict)
                        or not isinstance(subject.get("reference"), str)
                        or subject["reference"] not in patients):
                    raise GenerationBlocked("FHIR_ENCOUNTER_PATIENT_REFERENCE")
            metrics["fhir_bundles"] += 1
    if not any(x["format"] in allowed for x in file_records):
        raise GenerationBlocked("MISSING_REQUESTED_FILES")
    return {"files":file_records, "metrics":metrics}


@contextlib.contextmanager
def _lock(root: Path):
    if not root.is_dir() or root.is_symlink():
        raise GenerationBlocked("INVALID_STATE_ROOT")
    file = root / ".synthea-new-generator.lock"
    with file.open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def generate(root: Path, raw_request: dict, jar: Path, runner=subprocess.run) -> dict:
    """Produce or independently verify one immutable request; no downstream publication."""
    req = normalize(raw_request)
    if not jar.is_file():
        raise GenerationBlocked("SYNTHEA_JAR_MISSING")
    root = Path(root)
    with _lock(root):
        requests_base = root / "requests"
        if requests_base.is_symlink():
            raise GenerationBlocked("UNSAFE_REQUESTS_DIRECTORY")
        folder = requests_base / req["request_id"]
        if folder.is_symlink():
            raise GenerationBlocked("UNSAFE_REQUEST_DIRECTORY")
        folder.mkdir(parents=True, exist_ok=True)
        frozen = {"request":req, "request_sha256":fingerprint(req)}
        atomic_once(folder / "request.json", frozen)
        payload = folder / "payload"
        marker = folder / "generation-manifest.json"
        if marker.exists():
            if marker.is_symlink() or payload.is_symlink():
                raise GenerationBlocked("UNSAFE_COMPLETED_ASSET")
            actual = validate_payload(payload, req)
            expected = {"schema_version":MANIFEST_VERSION, "request_id":req["request_id"],
                        "request_sha256":fingerprint(req), "status":COMPLETED, **actual}
            atomic_once(marker, expected)
            return expected
        if payload.exists():
            raise GenerationBlocked("ORPHAN_PAYLOAD_WITHOUT_MANIFEST")
        stage = folder / (".attempt-" + secrets.token_hex(8))
        stage.mkdir()
        log = folder / (stage.name + ".log")
        try:
            with log.open("w", encoding="utf-8") as stream:
                result = runner(build_command(req, jar, stage), stdout=stream,
                                stderr=subprocess.STDOUT, check=False, timeout=1200)
            if result.returncode != 0:
                raise GenerationBlocked("SYNTHEA_EXECUTION_FAILED")
            actual = validate_payload(stage, req)
            stage.rename(payload)
            expected = {"schema_version":MANIFEST_VERSION, "request_id":req["request_id"],
                        "request_sha256":fingerprint(req), "status":COMPLETED, **actual}
            atomic_once(marker, expected)
            return expected
        except subprocess.TimeoutExpired as exc:
            raise GenerationBlocked("SYNTHEA_EXECUTION_TIMEOUT") from exc
        # Failed attempt output/log deliberately preserved; no READY marker is published.

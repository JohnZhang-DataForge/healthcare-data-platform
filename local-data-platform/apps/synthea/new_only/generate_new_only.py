#!/usr/bin/env python3
"""Standalone Synthea NEW_ONLY producer: durable request identity and local CSV.

Independent of Airflow, S3 and PostgreSQL. This stage intentionally DOES NOT
publish a READY manifest. Full authoritative source-ID validation and immutable
S3 publication must be added and verified before a batch can be consumed.
"""
from __future__ import annotations

import csv
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

PINNED_VERSION = "v3.3.0"
PINNED_COMMIT = "995cf2fd33e67918d4e33110d9f68ad248002221"
STATES = (
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
)
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{7,65}$")


class GateError(RuntimeError):
    pass


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda: h.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_once(path: Path, body: dict) -> dict:
    """Publish complete bytes by hard link; never replace existing identity."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(body, sort_keys=True, indent=2) + "\n").encode()
    temporary = path.parent / ("." + path.name + "." + secrets.token_hex(12))
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            pass
    finally:
        temporary.unlink(missing_ok=True)
    result = json.loads(path.read_text())
    # Reject wrong request identity or unexpected changes after a crash.
    return result


def new_params(request_id: str, now: dt.datetime | None = None) -> dict:
    if not ID_PATTERN.fullmatch(request_id):
        raise GateError("invalid generator request id")
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise GateError("timezone must be explicit")
    utc = now.astimezone(dt.timezone.utc)
    seed = secrets.randbelow(2**63 - 1) + 1
    clinician_seed = secrets.randbelow(2**63 - 1) + 1
    requested_population=os.environ.get("NEW_ONLY_TARGET_POPULATION")
    if requested_population is None:
        population=secrets.randbelow(100)+1
    else:
        if not re.fullmatch(r"[1-9][0-9]*",requested_population):
            raise GateError("invalid independent NEW_ONLY population override")
        population=int(requested_population)
        if not 1<=population<=100:
            raise GateError("NEW_ONLY target population outside 1..100")
    return {
        "generator": "synthea-new-only",
        "contract_version": "new-only-local-v1",
        "generation_request_id": request_id,
        "batch_id": "synthea-new-only-" + request_id,
        "created_utc": utc.isoformat(),
        "reference_date": utc.strftime("%Y%m%d"),
        "state": secrets.choice(STATES),
        "target_population": population,
        "seed": seed, "clinician_seed": clinician_seed,
        "synthea_version": PINNED_VERSION,
        "synthea_commit": PINNED_COMMIT,
    }


def freeze_params(root: Path, request_id: str, now=None) -> dict:
    if not ID_PATTERN.fullmatch(request_id):
        raise GateError("invalid generator request id")
    path = root / "new-only" / "requests" / request_id / "params.json"
    if path.is_file():
        result = json.loads(path.read_text())
    else:
        result = atomic_once(path, new_params(request_id, now))
    # An override can only initialize a NEW request; later replays must
    # reproduce its frozen parameter rather than silently changing it.
    requested=os.environ.get("NEW_ONLY_TARGET_POPULATION")
    if requested is not None:
        if not re.fullmatch(r"[1-9][0-9]*",requested) or not 1<=int(requested)<=100:
            raise GateError("invalid population override")
        if result.get("target_population")!=int(requested):
            raise GateError("immutable target population does not match request")
    if result.get("generation_request_id") != request_id or result.get("batch_id") != "synthea-new-only-" + request_id:
        raise GateError("immutable request identity mismatch")
    if (not isinstance(result.get("target_population"), int)
        or not 1 <= result["target_population"] <= 100
        or result.get("state") not in STATES
        or result.get("synthea_commit") != PINNED_COMMIT
        or not isinstance(result.get("seed"), int)
        or not isinstance(result.get("clinician_seed"), int)):
        raise GateError("persisted immutable params invalid")
    return result


def command(params: dict, jar: Path, output: Path) -> list[str]:
    return [
        "java", "-jar", str(jar), "-s", str(params["seed"]),
        "-cs", str(params["clinician_seed"]),
        "-p", str(params["target_population"]),
        "-r", params["reference_date"], "-e", params["reference_date"],
        "-o", "false",
        f"--exporter.baseDirectory={output}",
        "--exporter.csv.export=true",
        "--exporter.csv.append_mode=false",
        "--exporter.csv.folder_per_run=false",
        "--exporter.csv.excluded_files=patient_expenses.csv",
        "--exporter.years_of_history=0",
        "--exporter.metadata.export=false",
        "--exporter.ccda.export=false",
        "--exporter.fhir.export=false",
        "--exporter.fhir_stu3.export=false",
        "--exporter.fhir_dstu2.export=false",
        "--exporter.hospital.fhir.export=false",
        "--exporter.hospital.fhir_stu3.export=false",
        "--exporter.hospital.fhir_dstu2.export=false",
        "--exporter.practitioner.fhir.export=false",
        "--exporter.practitioner.fhir_stu3.export=false",
        "--exporter.practitioner.fhir_dstu2.export=false",
        "--exporter.groups.fhir.export=false",
        "--exporter.json.export=false",
        "--exporter.cpcds.export=false",
        "--exporter.bfd.export=false",
        "--exporter.cdw.export=false",
        "--exporter.text.export=false",
        "--exporter.clinical_note.export=false",
        "--exporter.symptoms.csv.export=false",
        "--exporter.symptoms.text.export=false",
        "--generate.thread_pool_size=1",
        "--generate.log_patients.detail=none",
        params["state"],
    ]


def validate_csv(directory: Path, contract: Path, population_limit: int = 100) -> dict:
    spec = json.loads(contract.read_text())
    files = spec["files"]
    names = {x["filename"] for x in files}
    if len(files) != 18 or len(names) != 18 or spec["source_version"] != PINNED_VERSION:
        raise GateError("unexpected historical 18-CSV contract")
    actual = {p.name for p in directory.glob("*.csv")}
    if actual != names:
        raise GateError("18-CSV inventory mismatch")
    summary = {}
    patient_ids = set()
    encounter_patients = set()
    for item in files:
        name = item["filename"]
        with (directory / name).open(newline="", encoding="utf-8-sig") as f:
            rows = csv.reader(f, strict=True)
            try:
                header = next(rows)
            except StopIteration:
                raise GateError("missing CSV header: " + name)
            if header != item["header"]:
                raise GateError("CSV header mismatch: " + name)
            count = 0
            for row in rows:
                count += 1
                if len(row) != len(header):
                    raise GateError("CSV column count mismatch: " + name)
                if name == "patients.csv":
                    uid = row[header.index("Id")]
                    if not uid or uid in patient_ids:
                        raise GateError("repeated/empty Person source ID")
                    patient_ids.add(uid)
                elif name == "encounters.csv":
                    encounter_patients.add(row[header.index("PATIENT")])
        summary[name] = {"rows": count, "sha256": sha(directory / name)}
    if not 1 <= len(patient_ids) <= population_limit:
        raise GateError("actual Person population outside 1..100")
    if summary["encounters.csv"]["rows"] < 1:
        raise GateError("no Encounter records; cannot create Person/Visit batch")
    if not encounter_patients.issubset(patient_ids):
        raise GateError("Encounter references missing Person")
    return {
        "actual_persons": len(patient_ids),
        "actual_encounters": summary["encounters.csv"]["rows"],
        "files": summary,
        "person_id_hashes": sorted(hashlib.sha256(("synthea-source:" + uid).encode()).hexdigest()
                                   for uid in patient_ids),
        "legacy_18_csv_nonempty_contract_applied": False,
        "publication_eligible": False,
    }


def guarded_registry_write(base: Path, request_id: str, hashes: list[str]) -> None:
    if not ID_PATTERN.fullmatch(request_id):
        raise GateError("invalid registry request id")
    registry = base / "registry"
    registry.mkdir(parents=True, exist_ok=True)
    ids = set(hashes)
    if len(ids) != len(hashes):
        raise GateError("duplicate source IDs in registry")
    for entry in registry.glob("*.json"):
        previous = json.loads(entry.read_text())
        prev = set(previous["person_id_hashes"])
        if entry.stem == request_id:
            if prev != ids:
                raise GateError("same request changed Person source IDs")
        elif ids & prev:
            raise GateError("new-only persisted source ID collision")
    frozen = atomic_once(registry / (request_id + ".json"),
                         {"generation_request_id": request_id, "person_id_hashes": hashes})
    if frozen.get("person_id_hashes") != hashes:
        raise GateError("registry conflict")


def run(root: Path, request_id: str, jar: Path, contract: Path) -> dict:
    if not root.is_dir() or not jar.is_file() or not contract.is_file():
        raise GateError("missing mounted persistent storage, Synthea JAR or contract")
    base = root / "new-only"
    base.mkdir(parents=True, exist_ok=True)
    # Global local-fs flock serializes request freezes, registry and publication gates.
    with (base / ".generator.lock").open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        params = freeze_params(root, request_id)
        request_dir = base / "requests" / request_id
        complete = request_dir / "validated.json"
        if complete.is_file():
            result = json.loads(complete.read_text())
            if result.get("generation_request_id") != request_id:
                raise GateError("existing validation marker identity mismatch")
            if not (request_dir / "csv" / "patients.csv").is_file():
                raise GateError("validation marker exists but CSV missing")
            checked = validate_csv(request_dir / "csv", contract)
            if checked["person_id_hashes"] != result["person_id_hashes"]:
                raise GateError("existing Person source IDs drifted")
            guarded_registry_write(base, request_id, checked["person_id_hashes"])
            print("NEW_ONLY_REPLAY=REUSED_FIXED_REQUEST")
            return result

        stage = request_dir / "staging"
        if stage.exists():
            shutil.rmtree(stage)  # Only THIS incomplete request under exclusive lock
        stage.mkdir(parents=True)
        with (request_dir / "synthea.log").open("w") as log:
            p = subprocess.run(command(params, jar, stage), stdout=log, stderr=subprocess.STDOUT, check=False)
        if p.returncode != 0:
            raise GateError("Synthea exited non-zero; details retained on PVC")
        csv_dir = stage / "csv"
        checked = validate_csv(csv_dir, contract)
        guarded_registry_write(base, request_id, checked["person_id_hashes"])
        final_csv = request_dir / "csv"
        if final_csv.exists():
            raise GateError("incomplete request has unexpected final CSV; fail closed")
        os.replace(csv_dir, final_csv)
        record = {
            "generation_request_id": request_id,
            "batch_id": params["batch_id"],
            "state": "LOCAL_CSV_VALIDATED_NOT_PUBLISHED",
            "params_sha256": sha(request_dir / "params.json"),
            **checked,
        }
        frozen = atomic_once(complete, record)
        if frozen != record:
            raise GateError("unexpected existing validation marker")
        print("NEW_ONLY_GENERATION=PASS")
        return record


def main() -> int:
    request_id = os.environ["GENERATION_REQUEST_ID"]
    root = Path(os.environ.get("SYNTHEA_STATE_ROOT", "/synthea-state")).resolve()
    jar = Path(os.environ.get("SYNTHEA_JAR", "/opt/synthea/synthea-with-dependencies.jar"))
    contract = Path(os.environ.get("SYNTHEA_CSV_CONTRACT", "/opt/healthcare/contracts/synthea/v3.3.0/csv-contract.json"))
    result = run(root, request_id, jar, contract)
    print("GENERATION_REQUEST_ID=" + request_id)
    print("BATCH_ID=" + result["batch_id"])
    print("PERSON_ROWS=" + str(result["actual_persons"]))
    print("ENCOUNTER_ROWS=" + str(result["actual_encounters"]))
    print("CSV_INVENTORY=" + str(len(result["files"])) + "/18")
    print("CSV_LOCAL_PERSISTENCE=PASS")
    print("S3_MANIFEST_PUBLICATION=NOT_STARTED")
    print("DATABASE_MUTATION=NO")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (GateError, BlockingIOError, OSError, KeyError, ValueError) as exc:
        print("NEW_ONLY_BLOCKED=" + str(exc).split("\n", 1)[0], file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

APP="${ROOT}/apps/task004/publish_synthea_landing.py"

TEMPLATE="${ROOT}/kubernetes/manifests/task004/synthea-generate-publish-job.yaml.tpl"

SECRET_SYNC="${ROOT}/scripts/task004/04b-sync-s3-secret-to-synthea.sh"

RUNNER="${ROOT}/scripts/task004/04c-run-synthea-generate-publish.sh"

TEST="${ROOT}/tests/task004/test_synthea_landing_publisher.py"

mkdir -p \
  "$(dirname "$APP")" \
  "$(dirname "$TEMPLATE")" \
  "$(dirname "$SECRET_SYNC")" \
  "$(dirname "$RUNNER")" \
  "$(dirname "$TEST")"

# ============================================================
# Publisher application
# ============================================================

cat > "$APP" <<'PY_APP'
#!/usr/bin/env python3

"""Publish one locally validated TASK004 Synthea batch to Landing.

Safety contract:
- input must already be LOCAL_VALIDATED_NOT_UPLOADED;
- existing payload is downloaded and SHA256-compared before writes;
- matching objects are reused;
- conflicting objects are never overwritten;
- only missing payload objects may be created;
- all 18 payload files are independently read back;
- manifest is published only after full payload verification;
- an existing verified manifest is reused;
- manifest + incomplete payload is corruption and is never repaired;
- final manifest is independently read back and validated;
- no PostgreSQL access exists in this module.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


EXPECTED_SOURCE = "synthea"
EXPECTED_SOURCE_VERSION = "v3.3.0"
EXPECTED_FILE_COUNT = 18


class PublishError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def utc_date() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y-%m-%d")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def atomic_json_write(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temporary = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")

        os.replace(
            temporary,
            path,
        )

    except Exception:
        try:
            os.unlink(
                temporary
            )
        except FileNotFoundError:
            pass
        raise


def canonical_json_bytes(
    payload: dict[str, Any],
) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def normalize_file(
    item: dict[str, Any],
) -> dict[str, Any]:
    return {
        "dataset":
            item["dataset"],
        "header":
            item["header"],
        "path":
            item["path"],
        "row_count":
            item["row_count"],
        "sha256":
            item["sha256"],
        "size_bytes":
            item["size_bytes"],
    }


def validate_ingest_date(
    value: str,
) -> None:
    try:
        parsed = dt.datetime.strptime(
            value,
            "%Y-%m-%d",
        )
    except ValueError as exc:
        raise PublishError(
            "ingest date must use YYYY-MM-DD"
        ) from exc

    if parsed.strftime(
        "%Y-%m-%d"
    ) != value:
        raise PublishError(
            "invalid ingest date"
        )


def validate_local_draft(
    draft: dict[str, Any],
    source_dir: Path,
    expected_batch_id: str,
) -> str:
    if (
        draft.get("status")
        != "LOCAL_VALIDATED_NOT_UPLOADED"
    ):
        raise PublishError(
            "draft status is not "
            "LOCAL_VALIDATED_NOT_UPLOADED"
        )

    if (
        draft.get("manifest_version")
        != "1.0"
    ):
        raise PublishError(
            "unexpected manifest_version"
        )

    if (
        draft.get("source")
        != EXPECTED_SOURCE
    ):
        raise PublishError(
            "unexpected source"
        )

    if (
        draft.get("source_version")
        != EXPECTED_SOURCE_VERSION
    ):
        raise PublishError(
            "unexpected source_version"
        )

    if (
        draft.get("batch_id")
        != expected_batch_id
    ):
        raise PublishError(
            "batch_id mismatch"
        )

    if (
        draft.get("expected_file_count")
        != EXPECTED_FILE_COUNT
    ):
        raise PublishError(
            "expected_file_count is not 18"
        )

    files = draft.get("files")

    if (
        not isinstance(files, list)
        or len(files) != EXPECTED_FILE_COUNT
    ):
        raise PublishError(
            "draft must contain exactly 18 files"
        )

    expected_names: list[str] = []

    fingerprint = hashlib.sha256()

    for item in sorted(
        files,
        key=lambda value: value["path"],
    ):
        normalized = normalize_file(
            item
        )

        path_value = normalized[
            "path"
        ]

        if not path_value.startswith(
            "payload/csv/"
        ):
            raise PublishError(
                "invalid payload path: "
                + path_value
            )

        filename = Path(
            path_value
        ).name

        if (
            path_value
            != "payload/csv/" + filename
        ):
            raise PublishError(
                "nested payload path forbidden: "
                + path_value
            )

        expected_names.append(
            filename
        )

        local_path = (
            source_dir
            / filename
        )

        if not local_path.is_file():
            raise PublishError(
                "missing local payload file: "
                + filename
            )

        actual_size = (
            local_path.stat().st_size
        )

        if (
            actual_size
            != normalized["size_bytes"]
        ):
            raise PublishError(
                "local size mismatch: "
                + filename
            )

        actual_sha = sha256_file(
            local_path
        )

        if (
            actual_sha
            != normalized["sha256"]
        ):
            raise PublishError(
                "local SHA256 mismatch: "
                + filename
            )

        if (
            not isinstance(
                normalized["row_count"],
                int,
            )
            or normalized["row_count"] <= 0
        ):
            raise PublishError(
                "invalid row_count: "
                + filename
            )

        fingerprint.update(
            (
                filename
                + "|"
                + normalized["sha256"]
                + "\n"
            ).encode("utf-8")
        )

    if (
        len(expected_names)
        != len(set(expected_names))
    ):
        raise PublishError(
            "duplicate payload filename"
        )

    actual_names = sorted(
        path.name
        for path in source_dir.glob(
            "*.csv"
        )
        if path.is_file()
    )

    if sorted(
        expected_names
    ) != actual_names:
        raise PublishError(
            "local CSV inventory differs "
            "from draft manifest"
        )

    source_parameters = draft.get(
        "source_parameters"
    )

    if not isinstance(
        source_parameters,
        dict,
    ):
        raise PublishError(
            "missing source_parameters"
        )

    population_size = (
        source_parameters.get(
            "population_size"
        )
    )

    patient = next(
        (
            item
            for item in files
            if item.get("dataset")
            == "patients"
        ),
        None,
    )

    if patient is None:
        raise PublishError(
            "patients dataset missing"
        )

    if (
        not isinstance(
            population_size,
            int,
        )
        or population_size <= 0
    ):
        raise PublishError(
            "invalid source population_size"
        )

    if (
        patient.get(
            "row_count"
        ) < population_size
    ):
        raise PublishError(
            "patients row count is less "
            "than population_size"
        )

    return fingerprint.hexdigest()


def resolve_batch_prefix(
    keys: list[str],
    root_prefix: str,
    batch_id: str,
    default_ingest_date: str,
) -> tuple[str, str, str]:
    validate_ingest_date(
        default_ingest_date
    )

    escaped_root = re.escape(
        root_prefix
    )

    escaped_batch = re.escape(
        batch_id
    )

    pattern = re.compile(
        rf"^"
        rf"{escaped_root}"
        rf"ingest_date=([^/]+)/"
        rf"batch_id={escaped_batch}/"
    )

    found: dict[str, str] = {}

    for key in keys:
        match = pattern.match(
            key
        )

        if not match:
            continue

        ingest_date = (
            match.group(1)
        )

        prefix = (
            root_prefix
            + f"ingest_date={ingest_date}/"
            + f"batch_id={batch_id}/"
        )

        found[prefix] = (
            ingest_date
        )

    if len(found) > 1:
        raise PublishError(
            "multiple Landing prefixes "
            "exist for the same batch_id"
        )

    if found:
        prefix = next(
            iter(found)
        )

        return (
            prefix,
            found[prefix],
            "REUSE_EXISTING_PREFIX",
        )

    prefix = (
        root_prefix
        + f"ingest_date={default_ingest_date}/"
        + f"batch_id={batch_id}/"
    )

    return (
        prefix,
        default_ingest_date,
        "CREATE_NEW_PREFIX",
    )


def expected_payload_keys(
    draft: dict[str, Any],
    batch_prefix: str,
) -> dict[str, dict[str, Any]]:
    return {
        batch_prefix + item["path"]:
            item
        for item in draft["files"]
    }


def inspect_batch_keys(
    draft: dict[str, Any],
    batch_prefix: str,
    remote_keys: list[str],
) -> tuple[
    set[str],
    bool,
]:
    expected = set(
        expected_payload_keys(
            draft,
            batch_prefix,
        )
    )

    manifest_key = (
        batch_prefix
        + "manifest.json"
    )

    allowed = (
        expected
        | {manifest_key}
    )

    unknown = sorted(
        set(remote_keys)
        - allowed
    )

    if unknown:
        raise PublishError(
            "unexpected object(s) inside "
            "batch prefix: "
            + ", ".join(unknown)
        )

    present = (
        set(remote_keys)
        & expected
    )

    return (
        present,
        manifest_key in remote_keys,
    )


def build_final_manifest(
    draft: dict[str, Any],
    ingest_date: str,
    landing_uri: str,
    verified_at: str,
    payload_fingerprint: str,
) -> dict[str, Any]:
    final = copy.deepcopy(
        draft
    )

    final["status"] = (
        "INTAKE_VERIFIED"
    )

    final["ingest_date"] = (
        ingest_date
    )

    final["ingested_at"] = (
        verified_at
    )

    final["landing_uri"] = (
        landing_uri
    )

    final["payload_fingerprint"] = (
        payload_fingerprint
    )

    final["verification"] = {
        "checksum_algorithm":
            "SHA256",
        "s3_readback":
            "PASS",
        "verified_at":
            verified_at,
        "verified_file_count":
            EXPECTED_FILE_COUNT,
    }

    return final


def validate_final_manifest(
    draft: dict[str, Any],
    final: dict[str, Any],
    ingest_date: str,
    landing_uri: str,
    payload_fingerprint: str,
) -> None:
    if (
        final.get("status")
        != "INTAKE_VERIFIED"
    ):
        raise PublishError(
            "existing manifest status "
            "is not INTAKE_VERIFIED"
        )

    for key in (
        "manifest_version",
        "source",
        "source_version",
        "batch_id",
        "payload_format",
        "expected_file_count",
        "source_parameters",
        "source_provenance",
        "contract",
    ):
        if (
            final.get(key)
            != draft.get(key)
        ):
            raise PublishError(
                "existing manifest field "
                "conflict: "
                + key
            )

    draft_files = sorted(
        (
            normalize_file(
                item
            )
            for item in draft["files"]
        ),
        key=lambda value:
            value["path"],
    )

    final_files = sorted(
        (
            normalize_file(
                item
            )
            for item in final.get(
                "files",
                []
            )
        ),
        key=lambda value:
            value["path"],
    )

    if (
        draft_files
        != final_files
    ):
        raise PublishError(
            "existing manifest file "
            "inventory/checksum conflict"
        )

    if (
        final.get("ingest_date")
        != ingest_date
    ):
        raise PublishError(
            "existing manifest ingest_date "
            "conflict"
        )

    if (
        final.get("landing_uri")
        != landing_uri
    ):
        raise PublishError(
            "existing manifest landing_uri "
            "conflict"
        )

    if (
        final.get(
            "payload_fingerprint"
        )
        not in (
            None,
            payload_fingerprint,
        )
    ):
        raise PublishError(
            "existing manifest payload "
            "fingerprint conflict"
        )

    verification = final.get(
        "verification"
    )

    if not isinstance(
        verification,
        dict,
    ):
        raise PublishError(
            "existing manifest missing "
            "verification"
        )

    if (
        verification.get(
            "verified_file_count"
        )
        != EXPECTED_FILE_COUNT
    ):
        raise PublishError(
            "existing manifest verified "
            "file count is not 18"
        )

    if (
        verification.get(
            "s3_readback"
        )
        != "PASS"
    ):
        raise PublishError(
            "existing manifest s3_readback "
            "is not PASS"
        )


class S3Client:

    def __init__(
        self,
        endpoint: str,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        self.endpoint = (
            endpoint.rstrip("/")
        )

        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key

        parsed = urllib.parse.urlparse(
            self.endpoint
        )

        if (
            parsed.scheme
            not in {"http", "https"}
            or not parsed.netloc
        ):
            raise PublishError(
                "invalid S3 endpoint"
            )

        self.host = parsed.netloc


    @staticmethod
    def _sign(
        key: bytes,
        message: str,
    ) -> bytes:
        return hmac.new(
            key,
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()


    def request(
        self,
        method: str,
        key: str = "",
        query: dict[str, str] | None = None,
        body: bytes | None = None,
        allowed: tuple[int, ...] = (200,),
    ) -> tuple[int, bytes]:

        payload = (
            body
            if body is not None
            else b""
        )

        payload_hash = (
            sha256_bytes(
                payload
            )
        )

        now = dt.datetime.now(
            dt.timezone.utc
        )

        amz_date = now.strftime(
            "%Y%m%dT%H%M%SZ"
        )

        date_stamp = now.strftime(
            "%Y%m%d"
        )

        raw_path = (
            "/" + self.bucket
        )

        if key:
            raw_path += (
                "/" + key
            )

        canonical_uri = (
            urllib.parse.quote(
                raw_path,
                safe="/-_.~",
            )
        )

        query_pairs: list[str] = []

        for query_key, query_value in sorted(
            (query or {}).items()
        ):
            query_pairs.append(
                urllib.parse.quote(
                    str(query_key),
                    safe="-_.~",
                )
                + "="
                + urllib.parse.quote(
                    str(query_value),
                    safe="-_.~",
                )
            )

        canonical_query = (
            "&".join(
                query_pairs
            )
        )

        canonical_headers = (
            f"host:{self.host}\n"
            f"x-amz-content-sha256:"
            f"{payload_hash}\n"
            f"x-amz-date:{amz_date}\n"
        )

        signed_headers = (
            "host;"
            "x-amz-content-sha256;"
            "x-amz-date"
        )

        canonical_request = (
            method
            + "\n"
            + canonical_uri
            + "\n"
            + canonical_query
            + "\n"
            + canonical_headers
            + "\n"
            + signed_headers
            + "\n"
            + payload_hash
        )

        algorithm = (
            "AWS4-HMAC-SHA256"
        )

        credential_scope = (
            f"{date_stamp}/"
            f"{self.region}/"
            "s3/aws4_request"
        )

        string_to_sign = (
            algorithm
            + "\n"
            + amz_date
            + "\n"
            + credential_scope
            + "\n"
            + sha256_bytes(
                canonical_request.encode(
                    "utf-8"
                )
            )
        )

        k_date = self._sign(
            (
                "AWS4"
                + self.secret_key
            ).encode("utf-8"),
            date_stamp,
        )

        k_region = self._sign(
            k_date,
            self.region,
        )

        k_service = self._sign(
            k_region,
            "s3",
        )

        k_signing = self._sign(
            k_service,
            "aws4_request",
        )

        signature = hmac.new(
            k_signing,
            string_to_sign.encode(
                "utf-8"
            ),
            hashlib.sha256,
        ).hexdigest()

        authorization = (
            algorithm
            + " Credential="
            + self.access_key
            + "/"
            + credential_scope
            + ", SignedHeaders="
            + signed_headers
            + ", Signature="
            + signature
        )

        url = (
            self.endpoint
            + canonical_uri
        )

        if canonical_query:
            url += (
                "?"
                + canonical_query
            )

        request = urllib.request.Request(
            url,
            data=(
                body
                if method in {
                    "PUT",
                    "POST",
                }
                else None
            ),
            method=method,
            headers={
                "Host":
                    self.host,
                "x-amz-content-sha256":
                    payload_hash,
                "x-amz-date":
                    amz_date,
                "Authorization":
                    authorization,
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=120,
            ) as response:
                status = response.status
                response_body = (
                    b""
                    if method == "HEAD"
                    else response.read()
                )

        except urllib.error.HTTPError as exc:
            status = exc.code

            response_body = (
                b""
                if method == "HEAD"
                else exc.read()
            )

        except OSError as exc:
            raise PublishError(
                "S3 request failed: "
                + str(exc)
            ) from exc

        if status not in allowed:
            detail = (
                response_body.decode(
                    "utf-8",
                    errors="replace",
                )[:1000]
            )

            raise PublishError(
                f"S3 {method} failed "
                f"status={status} "
                f"key={key!r} "
                f"body={detail!r}"
            )

        return (
            status,
            response_body,
        )


    def head_bucket(
        self,
    ) -> None:
        self.request(
            "HEAD",
            allowed=(200,),
        )


    def head_object(
        self,
        key: str,
    ) -> bool:
        status, _ = self.request(
            "HEAD",
            key=key,
            allowed=(
                200,
                404,
            ),
        )

        return status == 200


    def get_object(
        self,
        key: str,
    ) -> bytes:
        _, body = self.request(
            "GET",
            key=key,
            allowed=(200,),
        )

        return body


    def put_object(
        self,
        key: str,
        body: bytes,
    ) -> None:
        self.request(
            "PUT",
            key=key,
            body=body,
            allowed=(
                200,
                201,
                204,
            ),
        )


    def list_keys(
        self,
        prefix: str,
    ) -> list[str]:
        keys: list[str] = []

        continuation: str | None = (
            None
        )

        while True:
            query = {
                "list-type":
                    "2",
                "max-keys":
                    "1000",
                "prefix":
                    prefix,
            }

            if continuation:
                query[
                    "continuation-token"
                ] = continuation

            _, body = self.request(
                "GET",
                query=query,
                allowed=(200,),
            )

            root = ET.fromstring(
                body
            )

            page_keys = [
                element.text
                for element in root.iter()
                if (
                    element.tag.endswith(
                        "Key"
                    )
                    and element.text
                )
            ]

            keys.extend(
                page_keys
            )

            truncated = next(
                (
                    element.text
                    for element in root.iter()
                    if element.tag.endswith(
                        "IsTruncated"
                    )
                ),
                "false",
            )

            if (
                str(truncated).lower()
                != "true"
            ):
                break

            continuation = next(
                (
                    element.text
                    for element in root.iter()
                    if element.tag.endswith(
                        "NextContinuationToken"
                    )
                ),
                None,
            )

            if not continuation:
                raise PublishError(
                    "S3 listing truncated "
                    "without continuation token"
                )

        return sorted(
            set(keys)
        )


def publish_batch(
    client: S3Client,
    draft: dict[str, Any],
    source_dir: Path,
    batch_id: str,
    default_ingest_date: str,
    bucket: str,
) -> dict[str, Any]:

    payload_fingerprint = (
        validate_local_draft(
            draft,
            source_dir,
            batch_id,
        )
    )

    root_prefix = (
        f"source={draft['source']}/"
        f"source_version="
        f"{draft['source_version']}/"
    )

    client.head_bucket()

    root_keys = client.list_keys(
        root_prefix
    )

    (
        batch_prefix,
        ingest_date,
        prefix_mode,
    ) = resolve_batch_prefix(
        root_keys,
        root_prefix,
        batch_id,
        default_ingest_date,
    )

    landing_uri = (
        f"s3://{bucket}/"
        f"{batch_prefix}"
    )

    manifest_key = (
        batch_prefix
        + "manifest.json"
    )

    expected = (
        expected_payload_keys(
            draft,
            batch_prefix,
        )
    )

    before_keys = client.list_keys(
        batch_prefix
    )

    (
        present_payload,
        manifest_present,
    ) = inspect_batch_keys(
        draft,
        batch_prefix,
        before_keys,
    )

    reused = 0
    uploaded = 0

    # Existing payload bytes are independently read and hashed
    # BEFORE any write is attempted.
    for key in sorted(
        present_payload
    ):
        item = expected[key]

        remote_bytes = (
            client.get_object(
                key
            )
        )

        remote_sha = (
            sha256_bytes(
                remote_bytes
            )
        )

        if (
            remote_sha
            != item["sha256"]
        ):
            raise PublishError(
                "existing payload conflict; "
                "overwrite forbidden: "
                + key
            )

        reused += 1

    # A final manifest marks the batch immutable.
    # If it exists but payload is incomplete, fail and do not repair.
    if manifest_present:

        if (
            len(present_payload)
            != EXPECTED_FILE_COUNT
        ):
            raise PublishError(
                "INTAKE_VERIFIED manifest exists "
                "with incomplete payload; "
                "corruption detected; "
                "automatic repair forbidden"
            )

        remote_manifest_bytes = (
            client.get_object(
                manifest_key
            )
        )

        try:
            remote_manifest = (
                json.loads(
                    remote_manifest_bytes
                )
            )
        except Exception as exc:
            raise PublishError(
                "existing manifest is invalid JSON"
            ) from exc

        validate_final_manifest(
            draft,
            remote_manifest,
            ingest_date,
            landing_uri,
            payload_fingerprint,
        )

        return {
            "batch_id":
                batch_id,
            "ingest_date":
                ingest_date,
            "landing_uri":
                landing_uri,
            "manifest_uri":
                landing_uri
                + "manifest.json",
            "manifest_sha256":
                sha256_bytes(
                    remote_manifest_bytes
                ),
            "payload_fingerprint":
                payload_fingerprint,
            "prefix_mode":
                prefix_mode,
            "publish_mode":
                "REUSE_EXISTING",
            "reused_this_run":
                reused,
            "uploaded_this_run":
                0,
            "verified_file_count":
                EXPECTED_FILE_COUNT,
            "status":
                "INTAKE_VERIFIED",
        }

    # No manifest exists: create only missing payload.
    for key in sorted(
        set(expected)
        - present_payload
    ):
        item = expected[key]

        local_path = (
            source_dir
            / Path(
                item["path"]
            ).name
        )

        # Narrow race guard: if another writer created it
        # after the initial listing, verify rather than overwrite.
        if client.head_object(
            key
        ):
            current = (
                client.get_object(
                    key
                )
            )

            if (
                sha256_bytes(
                    current
                )
                != item["sha256"]
            ):
                raise PublishError(
                    "concurrent payload conflict; "
                    "overwrite forbidden: "
                    + key
                )

            reused += 1
            continue

        client.put_object(
            key,
            local_path.read_bytes(),
        )

        uploaded += 1

    # Mandatory full remote inventory after payload publication.
    payload_keys_after = (
        client.list_keys(
            batch_prefix
        )
    )

    (
        present_after,
        manifest_after_payload,
    ) = inspect_batch_keys(
        draft,
        batch_prefix,
        payload_keys_after,
    )

    if (
        len(present_after)
        != EXPECTED_FILE_COUNT
    ):
        raise PublishError(
            "remote payload count is not 18"
        )

    # If a concurrent writer published the manifest,
    # treat it as immutable and validate it.
    if manifest_after_payload:
        concurrent_manifest_bytes = (
            client.get_object(
                manifest_key
            )
        )

        concurrent_manifest = json.loads(
            concurrent_manifest_bytes
        )

        validate_final_manifest(
            draft,
            concurrent_manifest,
            ingest_date,
            landing_uri,
            payload_fingerprint,
        )

        return {
            "batch_id":
                batch_id,
            "ingest_date":
                ingest_date,
            "landing_uri":
                landing_uri,
            "manifest_uri":
                landing_uri
                + "manifest.json",
            "manifest_sha256":
                sha256_bytes(
                    concurrent_manifest_bytes
                ),
            "payload_fingerprint":
                payload_fingerprint,
            "prefix_mode":
                prefix_mode,
            "publish_mode":
                "REUSE_CONCURRENT_MANIFEST",
            "reused_this_run":
                reused,
            "uploaded_this_run":
                uploaded,
            "verified_file_count":
                EXPECTED_FILE_COUNT,
            "status":
                "INTAKE_VERIFIED",
        }

    # Mandatory independent readback of all 18 payload objects.
    for key in sorted(
        expected
    ):
        item = expected[key]

        remote = client.get_object(
            key
        )

        if (
            sha256_bytes(
                remote
            )
            != item["sha256"]
        ):
            raise PublishError(
                "S3 readback SHA256 mismatch: "
                + key
            )

    verified_at = utc_now()

    final_manifest = (
        build_final_manifest(
            draft,
            ingest_date,
            landing_uri,
            verified_at,
            payload_fingerprint,
        )
    )

    final_bytes = (
        canonical_json_bytes(
            final_manifest
        )
    )

    # Manifest is deliberately the LAST object created.
    if client.head_object(
        manifest_key
    ):
        existing_bytes = (
            client.get_object(
                manifest_key
            )
        )

        existing = json.loads(
            existing_bytes
        )

        validate_final_manifest(
            draft,
            existing,
            ingest_date,
            landing_uri,
            payload_fingerprint,
        )

        final_bytes = (
            existing_bytes
        )

        publish_mode = (
            "REUSE_CONCURRENT_MANIFEST"
        )

    else:
        client.put_object(
            manifest_key,
            final_bytes,
        )

        publish_mode = (
            "PUBLISHED_NEW"
        )

    # Final manifest remote readback is mandatory.
    remote_manifest_bytes = (
        client.get_object(
            manifest_key
        )
    )

    remote_manifest = json.loads(
        remote_manifest_bytes
    )

    validate_final_manifest(
        draft,
        remote_manifest,
        ingest_date,
        landing_uri,
        payload_fingerprint,
    )

    return {
        "batch_id":
            batch_id,
        "ingest_date":
            ingest_date,
        "landing_uri":
            landing_uri,
        "manifest_uri":
            landing_uri
            + "manifest.json",
        "manifest_sha256":
            sha256_bytes(
                remote_manifest_bytes
            ),
        "payload_fingerprint":
            payload_fingerprint,
        "prefix_mode":
            prefix_mode,
        "publish_mode":
            publish_mode,
        "reused_this_run":
            reused,
        "uploaded_this_run":
            uploaded,
        "verified_file_count":
            EXPECTED_FILE_COUNT,
        "status":
            "INTAKE_VERIFIED",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source-dir",
        required=True,
    )

    parser.add_argument(
        "--draft",
        required=True,
    )

    parser.add_argument(
        "--batch-id",
        required=True,
    )

    parser.add_argument(
        "--endpoint",
        required=True,
    )

    parser.add_argument(
        "--bucket",
        required=True,
    )

    parser.add_argument(
        "--region",
        default="us-east-1",
    )

    parser.add_argument(
        "--default-ingest-date",
        default=utc_date(),
    )

    parser.add_argument(
        "--report",
        required=True,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    access_key = os.environ.get(
        "AWS_ACCESS_KEY_ID"
    )

    secret_key = os.environ.get(
        "AWS_SECRET_ACCESS_KEY"
    )

    if not access_key:
        raise SystemExit(
            "ERROR: AWS_ACCESS_KEY_ID missing"
        )

    if not secret_key:
        raise SystemExit(
            "ERROR: AWS_SECRET_ACCESS_KEY missing"
        )

    source_dir = Path(
        args.source_dir
    ).resolve()

    draft = load_json(
        Path(
            args.draft
        ).resolve()
    )

    client = S3Client(
        endpoint=args.endpoint,
        bucket=args.bucket,
        region=args.region,
        access_key=access_key,
        secret_key=secret_key,
    )

    try:
        result = publish_batch(
            client,
            draft,
            source_dir,
            args.batch_id,
            args.default_ingest_date,
            args.bucket,
        )

    except PublishError as exc:
        print(
            "LANDING_PUBLICATION=FAIL"
        )

        print(
            "ERROR: "
            + str(exc)
        )

        return 1

    atomic_json_write(
        Path(
            args.report
        ).resolve(),
        result,
    )

    print(
        "LANDING_PUBLICATION=PASS"
    )

    print(
        "MANIFEST_STATUS="
        + result["status"]
    )

    print(
        "PUBLISH_MODE="
        + result["publish_mode"]
    )

    print(
        "PREFIX_MODE="
        + result["prefix_mode"]
    )

    print(
        "UPLOADED_THIS_RUN="
        + str(
            result[
                "uploaded_this_run"
            ]
        )
    )

    print(
        "REUSED_THIS_RUN="
        + str(
            result[
                "reused_this_run"
            ]
        )
    )

    print(
        "S3_PAYLOAD_READBACK_SHA256="
        + str(
            result[
                "verified_file_count"
            ]
        )
        + "/18"
    )

    print(
        "PAYLOAD_FINGERPRINT="
        + result[
            "payload_fingerprint"
        ]
    )

    print(
        "LANDING_URI="
        + result[
            "landing_uri"
        ]
    )

    print(
        "MANIFEST_URI="
        + result[
            "manifest_uri"
        ]
    )

    print(
        "MANIFEST_SHA256="
        + result[
            "manifest_sha256"
        ]
    )

    print(
        "POSTGRESQL_WRITE=NO"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
PY_APP

chmod 0755 "$APP"

# ============================================================
# Kubernetes generate + publish Job template
# ============================================================

cat > "$TEMPLATE" <<'YAML_TEMPLATE'
apiVersion: batch/v1
kind: Job

metadata:
  name: __JOB_NAME__
  namespace: dw-synthea

  labels:
    app.kubernetes.io/name: synthea-generator
    app.kubernetes.io/part-of: healthcare-data-platform
    healthcare-data-platform/task: task004
    healthcare-data-platform/runtime: generate-publish

spec:
  backoffLimit: 0

  template:
    metadata:
      labels:
        app.kubernetes.io/name: synthea-generator
        healthcare-data-platform/task: task004
        healthcare-data-platform/runtime: generate-publish

    spec:
      restartPolicy: Never
      automountServiceAccountToken: false

      nodeSelector:
        kubernetes.io/hostname: worker01

      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001

        seccompProfile:
          type: RuntimeDefault

      containers:
        - name: synthea-generator

          image: __IMAGE_REF_JSON__
          imagePullPolicy: IfNotPresent

          securityContext:
            allowPrivilegeEscalation: false

            capabilities:
              drop:
                - ALL

          resources:
            requests:
              cpu: "250m"
              memory: "1Gi"

            limits:
              cpu: "2"
              memory: "4Gi"

          envFrom:
            - secretRef:
                name: dw-synthea-s3-secret

          env:
            - name: BATCH_ID
              value: __BATCH_ID_JSON__

            - name: POPULATION_SIZE
              value: __POPULATION_SIZE_JSON__

            - name: SEED
              value: __SEED_JSON__

            - name: CLINICIAN_SEED
              value: __CLINICIAN_SEED_JSON__

            - name: REFERENCE_DATE
              value: __REFERENCE_DATE_JSON__

            - name: STATE
              value: __STATE_JSON__

            - name: CITY
              value: __CITY_JSON__

            - name: S3_ENDPOINT
              value: "http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333"

            - name: S3_BUCKET_LANDING
              value: "health-landing"

            - name: AWS_DEFAULT_REGION
              value: "us-east-1"

            - name: LANDING_INGEST_DATE
              value: __INGEST_DATE_JSON__

          volumeMounts:
            - name: publisher-source
              mountPath: /opt/task004
              readOnly: true

          command:
            - /bin/bash
            - -lc

          args:
            - |
              set -Eeuo pipefail

              echo "TASK004_GENERATE_PUBLISH_CONTAINER_START=YES"

              /usr/local/bin/healthcare-synthea-generator

              python3 \
                /opt/task004/publish_synthea_landing.py \
                --source-dir /work/output/csv \
                --draft /work/evidence/manifest.draft.json \
                --batch-id "$BATCH_ID" \
                --endpoint "$S3_ENDPOINT" \
                --bucket "$S3_BUCKET_LANDING" \
                --region "$AWS_DEFAULT_REGION" \
                --default-ingest-date "$LANDING_INGEST_DATE" \
                --report /work/evidence/landing-publication.json

              echo "TASK004_GENERATE_PUBLISH_RUNTIME=PASS"

      volumes:
        - name: publisher-source
          configMap:
            name: __CONFIGMAP_NAME__
YAML_TEMPLATE

# ============================================================
# Secret sync script
# ============================================================

cat > "$SECRET_SYNC" <<'SECRET_SYNC_SCRIPT'
#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_NAMESPACE="dw-spark"
SOURCE_SECRET="dw-spark-s3-secret"

TARGET_NAMESPACE="dw-synthea"
TARGET_SECRET="dw-synthea-s3-secret"

fail() {
  echo "ERROR=$*"
  exit 1
}

echo '#### TASK004 SYNTHEA S3 SECRET SYNC OUTPUT BEGIN ####'

kubectl get namespace \
  "$SOURCE_NAMESPACE" \
  >/dev/null \
  || fail "Source namespace missing"

kubectl get namespace \
  "$TARGET_NAMESPACE" \
  >/dev/null \
  || fail "Target namespace missing"

kubectl get secret \
  "$SOURCE_SECRET" \
  -n "$SOURCE_NAMESPACE" \
  >/dev/null \
  || fail "Source S3 secret missing"

SOURCE_KEYS="$(
  kubectl get secret \
    "$SOURCE_SECRET" \
    -n "$SOURCE_NAMESPACE" \
    -o go-template='{{range $key, $value := .data}}{{$key}}{{"\n"}}{{end}}' \
  | sort
)"

printf '%s\n' "$SOURCE_KEYS" \
  | grep -Fx "AWS_ACCESS_KEY_ID" \
  >/dev/null \
  || fail "Source access-key field missing"

printf '%s\n' "$SOURCE_KEYS" \
  | grep -Fx "AWS_SECRET_ACCESS_KEY" \
  >/dev/null \
  || fail "Source secret-key field missing"

ACCESS_KEY="$(
  kubectl get secret \
    "$SOURCE_SECRET" \
    -n "$SOURCE_NAMESPACE" \
    -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' \
  | base64 --decode
)"

SECRET_KEY="$(
  kubectl get secret \
    "$SOURCE_SECRET" \
    -n "$SOURCE_NAMESPACE" \
    -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' \
  | base64 --decode
)"

[[ -n "$ACCESS_KEY" ]] \
  || fail "Decoded access key is empty"

[[ -n "$SECRET_KEY" ]] \
  || fail "Decoded secret key is empty"

kubectl create secret generic \
  "$TARGET_SECRET" \
  -n "$TARGET_NAMESPACE" \
  --from-literal=AWS_ACCESS_KEY_ID="$ACCESS_KEY" \
  --from-literal=AWS_SECRET_ACCESS_KEY="$SECRET_KEY" \
  --dry-run=client \
  -o yaml \
| kubectl apply \
    -f - \
    >/dev/null

TARGET_ACCESS="$(
  kubectl get secret \
    "$TARGET_SECRET" \
    -n "$TARGET_NAMESPACE" \
    -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' \
  | base64 --decode
)"

TARGET_SECRET_VALUE="$(
  kubectl get secret \
    "$TARGET_SECRET" \
    -n "$TARGET_NAMESPACE" \
    -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' \
  | base64 --decode
)"

[[ "$TARGET_ACCESS" == "$ACCESS_KEY" ]] \
  || fail "Target access key differs"

[[ "$TARGET_SECRET_VALUE" == "$SECRET_KEY" ]] \
  || fail "Target secret key differs"

unset ACCESS_KEY
unset SECRET_KEY
unset TARGET_ACCESS
unset TARGET_SECRET_VALUE

echo "SOURCE_SECRET=${SOURCE_NAMESPACE}/${SOURCE_SECRET}"
echo "TARGET_SECRET=${TARGET_NAMESPACE}/${TARGET_SECRET}"
echo "SECRET_VALUES_DISPLAYED=NO"
echo "CREDENTIAL_MATCH=YES"
echo "TASK004_SYNTHEA_S3_SECRET_SYNC=PASS"
echo '#### TASK004 SYNTHEA S3 SECRET SYNC OUTPUT END ####'
SECRET_SYNC_SCRIPT

chmod 0755 "$SECRET_SYNC"

# ============================================================
# Canonical generate + publish runner
# ============================================================

cat > "$RUNNER" <<'RUNNER_SCRIPT'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

APP="${ROOT}/apps/task004/publish_synthea_landing.py"

TEMPLATE="${ROOT}/kubernetes/manifests/task004/synthea-generate-publish-job.yaml.tpl"

NAMESPACE="dw-synthea"
NODE="worker01"

SECRET_NAME="dw-synthea-s3-secret"

DEFAULT_IMAGE_REF="ghcr.io/johnzhang-dataforge/healthcare-data-platform-synthea@sha256:2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d"

IMAGE_REF="${SYNTHEA_IMAGE_REF:-${DEFAULT_IMAGE_REF}}"

RENDER_ONLY=0
JOB_CREATED=0
CONFIGMAP_CREATED=0
JOB_NAME=""
POD_NAME=""

fail() {
  echo "ERROR=$*" >&2

  if [[ "$JOB_CREATED" -eq 1 ]]; then

    echo "FAILED_JOB_RETAINED_FOR_DIAGNOSIS=YES" >&2

    kubectl get job \
      "$JOB_NAME" \
      -n "$NAMESPACE" \
      -o wide \
      >&2 2>/dev/null || true

    kubectl get pods \
      -n "$NAMESPACE" \
      -l "job-name=${JOB_NAME}" \
      -o wide \
      >&2 2>/dev/null || true

    if [[ -n "$POD_NAME" ]]; then
      kubectl describe pod \
        "$POD_NAME" \
        -n "$NAMESPACE" \
        >&2 2>/dev/null || true

      kubectl logs \
        "$POD_NAME" \
        -n "$NAMESPACE" \
        >&2 2>/dev/null || true
    fi
  fi

  exit 1
}

usage() {
  cat <<'USAGE'
TASK004 canonical Synthea generate + Landing publish runner.

Required environment:
  BATCH_ID
  POPULATION_SIZE       20 or 50
  SEED
  REFERENCE_DATE        YYYYMMDD
  STATE

Optional:
  CLINICIAN_SEED        defaults to SEED
  CITY                  defaults empty
  LANDING_INGEST_DATE   defaults current UTC YYYY-MM-DD
  SYNTHEA_IMAGE_REF     digest-pinned image

Prerequisite:
  dw-synthea/dw-synthea-s3-secret

Use scripts/task004/04b-sync-s3-secret-to-synthea.sh
to create/update that namespace-local credential Secret.

Options:
  --render-only
USAGE
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--render-only" ]]; then
  RENDER_ONLY=1
  shift
fi

[[ "$#" -eq 0 ]] \
  || fail "Unexpected positional arguments"

: "${BATCH_ID:?BATCH_ID is required}"
: "${POPULATION_SIZE:?POPULATION_SIZE is required}"
: "${SEED:?SEED is required}"
: "${REFERENCE_DATE:?REFERENCE_DATE is required}"
: "${STATE:?STATE is required}"

CLINICIAN_SEED="${CLINICIAN_SEED:-${SEED}}"
CITY="${CITY:-}"

LANDING_INGEST_DATE="${LANDING_INGEST_DATE:-$(date -u +%Y-%m-%d)}"

[[ -s "$APP" ]] \
  || fail "Publisher application missing"

[[ -s "$TEMPLATE" ]] \
  || fail "Job template missing"

[[ "$POPULATION_SIZE" == "20" || "$POPULATION_SIZE" == "50" ]] \
  || fail "POPULATION_SIZE must be 20 or 50"

[[ "$SEED" =~ ^-?[0-9]+$ ]] \
  || fail "SEED must be integer"

[[ "$CLINICIAN_SEED" =~ ^-?[0-9]+$ ]] \
  || fail "CLINICIAN_SEED must be integer"

[[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]] \
  || fail "Image must be digest-pinned"

python3 - \
  "$BATCH_ID" \
  "$REFERENCE_DATE" \
  "$LANDING_INGEST_DATE" \
  "$STATE" \
  <<'PY'
import datetime
import re
import sys

batch_id = sys.argv[1]
reference_date = sys.argv[2]
ingest_date = sys.argv[3]
state = sys.argv[4]

if not re.fullmatch(
    r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}",
    batch_id,
):
    raise SystemExit(
        "ERROR: invalid BATCH_ID"
    )

datetime.datetime.strptime(
    reference_date,
    "%Y%m%d",
)

datetime.datetime.strptime(
    ingest_date,
    "%Y-%m-%d",
)

if not state.strip():
    raise SystemExit(
        "ERROR: STATE must not be blank"
    )
PY

SOURCE_HASH="$(
  sha256sum "$APP" \
  | awk '{print $1}'
)"

CONFIGMAP_NAME="$(
  printf 'task004-syn-publisher-%s' \
    "${SOURCE_HASH:0:12}"
)"

JOB_NAME="$(
  python3 - "$BATCH_ID" <<'PY'
import hashlib
import re
import sys

value = sys.argv[1]

slug = re.sub(
    r"[^a-z0-9]+",
    "-",
    value.lower(),
).strip("-")

slug = (
    slug[:32].rstrip("-")
    or "batch"
)

digest = hashlib.sha256(
    value.encode("utf-8")
).hexdigest()[:10]

print(
    f"task004-syn-pub-{slug}-{digest}"
)
PY
)"

TMP_DIR="$(mktemp -d)"
RENDERED="${TMP_DIR}/job.yaml"

cleanup_tmp() {
  rm -rf "$TMP_DIR"
}

trap cleanup_tmp EXIT

python3 - \
  "$TEMPLATE" \
  "$RENDERED" \
  "$JOB_NAME" \
  "$CONFIGMAP_NAME" \
  "$IMAGE_REF" \
  "$BATCH_ID" \
  "$POPULATION_SIZE" \
  "$SEED" \
  "$CLINICIAN_SEED" \
  "$REFERENCE_DATE" \
  "$STATE" \
  "$CITY" \
  "$LANDING_INGEST_DATE" \
  <<'PY'
import json
import sys
from pathlib import Path

(
    template_path,
    output_path,
    job_name,
    configmap_name,
    image_ref,
    batch_id,
    population_size,
    seed,
    clinician_seed,
    reference_date,
    state,
    city,
    ingest_date,
) = sys.argv[1:]

text = Path(
    template_path
).read_text(
    encoding="utf-8"
)

mapping = {
    "__JOB_NAME__":
        job_name,
    "__CONFIGMAP_NAME__":
        configmap_name,
    "__IMAGE_REF_JSON__":
        json.dumps(image_ref),
    "__BATCH_ID_JSON__":
        json.dumps(batch_id),
    "__POPULATION_SIZE_JSON__":
        json.dumps(population_size),
    "__SEED_JSON__":
        json.dumps(seed),
    "__CLINICIAN_SEED_JSON__":
        json.dumps(clinician_seed),
    "__REFERENCE_DATE_JSON__":
        json.dumps(reference_date),
    "__STATE_JSON__":
        json.dumps(state),
    "__CITY_JSON__":
        json.dumps(city),
    "__INGEST_DATE_JSON__":
        json.dumps(ingest_date),
}

for key, value in mapping.items():

    count = text.count(
        key
    )

    if count != 1:
        raise SystemExit(
            f"ERROR: placeholder {key} "
            f"count={count}"
        )

    text = text.replace(
        key,
        value,
    )

Path(
    output_path
).write_text(
    text,
    encoding="utf-8",
)
PY

if [[ "$RENDER_ONLY" -eq 1 ]]; then
  cat "$RENDERED"
  exit 0
fi

kubectl get namespace \
  "$NAMESPACE" \
  >/dev/null \
  || fail "dw-synthea namespace missing"

kubectl get secret \
  "$SECRET_NAME" \
  -n "$NAMESPACE" \
  >/dev/null \
  || fail "Run 04b secret sync first"

NODE_READY="$(
  kubectl get node "$NODE" \
    -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status}{end}'
)"

[[ "$NODE_READY" == "True" ]] \
  || fail "worker01 is not Ready"

kubectl create configmap \
  "$CONFIGMAP_NAME" \
  -n "$NAMESPACE" \
  --from-file=publish_synthea_landing.py="$APP" \
  --dry-run=client \
  -o yaml \
| kubectl apply \
    -f - \
    >/dev/null

CONFIGMAP_CREATED=1

if kubectl get job \
    "$JOB_NAME" \
    -n "$NAMESPACE" \
    >/dev/null 2>&1
then
  kubectl delete job \
    "$JOB_NAME" \
    -n "$NAMESPACE" \
    --cascade=foreground \
    --wait=true
fi

kubectl create \
  -f "$RENDERED"

JOB_CREATED=1

TERMINAL=""

for _ in $(seq 1 300); do

  COMPLETE="$(
    kubectl get job "$JOB_NAME" \
      -n "$NAMESPACE" \
      -o jsonpath='{range .status.conditions[?(@.type=="Complete")]}{.status}{end}' \
      2>/dev/null || true
  )"

  FAILED="$(
    kubectl get job "$JOB_NAME" \
      -n "$NAMESPACE" \
      -o jsonpath='{range .status.conditions[?(@.type=="Failed")]}{.status}{end}' \
      2>/dev/null || true
  )"

  if [[ "$COMPLETE" == "True" ]]; then
    TERMINAL="COMPLETE"
    break
  fi

  if [[ "$FAILED" == "True" ]]; then
    TERMINAL="FAILED"
    break
  fi

  sleep 5
done

[[ "$TERMINAL" == "COMPLETE" ]] \
  || fail "Generate-publish Job failed or timed out"

POD_NAME="$(
  kubectl get pods \
    -n "$NAMESPACE" \
    -l "job-name=${JOB_NAME}" \
    -o jsonpath='{.items[0].metadata.name}'
)"

[[ -n "$POD_NAME" ]] \
  || fail "Unable to resolve Job pod"

ACTUAL_NODE="$(
  kubectl get pod "$POD_NAME" \
    -n "$NAMESPACE" \
    -o jsonpath='{.spec.nodeName}'
)"

EXIT_CODE="$(
  kubectl get pod "$POD_NAME" \
    -n "$NAMESPACE" \
    -o jsonpath='{.status.containerStatuses[0].state.terminated.exitCode}'
)"

[[ "$ACTUAL_NODE" == "$NODE" ]] \
  || fail "Job did not run on worker01"

[[ "$EXIT_CODE" == "0" ]] \
  || fail "Container exited non-zero"

if git check-ignore \
    -q \
    --no-index \
    "runtime/reports/task004/landing/probe"
then
  REPORT_DIR="${ROOT}/runtime/reports/task004/landing"
else
  REPORT_DIR="/data/spark/runtime/task004/landing"
fi

mkdir -p "$REPORT_DIR"

LOG_FILE="${REPORT_DIR}/${JOB_NAME}.log"
REPORT_FILE="${REPORT_DIR}/${JOB_NAME}.json"

kubectl logs \
  "$POD_NAME" \
  -n "$NAMESPACE" \
| tee "$LOG_FILE"

for marker in \
  "SYNTHEA_GENERATION=PASS" \
  "CSV_VALIDATED=18/18" \
  "LANDING_PUBLICATION=PASS" \
  "MANIFEST_STATUS=INTAKE_VERIFIED" \
  "S3_PAYLOAD_READBACK_SHA256=18/18" \
  "POSTGRESQL_WRITE=NO" \
  "TASK004_GENERATE_PUBLISH_RUNTIME=PASS"
do
  grep -F "$marker" \
    "$LOG_FILE" \
    >/dev/null \
    || fail "Missing runtime marker: ${marker}"
done

python3 - \
  "$LOG_FILE" \
  "$REPORT_FILE" \
  "$BATCH_ID" \
  <<'PY'
import json
import re
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
report_path = Path(sys.argv[2])
batch_id = sys.argv[3]

lines = log_path.read_text(
    encoding="utf-8"
).splitlines()


def one(key):
    prefix = key + "="

    values = [
        line[len(prefix):]
        for line in lines
        if line.startswith(prefix)
    ]

    if len(values) != 1:
        raise SystemExit(
            f"ERROR: expected exactly one "
            f"{key}; found {len(values)}"
        )

    return values[0]


status = one(
    "MANIFEST_STATUS"
)

publish_mode = one(
    "PUBLISH_MODE"
)

prefix_mode = one(
    "PREFIX_MODE"
)

uploaded = int(
    one(
        "UPLOADED_THIS_RUN"
    )
)

reused = int(
    one(
        "REUSED_THIS_RUN"
    )
)

fingerprint = one(
    "PAYLOAD_FINGERPRINT"
)

landing_uri = one(
    "LANDING_URI"
)

manifest_uri = one(
    "MANIFEST_URI"
)

manifest_sha = one(
    "MANIFEST_SHA256"
)

readback = one(
    "S3_PAYLOAD_READBACK_SHA256"
)

if status != "INTAKE_VERIFIED":
    raise SystemExit(
        "ERROR: Landing log status "
        "is not INTAKE_VERIFIED"
    )

if readback != "18/18":
    raise SystemExit(
        "ERROR: Landing readback "
        "is not 18/18"
    )

if not re.fullmatch(
    r"[0-9a-f]{64}",
    fingerprint,
):
    raise SystemExit(
        "ERROR: invalid payload fingerprint"
    )

if not re.fullmatch(
    r"[0-9a-f]{64}",
    manifest_sha,
):
    raise SystemExit(
        "ERROR: invalid manifest SHA256"
    )

if manifest_uri != (
    landing_uri
    + "manifest.json"
):
    raise SystemExit(
        "ERROR: manifest URI does not "
        "match landing URI"
    )

# The actual ingest date is authoritative from
# the resolved Landing URI.  This matters when
# a batch is replayed on a later UTC date.
landing_match = re.search(
    r"/ingest_date=([^/]+)/"
    + r"batch_id="
    + re.escape(batch_id)
    + r"/$",
    landing_uri,
)

if landing_match is None:
    raise SystemExit(
        "ERROR: unable to derive ingest_date "
        "from Landing URI"
    )

ingest_date = landing_match.group(1)

report = {
    "batch_id":
        batch_id,

    "ingest_date":
        ingest_date,

    "landing_uri":
        landing_uri,

    "manifest_uri":
        manifest_uri,

    "manifest_sha256":
        manifest_sha,

    "payload_fingerprint":
        fingerprint,

    "prefix_mode":
        prefix_mode,

    "publish_mode":
        publish_mode,

    "reused_this_run":
        reused,

    "uploaded_this_run":
        uploaded,

    "verified_file_count":
        18,

    "status":
        status,

    "report_source":
        "POD_LOG",
}

report_path.write_text(
    json.dumps(
        report,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)

print(
    "REPORT_SOURCE=POD_LOG"
)
PY

python3 - "$REPORT_FILE" "$BATCH_ID" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

if data["status"] != "INTAKE_VERIFIED":
    raise SystemExit(
        "ERROR: landing report not verified"
    )

if data["batch_id"] != sys.argv[2]:
    raise SystemExit(
        "ERROR: report batch mismatch"
    )

if data["verified_file_count"] != 18:
    raise SystemExit(
        "ERROR: report file count mismatch"
    )

print(
    "LANDING_REPORT_GATE=PASS"
)
PY

kubectl delete job \
  "$JOB_NAME" \
  -n "$NAMESPACE" \
  --cascade=foreground \
  --wait=true

JOB_CREATED=0

kubectl delete configmap \
  "$CONFIGMAP_NAME" \
  -n "$NAMESPACE" \
  --ignore-not-found=true \
  >/dev/null

CONFIGMAP_CREATED=0

echo "GENERATE_PUBLISH_RUNNER=PASS"
echo "KUBERNETES_RESIDUAL_JOB=NO"
echo "POSTGRESQL_WRITE=NO"
echo "RESULT=PASS"
RUNNER_SCRIPT

chmod 0755 "$RUNNER"

# ============================================================
# Tests
# ============================================================

cat > "$TEST" <<'PY_TEST'
from __future__ import annotations

import copy
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

APP = (
    ROOT
    / "apps/task004/publish_synthea_landing.py"
)

TEMPLATE = (
    ROOT
    / "kubernetes/manifests/task004/"
      "synthea-generate-publish-job.yaml.tpl"
)

SECRET_SYNC = (
    ROOT
    / "scripts/task004/"
      "04b-sync-s3-secret-to-synthea.sh"
)

RUNNER = (
    ROOT
    / "scripts/task004/"
      "04c-run-synthea-generate-publish.sh"
)


spec = importlib.util.spec_from_file_location(
    "task004_landing_publisher",
    APP,
)

module = importlib.util.module_from_spec(
    spec
)

assert spec.loader is not None

sys.modules[
    spec.name
] = module

spec.loader.exec_module(
    module
)


def sample_draft():
    files = []

    for index in range(18):

        filename = (
            "patients.csv"
            if index == 0
            else f"file{index:02d}.csv"
        )

        dataset = (
            "patients"
            if index == 0
            else f"dataset{index:02d}"
        )

        files.append(
            {
                "dataset":
                    dataset,
                "header":
                    ["A"],
                "path":
                    "payload/csv/"
                    + filename,
                "row_count":
                    20
                    if index == 0
                    else 1,
                "sha256":
                    f"{index + 1:064x}",
                "size_bytes":
                    index + 10,
            }
        )

    return {
        "batch_id":
            "batch-001",
        "contract": {
            "path":
                "contracts/synthea/v3.3.0/"
                "csv-contract.json",
            "sha256":
                "a" * 64,
        },
        "expected_file_count":
            18,
        "files":
            files,
        "manifest_version":
            "1.0",
        "payload_format":
            "csv",
        "source":
            "synthea",
        "source_parameters": {
            "city":
                None,
            "clinician_seed":
                1,
            "population_size":
                20,
            "reference_date":
                "20261010",
            "seed":
                1,
            "state":
                "Georgia",
        },
        "source_provenance": {
            "synthea_commit":
                "x",
            "synthea_version":
                "v3.3.0",
        },
        "source_version":
            "v3.3.0",
        "status":
            "LOCAL_VALIDATED_NOT_UPLOADED",
    }


class LandingPublisherTests(
    unittest.TestCase
):

    def test_resolve_new_prefix(self):
        prefix, date, mode = (
            module.resolve_batch_prefix(
                [],
                "source=synthea/"
                "source_version=v3.3.0/",
                "batch-001",
                "2026-10-10",
            )
        )

        self.assertEqual(
            date,
            "2026-10-10",
        )

        self.assertEqual(
            mode,
            "CREATE_NEW_PREFIX",
        )

        self.assertTrue(
            prefix.endswith(
                "ingest_date=2026-10-10/"
                "batch_id=batch-001/"
            )
        )

    def test_resolve_existing_prefix(self):
        root = (
            "source=synthea/"
            "source_version=v3.3.0/"
        )

        key = (
            root
            + "ingest_date=2026-10-08/"
            + "batch_id=batch-001/"
            + "manifest.json"
        )

        prefix, date, mode = (
            module.resolve_batch_prefix(
                [key],
                root,
                "batch-001",
                "2026-10-10",
            )
        )

        self.assertEqual(
            date,
            "2026-10-08",
        )

        self.assertEqual(
            mode,
            "REUSE_EXISTING_PREFIX",
        )

        self.assertIn(
            "batch_id=batch-001/",
            prefix,
        )

    def test_multiple_prefixes_rejected(self):
        root = (
            "source=synthea/"
            "source_version=v3.3.0/"
        )

        keys = [
            root
            + "ingest_date=2026-10-08/"
            + "batch_id=batch-001/"
            + "manifest.json",

            root
            + "ingest_date=2026-10-09/"
            + "batch_id=batch-001/"
            + "manifest.json",
        ]

        with self.assertRaises(
            module.PublishError
        ):
            module.resolve_batch_prefix(
                keys,
                root,
                "batch-001",
                "2026-10-10",
            )

    def test_unknown_remote_object_rejected(self):
        draft = sample_draft()

        prefix = (
            "source=synthea/"
            "source_version=v3.3.0/"
            "ingest_date=2026-10-10/"
            "batch_id=batch-001/"
        )

        with self.assertRaises(
            module.PublishError
        ):
            module.inspect_batch_keys(
                draft,
                prefix,
                [
                    prefix
                    + "unexpected.bin"
                ],
            )

    def test_final_manifest_preserves_provenance(self):
        draft = sample_draft()

        final = (
            module.build_final_manifest(
                draft,
                "2026-10-10",
                "s3://health-landing/x/",
                "2026-10-10T12:00:00Z",
                "f" * 64,
            )
        )

        self.assertEqual(
            final["source_provenance"],
            draft["source_provenance"],
        )

        self.assertEqual(
            final["contract"],
            draft["contract"],
        )

        self.assertEqual(
            final["status"],
            "INTAKE_VERIFIED",
        )

    def test_final_manifest_file_conflict_rejected(self):
        draft = sample_draft()

        final = (
            module.build_final_manifest(
                draft,
                "2026-10-10",
                "s3://health-landing/x/",
                "2026-10-10T12:00:00Z",
                "f" * 64,
            )
        )

        final = copy.deepcopy(
            final
        )

        final["files"][0][
            "sha256"
        ] = "0" * 64

        with self.assertRaises(
            module.PublishError
        ):
            module.validate_final_manifest(
                draft,
                final,
                "2026-10-10",
                "s3://health-landing/x/",
                "f" * 64,
            )

    def test_manifest_last_source_semantics(self):
        source = APP.read_text(
            encoding="utf-8"
        )

        readback = source.index(
            "# Mandatory independent readback "
            "of all 18 payload objects."
        )

        manifest_last = source.index(
            "# Manifest is deliberately "
            "the LAST object created."
        )

        self.assertLess(
            readback,
            manifest_last,
        )

    def test_no_boto3_or_database_dependency(self):
        source = APP.read_text(
            encoding="utf-8"
        ).lower()

        self.assertNotIn(
            "boto3",
            source,
        )

        self.assertNotIn(
            "psycopg",
            source,
        )

        self.assertNotIn(
            "jdbc:postgresql",
            source,
        )

    def test_template_targets_dw_synthea(self):
        source = TEMPLATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "namespace: dw-synthea",
            source,
        )

        self.assertIn(
            "kubernetes.io/hostname: worker01",
            source,
        )

    def test_template_uses_namespace_local_secret(self):
        source = TEMPLATE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "name: dw-synthea-s3-secret",
            source,
        )

    def test_same_container_generates_then_publishes(self):
        source = TEMPLATE.read_text(
            encoding="utf-8"
        )

        generate = source.index(
            "/usr/local/bin/"
            "healthcare-synthea-generator"
        )

        publish = source.index(
            "publish_synthea_landing.py"
        )

        self.assertLess(
            generate,
            publish,
        )

    def test_template_has_no_postgresql(self):
        source = TEMPLATE.read_text(
            encoding="utf-8"
        ).lower()

        self.assertNotIn(
            "postgres",
            source,
        )

    def test_secret_sync_is_cross_namespace_copy(self):
        source = SECRET_SYNC.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'SOURCE_NAMESPACE="dw-spark"',
            source,
        )

        self.assertIn(
            'TARGET_NAMESPACE="dw-synthea"',
            source,
        )

        self.assertIn(
            'TARGET_SECRET="dw-synthea-s3-secret"',
            source,
        )

        self.assertIn(
            "SECRET_VALUES_DISPLAYED=NO",
            source,
        )

    def test_runner_does_not_depend_on_task001_runtime(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "runtime/reports/task001",
            source,
        )

        self.assertNotIn(
            "task001-final-validation",
            source,
        )

    def test_runner_is_digest_pinned(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "@sha256:"
            "2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d",
            source,
        )

    def test_runner_supports_render_only(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "--render-only",
            source,
        )

    def test_runner_render_only_executes_with_default_ingest_date(self):
        env = os.environ.copy()

        env.update(
            {
                "BATCH_ID":
                    "task004-unit-render",

                "POPULATION_SIZE":
                    "20",

                "SEED":
                    "20261010",

                "CLINICIAN_SEED":
                    "20261010",

                "REFERENCE_DATE":
                    "20261010",

                "STATE":
                    "Georgia",

                "CITY":
                    "",
            }
        )

        env.pop(
            "LANDING_INGEST_DATE",
            None,
        )

        result = subprocess.run(
            [
                str(RUNNER),
                "--render-only",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=(
                "render-only runner failed:\n"
                + result.stderr
            ),
        )

        self.assertIn(
            "namespace: dw-synthea",
            result.stdout,
        )

        self.assertIn(
            'name: LANDING_INGEST_DATE',
            result.stdout,
        )

        self.assertNotIn(
            "bad substitution",
            result.stderr.lower(),
        )


    def test_publisher_logs_prefix_mode(self):
        source = APP.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"PREFIX_MODE="',
            source,
        )

        self.assertIn(
            'result["prefix_mode"]',
            source,
        )

    def test_runner_collects_evidence_from_pod_log(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "REPORT_SOURCE=POD_LOG",
            source,
        )

        self.assertIn(
            '"report_source":',
            source,
        )

        self.assertIn(
            '"POD_LOG"',
            source,
        )

        self.assertNotIn(
            "kubectl exec",
            source,
        )

    def test_runner_derives_ingest_date_from_landing_uri(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "landing_match = re.search(",
            source,
        )

        self.assertIn(
            "ingest_date = landing_match.group(1)",
            source,
        )

    def test_local_draft_allows_patient_rows_above_requested_population(self):
        draft = sample_draft()

        draft["source_parameters"][
            "population_size"
        ] = 20

        with tempfile.TemporaryDirectory() as temporary:

            source_dir = Path(
                temporary
            )

            patient_item = None

            for item in draft["files"]:

                filename = Path(
                    item["path"]
                ).name

                row_count = (
                    21
                    if item["dataset"] == "patients"
                    else 1
                )

                payload = (
                    "A\n"
                    + "".join(
                        f"{index}\n"
                        for index in range(
                            row_count
                        )
                    )
                ).encode("utf-8")

                local_path = (
                    source_dir
                    / filename
                )

                local_path.write_bytes(
                    payload
                )

                item["row_count"] = (
                    row_count
                )

                item["size_bytes"] = (
                    len(payload)
                )

                item["sha256"] = (
                    module.sha256_file(
                        local_path
                    )
                )

                if item["dataset"] == "patients":
                    patient_item = item

            fingerprint = (
                module.validate_local_draft(
                    draft,
                    source_dir,
                    "batch-001",
                )
            )

            self.assertEqual(
                len(fingerprint),
                64,
            )

            self.assertIsNotNone(
                patient_item
            )

            # A requested population of 20 may produce
            # more than 20 patient records.  Fewer than
            # the requested population remains invalid.
            patient_payload = (
                "A\n"
                + "".join(
                    f"{index}\n"
                    for index in range(19)
                )
            ).encode("utf-8")

            patient_path = (
                source_dir
                / Path(
                    patient_item["path"]
                ).name
            )

            patient_path.write_bytes(
                patient_payload
            )

            patient_item["row_count"] = 19
            patient_item["size_bytes"] = len(
                patient_payload
            )
            patient_item["sha256"] = (
                module.sha256_file(
                    patient_path
                )
            )

            with self.assertRaises(
                module.PublishError
            ):
                module.validate_local_draft(
                    draft,
                    source_dir,
                    "batch-001",
                )

if __name__ == "__main__":
    unittest.main()
PY_TEST

echo "TASK004_LANDING_PUBLISHER_SOURCE=INSTALLED"

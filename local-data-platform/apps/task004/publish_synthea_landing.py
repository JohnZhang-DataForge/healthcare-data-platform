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

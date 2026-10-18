#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

APP="${ROOT}/apps/task004/resolve_verified_landing_file.py"
TEST="${ROOT}/tests/task004/test_generic_landing_resolver.py"

mkdir -p \
  "$(dirname "$APP")" \
  "$(dirname "$TEST")"

cat > "$APP" <<'APP_EOF'
#!/usr/bin/env python3

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


EXPECTED_FILE_COUNT = 18

SHA256_RE = re.compile(
    r"^[0-9a-f]{64}$"
)

BATCH_PREFIX_RE = re.compile(
    r"^"
    r"source=([^/]+)/"
    r"source_version=([^/]+)/"
    r"ingest_date=([^/]+)/"
    r"batch_id=([^/]+)/"
    r"manifest\.json$"
)


class ResolverError(
    RuntimeError
):
    pass


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def require_sha256(
    value: Any,
    label: str,
) -> str:
    if (
        not isinstance(
            value,
            str,
        )
        or not SHA256_RE.fullmatch(
            value
        )
    ):
        raise ResolverError(
            f"invalid {label}"
        )

    return value


def parse_manifest_uri(
    manifest_uri: str,
) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(
        manifest_uri
    )

    if (
        parsed.scheme != "s3"
        or not parsed.netloc
        or not parsed.path
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ResolverError(
            "manifest_uri must be a plain "
            "s3:// URI"
        )

    key = parsed.path.lstrip(
        "/"
    )

    if (
        not key
        or not key.endswith(
            "/manifest.json"
        )
    ):
        raise ResolverError(
            "manifest_uri must end with "
            "/manifest.json"
        )

    if (
        "//" in key
        or "/../" in (
            "/" + key + "/"
        )
        or "/./" in (
            "/" + key + "/"
        )
    ):
        raise ResolverError(
            "manifest_uri contains unsafe path"
        )

    return (
        parsed.netloc,
        key,
    )


def landing_uri_from_manifest_uri(
    manifest_uri: str,
) -> str:
    suffix = "manifest.json"

    if not manifest_uri.endswith(
        suffix
    ):
        raise ResolverError(
            "manifest_uri does not end "
            "with manifest.json"
        )

    return manifest_uri[
        :-len(suffix)
    ]


def manifest_lineage_from_key(
    key: str,
) -> dict[str, str]:
    match = BATCH_PREFIX_RE.fullmatch(
        key
    )

    if not match:
        raise ResolverError(
            "manifest_uri does not match "
            "canonical Landing prefix"
        )

    return {
        "source":
            match.group(1),

        "source_version":
            match.group(2),

        "ingest_date":
            match.group(3),

        "batch_id":
            match.group(4),
    }


def normalize_file(
    item: dict[str, Any],
) -> dict[str, Any]:
    required = (
        "path",
        "dataset",
        "size_bytes",
        "sha256",
        "row_count",
        "header",
    )

    missing = [
        key
        for key in required
        if key not in item
    ]

    if missing:
        raise ResolverError(
            "manifest file entry missing: "
            + ", ".join(
                missing
            )
        )

    path = item[
        "path"
    ]

    dataset = item[
        "dataset"
    ]

    if (
        not isinstance(
            path,
            str,
        )
        or not path.startswith(
            "payload/csv/"
        )
        or path.endswith(
            "/"
        )
        or ".." in path.split(
            "/"
        )
    ):
        raise ResolverError(
            "invalid manifest payload path"
        )

    if (
        not isinstance(
            dataset,
            str,
        )
        or not dataset
    ):
        raise ResolverError(
            "invalid manifest dataset"
        )

    row_count = item[
        "row_count"
    ]

    size_bytes = item[
        "size_bytes"
    ]

    if (
        not isinstance(
            row_count,
            int,
        )
        or row_count <= 0
    ):
        raise ResolverError(
            "manifest row_count must be > 0"
        )

    if (
        not isinstance(
            size_bytes,
            int,
        )
        or size_bytes <= 0
    ):
        raise ResolverError(
            "manifest size_bytes must be > 0"
        )

    file_sha = require_sha256(
        item[
            "sha256"
        ],
        "manifest file sha256",
    )

    header = item[
        "header"
    ]

    if (
        not isinstance(
            header,
            list,
        )
        or not header
        or not all(
            isinstance(
                value,
                str,
            )
            and value
            for value in header
        )
    ):
        raise ResolverError(
            "invalid manifest header"
        )

    return {
        "path":
            path,

        "dataset":
            dataset,

        "size_bytes":
            size_bytes,

        "sha256":
            file_sha,

        "row_count":
            row_count,

        "header":
            header,
    }


def payload_fingerprint(
    files: list[
        dict[str, Any]
    ],
) -> str:
    digest = hashlib.sha256()

    values = []

    for item in files:
        filename = item[
            "path"
        ].rsplit(
            "/",
            1,
        )[-1]

        values.append(
            (
                filename,
                item[
                    "sha256"
                ],
            )
        )

    for filename, file_sha in sorted(
        values
    ):
        digest.update(
            (
                filename
                + "|"
                + file_sha
                + "\n"
            ).encode(
                "utf-8"
            )
        )

    return digest.hexdigest()


def validate_manifest(
    manifest: Any,
    expected_batch_id: str,
    manifest_uri: str,
) -> list[
    dict[str, Any]
]:
    if not isinstance(
        manifest,
        dict,
    ):
        raise ResolverError(
            "manifest must be a JSON object"
        )

    required = (
        "manifest_version",
        "status",
        "source",
        "source_version",
        "batch_id",
        "ingest_date",
        "landing_uri",
        "expected_file_count",
        "payload_fingerprint",
        "verification",
        "files",
    )

    missing = [
        key
        for key in required
        if key not in manifest
    ]

    if missing:
        raise ResolverError(
            "manifest missing field(s): "
            + ", ".join(
                missing
            )
        )

    if (
        manifest[
            "manifest_version"
        ]
        != "1.0"
    ):
        raise ResolverError(
            "unsupported manifest_version"
        )

    if (
        manifest[
            "status"
        ]
        != "INTAKE_VERIFIED"
    ):
        raise ResolverError(
            "manifest status is not "
            "INTAKE_VERIFIED"
        )

    if (
        not isinstance(
            expected_batch_id,
            str,
        )
        or not expected_batch_id
    ):
        raise ResolverError(
            "invalid expected batch_id"
        )

    if (
        manifest[
            "batch_id"
        ]
        != expected_batch_id
    ):
        raise ResolverError(
            "manifest batch_id mismatch"
        )

    bucket, key = parse_manifest_uri(
        manifest_uri
    )

    lineage = manifest_lineage_from_key(
        key
    )

    for field in (
        "source",
        "source_version",
        "ingest_date",
        "batch_id",
    ):
        if (
            manifest.get(
                field
            )
            != lineage[
                field
            ]
        ):
            raise ResolverError(
                "manifest lineage mismatch: "
                + field
            )

    if (
        lineage[
            "batch_id"
        ]
        != expected_batch_id
    ):
        raise ResolverError(
            "manifest_uri batch_id mismatch"
        )

    expected_landing_uri = (
        landing_uri_from_manifest_uri(
            manifest_uri
        )
    )

    if (
        manifest[
            "landing_uri"
        ]
        != expected_landing_uri
    ):
        raise ResolverError(
            "manifest landing_uri mismatch"
        )

    if (
        not expected_landing_uri.startswith(
            f"s3://{bucket}/"
        )
    ):
        raise ResolverError(
            "manifest bucket mismatch"
        )

    if (
        manifest[
            "expected_file_count"
        ]
        != EXPECTED_FILE_COUNT
    ):
        raise ResolverError(
            "manifest expected_file_count "
            "is not 18"
        )

    files = manifest[
        "files"
    ]

    if (
        not isinstance(
            files,
            list,
        )
        or len(
            files
        )
        != EXPECTED_FILE_COUNT
    ):
        raise ResolverError(
            "manifest file inventory "
            "is not exactly 18"
        )

    normalized = [
        normalize_file(
            item
        )
        for item in files
    ]

    paths = [
        item[
            "path"
        ]
        for item in normalized
    ]

    datasets = [
        item[
            "dataset"
        ]
        for item in normalized
    ]

    if (
        len(
            set(
                paths
            )
        )
        != EXPECTED_FILE_COUNT
    ):
        raise ResolverError(
            "duplicate manifest payload path"
        )

    if (
        len(
            set(
                datasets
            )
        )
        != EXPECTED_FILE_COUNT
    ):
        raise ResolverError(
            "duplicate manifest dataset"
        )

    verification = manifest[
        "verification"
    ]

    if not isinstance(
        verification,
        dict,
    ):
        raise ResolverError(
            "manifest verification missing"
        )

    if (
        verification.get(
            "verified_file_count"
        )
        != EXPECTED_FILE_COUNT
    ):
        raise ResolverError(
            "verified_file_count is not 18"
        )

    if (
        verification.get(
            "s3_readback"
        )
        != "PASS"
    ):
        raise ResolverError(
            "manifest S3 readback is not PASS"
        )

    expected_fingerprint = (
        require_sha256(
            manifest[
                "payload_fingerprint"
            ],
            "payload_fingerprint",
        )
    )

    actual_fingerprint = (
        payload_fingerprint(
            normalized
        )
    )

    if (
        actual_fingerprint
        != expected_fingerprint
    ):
        raise ResolverError(
            "manifest payload_fingerprint "
            "mismatch"
        )

    return normalized


def resolve_dataset(
    manifest: dict[str, Any],
    files: list[
        dict[str, Any]
    ],
    dataset: str,
    manifest_uri: str,
    manifest_sha256: str,
) -> dict[str, Any]:
    if (
        not isinstance(
            dataset,
            str,
        )
        or not dataset
    ):
        raise ResolverError(
            "dataset is required"
        )

    matches = [
        item
        for item in files
        if item[
            "dataset"
        ]
        == dataset
    ]

    if len(
        matches
    ) != 1:
        raise ResolverError(
            f"expected exactly one dataset "
            f"{dataset!r}; "
            f"found {len(matches)}"
        )

    item = matches[
        0
    ]

    landing_uri = manifest[
        "landing_uri"
    ]

    source_uri = (
        landing_uri.rstrip(
            "/"
        )
        + "/"
        + item[
            "path"
        ].lstrip(
            "/"
        )
    )

    return {
        "manifest_status":
            manifest[
                "status"
            ],

        "manifest_version":
            manifest[
                "manifest_version"
            ],

        "manifest_uri":
            manifest_uri,

        "manifest_sha256":
            manifest_sha256,

        "source":
            manifest[
                "source"
            ],

        "source_version":
            manifest[
                "source_version"
            ],

        "batch_id":
            manifest[
                "batch_id"
            ],

        "ingest_date":
            manifest[
                "ingest_date"
            ],

        "landing_uri":
            landing_uri,

        "dataset":
            item[
                "dataset"
            ],

        "path":
            item[
                "path"
            ],

        "source_uri":
            source_uri,

        "row_count":
            item[
                "row_count"
            ],

        "size_bytes":
            item[
                "size_bytes"
            ],

        "sha256":
            item[
                "sha256"
            ],

        "header":
            item[
                "header"
            ],
    }


def resolve_from_bytes(
    manifest_bytes: bytes,
    dataset: str,
    batch_id: str,
    manifest_uri: str,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    expected_sha = require_sha256(
        expected_manifest_sha256,
        "manifest_sha256",
    )

    actual_sha = sha256_bytes(
        manifest_bytes
    )

    if actual_sha != expected_sha:
        raise ResolverError(
            "remote manifest SHA256 mismatch"
        )

    try:
        manifest = json.loads(
            manifest_bytes
        )
    except Exception as exc:
        raise ResolverError(
            "remote manifest is invalid JSON"
        ) from exc

    files = validate_manifest(
        manifest,
        batch_id,
        manifest_uri,
    )

    return resolve_dataset(
        manifest,
        files,
        dataset,
        manifest_uri,
        actual_sha,
    )


class S3ReadOnlyClient:

    def __init__(
        self,
        endpoint: str,
        region: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        self.endpoint = endpoint.rstrip(
            "/"
        )

        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key

        parsed = urllib.parse.urlparse(
            self.endpoint
        )

        if (
            parsed.scheme
            not in (
                "http",
                "https",
            )
            or not parsed.netloc
        ):
            raise ResolverError(
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
            message.encode(
                "utf-8"
            ),
            hashlib.sha256,
        ).digest()


    def get_object(
        self,
        bucket: str,
        key: str,
    ) -> bytes:
        payload_hash = sha256_bytes(
            b""
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
            "/"
            + bucket
            + "/"
            + key
        )

        canonical_uri = (
            urllib.parse.quote(
                raw_path,
                safe="/-_.~",
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
            "GET\n"
            + canonical_uri
            + "\n\n"
            + canonical_headers
            + "\n"
            + signed_headers
            + "\n"
            + payload_hash
        )

        scope = (
            f"{date_stamp}/"
            f"{self.region}/"
            "s3/aws4_request"
        )

        string_to_sign = (
            "AWS4-HMAC-SHA256\n"
            + amz_date
            + "\n"
            + scope
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
            ).encode(
                "utf-8"
            ),
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
            "AWS4-HMAC-SHA256 "
            "Credential="
            + self.access_key
            + "/"
            + scope
            + ", SignedHeaders="
            + signed_headers
            + ", Signature="
            + signature
        )

        url = (
            self.endpoint
            + canonical_uri
        )

        request = urllib.request.Request(
            url,
            method="GET",
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

                if response.status != 200:
                    raise ResolverError(
                        "S3 GET manifest failed"
                    )

                return response.read()

        except urllib.error.HTTPError as exc:
            raise ResolverError(
                "S3 GET manifest failed "
                f"status={exc.code}"
            ) from exc

        except OSError as exc:
            raise ResolverError(
                "S3 GET manifest failed: "
                + str(exc)
            ) from exc


def shell_lines(
    result: dict[str, Any],
) -> list[str]:
    values = {
        "MANIFEST_STATUS":
            result[
                "manifest_status"
            ],

        "MANIFEST_VERSION":
            result[
                "manifest_version"
            ],

        "MANIFEST_URI":
            result[
                "manifest_uri"
            ],

        "MANIFEST_SHA256":
            result[
                "manifest_sha256"
            ],

        "SOURCE":
            result[
                "source"
            ],

        "SOURCE_VERSION":
            result[
                "source_version"
            ],

        "BATCH_ID":
            result[
                "batch_id"
            ],

        "INGEST_DATE":
            result[
                "ingest_date"
            ],

        "LANDING_URI":
            result[
                "landing_uri"
            ],

        "SOURCE_DATASET":
            result[
                "dataset"
            ],

        "SOURCE_FILE":
            result[
                "path"
            ],

        "SOURCE_URI":
            result[
                "source_uri"
            ],

        "EXPECTED_ROWS":
            result[
                "row_count"
            ],

        "SOURCE_FILE_SIZE_BYTES":
            result[
                "size_bytes"
            ],

        "SOURCE_FILE_SHA256":
            result[
                "sha256"
            ],
    }

    output = []

    for key, raw_value in (
        values.items()
    ):
        value = str(
            raw_value
        )

        if any(
            char in value
            for char in (
                "\n",
                "\r",
            )
        ):
            raise ResolverError(
                f"unsafe shell value for {key}"
            )

        output.append(
            f"{key}={value}"
        )

    return output


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Resolve one dataset from a "
            "verified remote Landing manifest."
        )
    )

    parser.add_argument(
        "dataset"
    )

    parser.add_argument(
        "--batch-id",
        required=True,
    )

    parser.add_argument(
        "--manifest-uri",
        required=True,
    )

    parser.add_argument(
        "--manifest-sha256",
        required=True,
    )

    parser.add_argument(
        "--endpoint",
        default=os.environ.get(
            "S3_ENDPOINT"
        ),
    )

    parser.add_argument(
        "--region",
        default=os.environ.get(
            "S3_REGION",
            "us-east-1",
        ),
    )

    parser.add_argument(
        "--format",
        choices=(
            "json",
            "shell",
        ),
        default="json",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if not args.endpoint:
        raise ResolverError(
            "S3 endpoint is required"
        )

    access_key = os.environ.get(
        "AWS_ACCESS_KEY_ID"
    )

    secret_key = os.environ.get(
        "AWS_SECRET_ACCESS_KEY"
    )

    if (
        not access_key
        or not secret_key
    ):
        raise ResolverError(
            "AWS credentials are required"
        )

    bucket, key = parse_manifest_uri(
        args.manifest_uri
    )

    client = S3ReadOnlyClient(
        endpoint=args.endpoint,
        region=args.region,
        access_key=access_key,
        secret_key=secret_key,
    )

    manifest_bytes = (
        client.get_object(
            bucket,
            key,
        )
    )

    result = resolve_from_bytes(
        manifest_bytes=manifest_bytes,
        dataset=args.dataset,
        batch_id=args.batch_id,
        manifest_uri=args.manifest_uri,
        expected_manifest_sha256=(
            args.manifest_sha256
        ),
    )

    if args.format == "json":
        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

    else:
        for line in shell_lines(
            result
        ):
            print(
                line
            )


if __name__ == "__main__":
    main()
APP_EOF

cat > "$TEST" <<'TEST_EOF'
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(
    "/data/spark/healthcare-data-platform"
)

APP = (
    ROOT
    / "apps/task004/"
    "resolve_verified_landing_file.py"
)

SPEC = importlib.util.spec_from_file_location(
    "task004_generic_resolver",
    APP,
)

module = importlib.util.module_from_spec(
    SPEC
)

assert SPEC.loader is not None

SPEC.loader.exec_module(
    module
)


DATASETS = [
    "allergies",
    "careplans",
    "claims",
    "claims_transactions",
    "conditions",
    "devices",
    "encounters",
    "imaging_studies",
    "immunizations",
    "medications",
    "observations",
    "organizations",
    "patients",
    "payer_transitions",
    "payers",
    "procedures",
    "providers",
    "supplies",
]


def sample_manifest():
    files = []

    for index, dataset in enumerate(
        DATASETS,
        start=1,
    ):
        filename = (
            dataset
            + ".csv"
        )

        file_sha = hashlib.sha256(
            filename.encode(
                "utf-8"
            )
        ).hexdigest()

        files.append(
            {
                "path":
                    "payload/csv/"
                    + filename,

                "dataset":
                    dataset,

                "size_bytes":
                    1000
                    + index,

                "sha256":
                    file_sha,

                "row_count":
                    index,

                "header":
                    [
                        "COL_A",
                        "COL_B",
                    ],
            }
        )

    fingerprint = (
        module.payload_fingerprint(
            [
                module.normalize_file(
                    item
                )
                for item in files
            ]
        )
    )

    return {
        "manifest_version":
            "1.0",

        "status":
            "INTAKE_VERIFIED",

        "source":
            "synthea",

        "source_version":
            "v3.3.0",

        "batch_id":
            "batch-001",

        "ingest_date":
            "2026-10-11",

        "landing_uri":
            (
                "s3://health-landing/"
                "source=synthea/"
                "source_version=v3.3.0/"
                "ingest_date=2026-10-11/"
                "batch_id=batch-001/"
            ),

        "expected_file_count":
            18,

        "payload_fingerprint":
            fingerprint,

        "verification": {
            "verified_file_count":
                18,

            "s3_readback":
                "PASS",
        },

        "files":
            files,
    }


def manifest_uri():
    return (
        "s3://health-landing/"
        "source=synthea/"
        "source_version=v3.3.0/"
        "ingest_date=2026-10-11/"
        "batch_id=batch-001/"
        "manifest.json"
    )


class GenericLandingResolverTests(
    unittest.TestCase
):

    def test_parse_manifest_uri(self):
        bucket, key = (
            module.parse_manifest_uri(
                manifest_uri()
            )
        )

        self.assertEqual(
            bucket,
            "health-landing",
        )

        self.assertTrue(
            key.endswith(
                "/manifest.json"
            )
        )


    def test_rejects_non_s3_manifest_uri(self):
        with self.assertRaises(
            module.ResolverError
        ):
            module.parse_manifest_uri(
                "https://example/manifest.json"
            )


    def test_valid_manifest_passes(self):
        manifest = sample_manifest()

        files = (
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )
        )

        self.assertEqual(
            len(files),
            18,
        )


    def test_rejects_non_verified_manifest(self):
        manifest = sample_manifest()

        manifest[
            "status"
        ] = "LOCAL_VALIDATED_NOT_UPLOADED"

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )


    def test_rejects_batch_mismatch(self):
        manifest = sample_manifest()

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "wrong-batch",
                manifest_uri(),
            )


    def test_rejects_landing_uri_mismatch(self):
        manifest = sample_manifest()

        manifest[
            "landing_uri"
        ] = (
            "s3://health-landing/wrong/"
        )

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )


    def test_rejects_wrong_file_count(self):
        manifest = sample_manifest()

        manifest[
            "files"
        ] = manifest[
            "files"
        ][:-1]

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )


    def test_rejects_duplicate_dataset(self):
        manifest = sample_manifest()

        manifest[
            "files"
        ][1][
            "dataset"
        ] = manifest[
            "files"
        ][0][
            "dataset"
        ]

        manifest[
            "payload_fingerprint"
        ] = module.payload_fingerprint(
            [
                module.normalize_file(
                    item
                )
                for item in manifest[
                    "files"
                ]
            ]
        )

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )


    def test_resolves_patients_dataset(self):
        manifest = sample_manifest()

        files = (
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )
        )

        result = (
            module.resolve_dataset(
                manifest,
                files,
                "patients",
                manifest_uri(),
                "a" * 64,
            )
        )

        self.assertEqual(
            result[
                "dataset"
            ],
            "patients",
        )

        self.assertTrue(
            result[
                "source_uri"
            ].endswith(
                "/payload/csv/patients.csv"
            )
        )


    def test_resolves_encounters_dataset(self):
        manifest = sample_manifest()

        files = (
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )
        )

        result = (
            module.resolve_dataset(
                manifest,
                files,
                "encounters",
                manifest_uri(),
                "b" * 64,
            )
        )

        self.assertEqual(
            result[
                "dataset"
            ],
            "encounters",
        )

        self.assertGreater(
            result[
                "row_count"
            ],
            0,
        )


    def test_rejects_missing_dataset(self):
        manifest = sample_manifest()

        files = (
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )
        )

        with self.assertRaises(
            module.ResolverError
        ):
            module.resolve_dataset(
                manifest,
                files,
                "not_real",
                manifest_uri(),
                "c" * 64,
            )


    def test_resolve_from_bytes_checks_manifest_sha(self):
        manifest = sample_manifest()

        payload = json.dumps(
            manifest,
            sort_keys=True,
        ).encode(
            "utf-8"
        )

        with self.assertRaises(
            module.ResolverError
        ):
            module.resolve_from_bytes(
                payload,
                "patients",
                "batch-001",
                manifest_uri(),
                "0" * 64,
            )


    def test_resolve_from_bytes_success(self):
        manifest = sample_manifest()

        payload = json.dumps(
            manifest,
            sort_keys=True,
        ).encode(
            "utf-8"
        )

        manifest_sha = hashlib.sha256(
            payload
        ).hexdigest()

        result = (
            module.resolve_from_bytes(
                payload,
                "patients",
                "batch-001",
                manifest_uri(),
                manifest_sha,
            )
        )

        self.assertEqual(
            result[
                "manifest_sha256"
            ],
            manifest_sha,
        )

        self.assertEqual(
            result[
                "batch_id"
            ],
            "batch-001",
        )


    def test_rejects_payload_fingerprint_mismatch(self):
        manifest = sample_manifest()

        manifest[
            "payload_fingerprint"
        ] = "f" * 64

        with self.assertRaises(
            module.ResolverError
        ):
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )


    def test_shell_output_has_runtime_contract(self):
        manifest = sample_manifest()

        files = (
            module.validate_manifest(
                manifest,
                "batch-001",
                manifest_uri(),
            )
        )

        result = (
            module.resolve_dataset(
                manifest,
                files,
                "encounters",
                manifest_uri(),
                "a" * 64,
            )
        )

        output = "\n".join(
            module.shell_lines(
                result
            )
        )

        for name in (
            "MANIFEST_STATUS=",
            "MANIFEST_URI=",
            "MANIFEST_SHA256=",
            "BATCH_ID=",
            "LANDING_URI=",
            "SOURCE_DATASET=",
            "SOURCE_FILE=",
            "SOURCE_URI=",
            "EXPECTED_ROWS=",
            "SOURCE_FILE_SIZE_BYTES=",
            "SOURCE_FILE_SHA256=",
        ):
            self.assertIn(
                name,
                output,
            )


    def test_no_task001_runtime_dependency(self):
        source = APP.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "runtime/reports/task001",
            source,
        )

        self.assertNotIn(
            "TASK-001 final report",
            source,
        )


    def test_resolver_is_remote_read_only(self):
        source = APP.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'method="GET"',
            source,
        )

        self.assertNotIn(
            'method="PUT"',
            source,
        )

        self.assertNotIn(
            'method="DELETE"',
            source,
        )

        self.assertNotIn(
            "psycopg",
            source.lower(),
        )

        self.assertNotIn(
            "postgres",
            source.lower(),
        )


if __name__ == "__main__":
    unittest.main()
TEST_EOF

chmod 0755 "$APP"

echo "GENERIC_RESOLVER_SOURCE_RECONSTRUCTED=YES"

import json


def read_json_document(spark, uri):
    rows = (
        spark.read
        .text(uri)
        .collect()
    )

    payload = "\n".join(
        row["value"]
        for row in rows
    )

    if not payload.strip():
        raise RuntimeError(
            f"JSON document is empty: {uri}"
        )

    return json.loads(payload)


def validate_intake_manifest(
    manifest,
    expected_batch_id=None,
):
    required = [
        "manifest_version",
        "status",
        "source",
        "source_version",
        "batch_id",
        "ingest_date",
        "landing_uri",
        "expected_file_count",
        "verification",
        "files",
    ]

    missing = [
        name
        for name in required
        if name not in manifest
    ]

    if missing:
        raise RuntimeError(
            "Landing manifest missing fields: "
            + ", ".join(missing)
        )

    if manifest["status"] != "INTAKE_VERIFIED":
        raise RuntimeError(
            "Landing manifest is not "
            "INTAKE_VERIFIED."
        )

    if (
        expected_batch_id is not None
        and manifest["batch_id"]
        != expected_batch_id
    ):
        raise RuntimeError(
            "Landing batch_id mismatch: "
            f"expected={expected_batch_id}, "
            f"actual={manifest['batch_id']}"
        )

    expected_count = int(
        manifest["expected_file_count"]
    )

    files = manifest["files"]

    if expected_count != 18:
        raise RuntimeError(
            "Expected TASK-001 manifest "
            f"file count 18, got {expected_count}."
        )

    if len(files) != expected_count:
        raise RuntimeError(
            "Landing file inventory incomplete: "
            f"expected={expected_count}, "
            f"actual={len(files)}"
        )

    verification = manifest[
        "verification"
    ]

    if int(
        verification.get(
            "verified_file_count",
            -1,
        )
    ) != expected_count:
        raise RuntimeError(
            "Landing verification count mismatch."
        )

    if (
        verification.get("s3_readback")
        != "PASS"
    ):
        raise RuntimeError(
            "Landing S3 readback was not PASS."
        )

    return manifest


def find_dataset_file(
    manifest,
    dataset,
    filename,
):
    matches = []

    for item in manifest["files"]:
        path = item.get("path", "")

        if (
            item.get("dataset") == dataset
            and path.endswith(
                "/" + filename
            )
        ):
            matches.append(item)

    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one "
            f"{dataset}/{filename} entry, "
            f"found {len(matches)}."
        )

    item = matches[0]

    required = [
        "path",
        "dataset",
        "size_bytes",
        "sha256",
        "row_count",
        "header",
    ]

    missing = [
        name
        for name in required
        if name not in item
    ]

    if missing:
        raise RuntimeError(
            f"{filename} manifest entry "
            "missing fields: "
            + ", ".join(missing)
        )

    return item


def s3_to_s3a(uri):
    if uri.startswith("s3a://"):
        return uri

    if uri.startswith("s3://"):
        return (
            "s3a://"
            + uri[len("s3://"):]
        )

    raise ValueError(
        f"Unsupported S3 URI: {uri}"
    )


def join_uri(base, relative):
    return (
        base.rstrip("/")
        + "/"
        + relative.lstrip("/")
    )

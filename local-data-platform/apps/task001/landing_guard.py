#!/usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path


def load_json(path):
    return json.loads(
        Path(path).read_text(
            encoding="utf-8"
        )
    )


def write_json(path, value):
    Path(path).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    Path(path).write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )


def read_keys(path):
    source = Path(path)

    if not source.exists():
        return []

    return [
        line.strip()
        for line in source.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
        and line.strip() != "None"
    ]


def resolve_prefix(args):

    keys = read_keys(
        args.keys
    )

    escaped_root = re.escape(
        args.root_prefix
    )

    escaped_batch = re.escape(
        args.batch_id
    )

    pattern = re.compile(
        rf"^"
        rf"{escaped_root}"
        rf"ingest_date=([^/]+)/"
        rf"batch_id={escaped_batch}/"
    )

    found = {}

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
            f"{args.root_prefix}"
            f"ingest_date={ingest_date}/"
            f"batch_id={args.batch_id}/"
        )

        found[prefix] = (
            ingest_date
        )


    if len(found) > 1:

        print(
            "ERROR: multiple V2 prefixes "
            "exist for the same batch_id:",
            file=sys.stderr
        )

        for prefix in sorted(found):
            print(
                f"  {prefix}",
                file=sys.stderr
            )

        return 2


    if found:

        prefix = next(
            iter(found)
        )

        ingest_date = (
            found[prefix]
        )

        mode = "REUSE_EXISTING"

    else:

        ingest_date = (
            args.default_ingest_date
        )

        prefix = (
            f"{args.root_prefix}"
            f"ingest_date={ingest_date}/"
            f"batch_id={args.batch_id}/"
        )

        mode = "CREATE_NEW"


    result = {
        "batch_id":
            args.batch_id,

        "ingest_date":
            ingest_date,

        "batch_prefix":
            prefix,

        "mode":
            mode
    }

    write_json(
        args.output,
        result
    )

    print(
        f"PREFIX_MODE={mode}"
    )

    print(
        f"INGEST_DATE={ingest_date}"
    )

    print(
        f"BATCH_PREFIX={prefix}"
    )

    return 0


def inspect_keys(args):

    draft = load_json(
        args.draft
    )

    keys = read_keys(
        args.keys
    )

    expected_payload = {
        args.batch_prefix
        + item["path"]
        for item in draft["files"]
    }

    manifest_key = (
        args.batch_prefix
        + "manifest.json"
    )

    allowed = (
        expected_payload
        | {manifest_key}
    )

    unknown = sorted(
        set(keys) - allowed
    )

    if unknown:

        print(
            "ERROR: unexpected object(s) "
            "exist inside batch prefix:",
            file=sys.stderr
        )

        for key in unknown:
            print(
                f"  {key}",
                file=sys.stderr
            )

        return 2


    payload_present = sorted(
        set(keys)
        & expected_payload
    )

    manifest_present = (
        manifest_key in keys
    )

    result = {
        "manifest_present":
            manifest_present,

        "payload_present_count":
            len(payload_present),

        "expected_payload_count":
            len(expected_payload),

        "payload_keys":
            payload_present
    }

    write_json(
        args.output,
        result
    )

    print(
        "MANIFEST_PRESENT="
        + (
            "YES"
            if manifest_present
            else "NO"
        )
    )

    print(
        "REMOTE_PAYLOAD_PRESENT="
        f"{len(payload_present)}/"
        f"{len(expected_payload)}"
    )

    return 0


def normalize_file(item):

    return {
        "path":
            item["path"],

        "dataset":
            item["dataset"],

        "size_bytes":
            item["size_bytes"],

        "sha256":
            item["sha256"],

        "row_count":
            item["row_count"],

        "header":
            item["header"]
    }


def compare_manifest(args):

    draft = load_json(
        args.draft
    )

    final = load_json(
        args.manifest
    )


    errors = []


    if final.get("status") != "INTAKE_VERIFIED":

        errors.append(
            "existing manifest status is not "
            "INTAKE_VERIFIED"
        )


    for key in [
        "manifest_version",
        "source",
        "source_version",
        "batch_id",
        "payload_format",
        "expected_file_count",
        "source_parameters"
    ]:

        if final.get(key) != draft.get(key):

            errors.append(
                f"manifest field mismatch: "
                f"{key}"
            )


    draft_files = sorted(
        (
            normalize_file(x)
            for x in draft["files"]
        ),
        key=lambda x: x["path"]
    )

    final_files = sorted(
        (
            normalize_file(x)
            for x in final.get(
                "files",
                []
            )
        ),
        key=lambda x: x["path"]
    )


    if draft_files != final_files:

        errors.append(
            "manifest file inventory/checksum "
            "does not match current local batch"
        )


    if errors:

        print(
            "ERROR: existing manifest conflicts "
            "with current batch:",
            file=sys.stderr
        )

        for error in errors:

            print(
                f"  {error}",
                file=sys.stderr
            )

        return 2


    print(
        "EXISTING_MANIFEST_MATCH=PASS"
    )

    return 0


def main():

    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="command",
        required=True
    )


    p = sub.add_parser(
        "resolve-prefix"
    )

    p.add_argument(
        "--keys",
        required=True
    )

    p.add_argument(
        "--root-prefix",
        required=True
    )

    p.add_argument(
        "--batch-id",
        required=True
    )

    p.add_argument(
        "--default-ingest-date",
        required=True
    )

    p.add_argument(
        "--output",
        required=True
    )

    p.set_defaults(
        func=resolve_prefix
    )


    p = sub.add_parser(
        "inspect-keys"
    )

    p.add_argument(
        "--keys",
        required=True
    )

    p.add_argument(
        "--draft",
        required=True
    )

    p.add_argument(
        "--batch-prefix",
        required=True
    )

    p.add_argument(
        "--output",
        required=True
    )

    p.set_defaults(
        func=inspect_keys
    )


    p = sub.add_parser(
        "compare-manifest"
    )

    p.add_argument(
        "--draft",
        required=True
    )

    p.add_argument(
        "--manifest",
        required=True
    )

    p.set_defaults(
        func=compare_manifest
    )


    args = parser.parse_args()

    return args.func(
        args
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )

import ast
from pathlib import Path


APP = Path(
    "/data/spark/healthcare-data-platform/"
    "apps/resolve_verified_intake_file.py"
)


def source():
    return APP.read_text(
        encoding="utf-8"
    )


def test_python_parses():
    ast.parse(source())


def test_requires_task001_pass():
    value = source()

    assert (
        'final_report.get("status") != "PASS"'
        in value
    )


def test_verifies_manifest_sha():
    value = source()

    assert "manifest_sha256" in value
    assert "sha256_file" in value


def test_requires_intake_verified():
    assert (
        '"INTAKE_VERIFIED"'
        in source()
    )


def test_requires_18_file_manifest():
    assert (
        "len(files) != 18"
        in source()
    )


def test_resolves_dataset_dynamically():
    value = source()

    assert '"dataset"' in value
    assert "args.dataset" in value


def test_returns_runtime_row_count():
    value = source()

    assert '"row_count"' in value
    assert "EXPECTED_ROWS" in value


def test_no_database_or_s3_write():
    value = source()

    assert "kubectl" not in value
    assert ".write" not in value
    assert "boto3" not in value

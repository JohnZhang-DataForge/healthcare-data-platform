import ast
from pathlib import Path


APP = Path(
    "/data/spark/healthcare-data-platform/"
    "spark/apps/visit/"
    "synthea_encounter_adapter.py"
)


EXPECTED_SOURCE = [
    "Id",
    "START",
    "STOP",
    "PATIENT",
    "ORGANIZATION",
    "PROVIDER",
    "PAYER",
    "ENCOUNTERCLASS",
    "CODE",
    "DESCRIPTION",
    "BASE_ENCOUNTER_COST",
    "TOTAL_CLAIM_COST",
    "PAYER_COVERAGE",
    "REASONCODE",
    "REASONDESCRIPTION",
]


def text():
    return APP.read_text(
        encoding="utf-8"
    )


def test_python_parses():
    ast.parse(text())


def test_exact_synthea_columns_present():
    value = text()

    for item in EXPECTED_SOURCE:
        assert f'"{item}"' in value


def test_requires_authoritative_lineage_args():
    value = text()

    for flag in [
        "--source-system",
        "--source-version",
        "--source-batch-id",
        "--source-ingest-date",
        "--source-file",
        "--source-file-sha256",
        "--source-file-size-bytes",
        "--processing-run-id",
    ]:
        assert flag in value


def test_expected_5799_not_hardcoded():
    assert "5799" not in text()


def test_immutable_processing_write():
    value = text()

    assert '.mode("errorifexists")' in value
    assert "PROCESSING_WRITE=PASS" in value


def test_no_database_write():
    value = text()

    assert ".format(\"jdbc\")" not in value
    assert "POSTGRESQL_WRITE=NO" in value


def test_no_raw_publish():
    value = text()

    assert "RAW_PUBLISH=NO" in value


def test_contract_and_dq_markers():
    value = text()

    assert (
        "CANONICAL_ENCOUNTER_CONTRACT=PASS"
        in value
    )

    assert (
        "CANONICAL_ENCOUNTER_DQ=PASS"
        in value
    )

    assert (
        "PROCESSING_READBACK=PASS"
        in value
    )

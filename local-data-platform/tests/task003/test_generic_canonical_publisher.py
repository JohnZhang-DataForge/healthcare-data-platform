import ast
from pathlib import Path


APP = Path(
    "/data/spark/healthcare-data-platform/"
    "spark/apps/publish_canonical_entity.py"
)


def text():
    return APP.read_text(
        encoding="utf-8"
    )


def test_python_parses():
    ast.parse(
        text()
    )


def test_uses_shared_manifest_framework():
    value = text()

    assert (
        "validate_intake_manifest"
        in value
    )

    assert (
        "find_dataset_file"
        in value
    )


def test_uses_shared_canonical_gate():
    value = text()

    for name in [
        "load_contract",
        "validate_contract",
        "validate_metadata",
        "validate_unique_key",
    ]:
        assert name in value


def test_entity_is_runtime_parameter():
    value = text()

    assert (
        '"--entity"'
        in value
    )

    assert (
        "args.entity"
        in value
    )


def test_dataset_is_runtime_parameter():
    value = text()

    assert (
        '"--dataset"'
        in value
    )

    assert (
        "args.dataset"
        in value
    )


def test_adapter_name_is_runtime_parameter():
    value = text()

    assert (
        '"--expected-adapter-name"'
        in value
    )

    assert (
        "args.expected_adapter_name"
        in value
    )


def test_no_patient_hardcoding():
    value = text()

    assert '"patients"' not in value
    assert '"patient"' not in value


def test_no_encounter_hardcoding():
    value = text()

    assert '"encounters"' not in value
    assert '"encounter"' not in value


def test_raw_write_is_immutable():
    value = text()

    assert (
        '.mode(\n                "errorifexists"'
        in value
    )

    assert (
        "RAW_WRITE=PASS"
        in value
    )


def test_manifest_is_not_published_by_spark():
    value = text()

    assert (
        "RAW_MANIFEST_PUBLISHED=NO"
        in value
    )


def test_no_database_write():
    value = text()

    assert ".format(\"jdbc\")" not in value
    assert "POSTGRESQL_WRITE=NO" in value


def test_readback_is_required():
    value = text()

    assert (
        "RAW_READBACK=PASS"
        in value
    )

    assert (
        "RAW_UNIQUE_KEYS="
        in value
    )

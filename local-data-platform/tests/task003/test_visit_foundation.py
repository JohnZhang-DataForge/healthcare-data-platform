import json
from pathlib import Path


ROOT = Path(
    "/data/spark/healthcare-data-platform"
)

CANONICAL = (
    ROOT
    / "spark/contracts/canonical/encounter-v1.json"
)

MAPPING = (
    ROOT
    / "spark/contracts/omop/visit-class-v1.json"
)


EXPECTED_FIELDS = [
    "source_encounter_id",
    "source_person_id",
    "start_datetime",
    "end_datetime",
    "encounter_class",
    "source_code",
    "source_description",
    "source_organization_id",
    "source_provider_id",
    "source_payer_id",
    "base_encounter_cost",
    "total_claim_cost",
    "payer_coverage",
    "reason_code",
    "reason_description",
    "source_system",
    "source_version",
    "source_batch_id",
    "source_ingest_date",
    "source_file",
    "source_file_sha256",
    "source_file_size_bytes",
    "adapter_name",
    "adapter_version",
    "canonical_version",
    "processing_run_id",
    "processed_at",
]


EXPECTED_CLASSES = {
    "ambulatory",
    "emergency",
    "home",
    "hospice",
    "inpatient",
    "outpatient",
    "snf",
    "urgentcare",
    "virtual",
    "wellness",
}


EXPECTED_MAPPING = {
    "ambulatory": 9202,
    "emergency": 9203,
    "home": 581476,
    "hospice": 581476,
    "inpatient": 9201,
    "outpatient": 9202,
    "snf": 9201,
    "urgentcare": 9202,
    "virtual": 722455,
    "wellness": 9202,
}


def load(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def test_canonical_contract_exact_fields():
    data = load(CANONICAL)

    actual = [
        item["name"]
        for item in data["fields"]
    ]

    assert actual == EXPECTED_FIELDS
    assert len(actual) == 27


def test_canonical_primary_key():
    data = load(CANONICAL)

    assert data["primary_key"] == [
        "source_system",
        "source_encounter_id",
    ]


def test_person_reference_required():
    data = load(CANONICAL)

    ref = data["references"][0]

    assert ref["field"] == "source_person_id"
    assert ref["target_entity"] == "patient"
    assert ref["required"] is True


def test_encounter_classes_frozen():
    data = load(CANONICAL)

    assert (
        set(
            data["allowed_encounter_classes"]
        )
        == EXPECTED_CLASSES
    )


def test_visit_mapping_complete():
    data = load(MAPPING)

    mapping = data[
        "class_to_visit_concept"
    ]

    assert set(mapping) == EXPECTED_CLASSES

    actual = {
        key: value["concept_id"]
        for key, value in mapping.items()
    }

    assert actual == EXPECTED_MAPPING


def test_visit_type_is_ehr_encounter():
    data = load(MAPPING)

    assert (
        data["visit_type_concept_id"]
        == 32827
    )

    assert (
        data["visit_type_concept_name"]
        == "EHR encounter record"
    )


def test_stable_id_strategy():
    data = load(MAPPING)

    model = data["visit_model"]

    assert (
        model["mode"]
        == "one_source_encounter_per_visit_occurrence"
    )

    assert (
        model["stable_id_map"]
        == "etl.visit_occurrence_id_map"
    )

    assert model["aggregation"] is False


def test_source_value_strategy():
    data = load(MAPPING)

    assert (
        data["visit_source_value"]
        == "encounter_class"
    )

    assert (
        data["visit_source_concept_id"]
        is None
    )

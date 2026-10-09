GENDER_CONCEPTS = {
    "M": 8507,
    "F": 8532,
}

RACE_CONCEPTS = {
    "asian": 8515,
    "black": 8516,
    "hawaiian": 8557,
    "white": 8527,
}

ETHNICITY_CONCEPTS = {
    "hispanic": 38003563,
    "nonhispanic": 38003564,
}

DEMOGRAPHIC_CONCEPT_IDS = sorted(
    set(GENDER_CONCEPTS.values())
    | set(RACE_CONCEPTS.values())
    | set(ETHNICITY_CONCEPTS.values())
)


def validate_omop_contract(
    dataframe,
    contract,
):
    from pyspark.sql.functions import col

    expected_columns = [
        field["name"]
        for field in contract["fields"]
    ]

    if dataframe.columns != expected_columns:
        raise RuntimeError(
            "OMOP Person column contract mismatch.\n"
            f"Expected: {expected_columns}\n"
            f"Actual  : {dataframe.columns}"
        )

    actual_types = {
        field.name:
            field.dataType.simpleString()
        for field
        in dataframe.schema.fields
    }

    for definition in contract["fields"]:
        name = definition["name"]

        expected_type = definition["type"]
        actual_type = actual_types[name]

        if actual_type != expected_type:
            raise RuntimeError(
                f"OMOP Person type mismatch "
                f"for {name}: "
                f"expected={expected_type}, "
                f"actual={actual_type}"
            )

        if not definition["nullable"]:
            null_count = (
                dataframe
                .filter(
                    col(name).isNull()
                )
                .count()
            )

            if null_count != 0:
                raise RuntimeError(
                    f"Required OMOP field "
                    f"{name} contains "
                    f"{null_count} NULL rows."
                )

    return {
        "schema":
            "PASS",

        "required_fields":
            "PASS",
    }


def validate_person_keys(
    dataframe,
    expected_rows,
):
    from pyspark.sql.functions import (
        countDistinct,
    )

    rows = dataframe.count()

    unique_person_ids = (
        dataframe
        .agg(
            countDistinct(
                "person_id"
            ).alias("cnt")
        )
        .first()["cnt"]
    )

    unique_source_ids = (
        dataframe
        .agg(
            countDistinct(
                "person_source_value"
            ).alias("cnt")
        )
        .first()["cnt"]
    )

    if rows != expected_rows:
        raise RuntimeError(
            "OMOP Person row mismatch: "
            f"expected={expected_rows}, "
            f"actual={rows}"
        )

    if unique_person_ids != expected_rows:
        raise RuntimeError(
            "OMOP person_id is not unique."
        )

    if unique_source_ids != expected_rows:
        raise RuntimeError(
            "OMOP person_source_value "
            "is not unique."
        )

    return {
        "rows":
            rows,

        "unique_person_ids":
            unique_person_ids,

        "unique_source_ids":
            unique_source_ids,
    }

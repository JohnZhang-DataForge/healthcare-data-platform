import json


def load_contract(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def validate_contract(
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
            "Canonical schema column mismatch.\n"
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
                f"Canonical type mismatch "
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
                    f"Required canonical field "
                    f"{name} contains "
                    f"{null_count} NULL rows."
                )

    return {
        "schema":
            "PASS",

        "required_fields":
            "PASS",
    }


def validate_unique_key(
    dataframe,
    columns,
):
    row_count = dataframe.count()

    unique_count = (
        dataframe
        .select(
            *columns
        )
        .distinct()
        .count()
    )

    if unique_count != row_count:
        raise RuntimeError(
            "Canonical primary key "
            "is not unique: "
            f"rows={row_count}, "
            f"unique={unique_count}"
        )

    return {
        "rows":
            row_count,

        "unique_keys":
            unique_count,
    }


def validate_metadata(
    dataframe,
    expected,
):
    columns = list(
        expected.keys()
    )

    rows = (
        dataframe
        .select(
            *columns
        )
        .distinct()
        .collect()
    )

    if len(rows) != 1:
        raise RuntimeError(
            "Canonical lineage metadata "
            "is inconsistent: "
            f"distinct_rows={len(rows)}"
        )

    row = rows[0]

    for name, expected_value in expected.items():
        actual_value = row[name]

        if (
            str(actual_value)
            != str(expected_value)
        ):
            raise RuntimeError(
                f"Canonical metadata mismatch "
                f"for {name}: "
                f"expected={expected_value}, "
                f"actual={actual_value}"
            )

    return {
        "metadata":
            "PASS",
    }

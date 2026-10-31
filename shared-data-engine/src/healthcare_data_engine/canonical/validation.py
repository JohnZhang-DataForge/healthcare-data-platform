"""Validate rows against injected immutable Local v1 Contract bytes; no schema clone."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Mapping

LOCAL_CONTRACT_SHA256 = {
    "patient": "e0be146222f13b2f24a84d883d70117fac9aab984c184558dab88726ac5a3dab",
    "encounter": "473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837",
}


def load_pinned_contract(raw_bytes: bytes, entity: str) -> dict[str, Any]:
    if entity not in LOCAL_CONTRACT_SHA256:
        raise ValueError("UNSUPPORTED_CANONICAL_ENTITY:" + entity)
    if hashlib.sha256(raw_bytes).hexdigest() != LOCAL_CONTRACT_SHA256[entity]:
        raise ValueError("CONTRACT_SHA256_MISMATCH:" + entity)
    contract = json.loads(raw_bytes.decode("utf-8"))
    if contract.get("entity") != entity or contract.get("canonical_version") != "v1":
        raise ValueError("CONTRACT_ENTITY_VERSION_MISMATCH:" + entity)
    return contract


def _matches(value: Any, kind: str) -> bool:
    if kind == "string":
        return isinstance(value, str) and bool(value.strip())
    if kind == "date":
        return isinstance(value, date) and not isinstance(value, datetime)
    if kind == "timestamp":
        return isinstance(value, datetime) and value.tzinfo is not None
    if kind == "bigint":
        return isinstance(value, int) and not isinstance(value, bool)
    if re.fullmatch(r"decimal\(\d+,\d+\)", kind):
        return isinstance(value, Decimal)
    raise ValueError("UNKNOWN_CONTRACT_FIELD_TYPE:" + kind)


def validate_row(row: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[str, ...]:
    fields = contract["fields"]
    names = {f["name"] for f in fields}
    errors = []
    for field in fields:
        name, kind = field["name"], field["type"]
        if name not in row:
            errors.append("MISSING_FIELD:" + name)
        elif row[name] is None:
            if not field["nullable"]:
                errors.append("REQUIRED_FIELD_NULL:" + name)
        elif not _matches(row[name], kind):
            errors.append("INVALID_FIELD_TYPE:" + name + ":" + kind)
    for unknown in sorted(row.keys() - names):
        errors.append("UNKNOWN_FIELD:" + unknown)
    return tuple(errors)


def canonical_schema(contract: Mapping[str, Any]):
    """PySpark StructType created only on caller request; no SparkSession side effects."""
    from pyspark.sql.types import (StructType, StructField, StringType,
                                   DateType, TimestampType, LongType, DecimalType)
    lookup = {"string": StringType, "date": DateType,
              "timestamp": TimestampType, "bigint": LongType}
    fields = []
    for field in contract["fields"]:
        kind = field["type"]
        decimal = re.fullmatch(r"decimal\((\d+),(\d+)\)", kind)
        if decimal:
            dtype = DecimalType(int(decimal.group(1)), int(decimal.group(2)))
        elif kind in lookup:
            dtype = lookup[kind]()
        else:
            raise ValueError("UNSUPPORTED_SPARK_FIELD_TYPE:" + kind)
        fields.append(StructField(field["name"], dtype, field["nullable"]))
    return StructType(fields)


def accepted_dataframe(spark, accepted: tuple[dict[str, Any], ...],
                       contract: Mapping[str, Any]):
    """Requires injected SparkSession; strict field order/schema, including empty batches."""
    schema = canonical_schema(contract)
    for row in accepted:
        errors = validate_row(row, contract)
        if errors:
            raise ValueError("CANONICAL_ROW_INVALID:" + ",".join(errors))
    return spark.createDataFrame(
        [tuple(row[field.name] for field in schema.fields) for row in accepted],
        schema=schema)

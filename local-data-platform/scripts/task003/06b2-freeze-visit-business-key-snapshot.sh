#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

NS=dw-spark

EXPECTED_HEAD=6d8ef90ac50b4ce96cbde16b7b3c0a68a7574d4a

RUN_ID=visit-proc-20261009t192437z-2081886

EXPECTED_KEY_SHA=aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e
EXPECTED_B1_SHA=58cd44b22eaf15674a7277c51c66418c305bd3743b403c7612d458453d87f9f0

B1_CONTRACT="$ROOT/runtime/reports/task003/step06/visit-id-mutation-contracts/$RUN_ID/contract.json"

PROCESSED_DATA_URI='s3a://health-processed/contract_version=v1/entity=visit_occurrence/source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=synthea-20261005-pop100-atlanta/raw_publish_run_id=encounter-raw-20261009T005128Z-1681690/run_id=visit-proc-20261009t192437z-2081886/data/'

SOURCE_APP=visit-id-recon-20261010t004249z-2195105

SNAPSHOT_DIR="$ROOT/runtime/reports/task003/step06/visit-id-key-snapshots/$RUN_ID"

SNAPSHOT="$SNAPSHOT_DIR/business-keys.tsv"
SNAPSHOT_META="$SNAPSHOT_DIR/snapshot.json"

STAMP="$(date -u +%Y%m%dt%H%M%Sz)"
SUFFIX="${STAMP}-$$"

APP="visit-key-freeze-${SUFFIX}"
CM="${APP}-app"

REPORT="$ROOT/runtime/reports/task003/step06/visit-id-key-snapshot-build.${SUFFIX}"

DRIVER="$REPORT/extract_visit_business_keys.py"
SOURCE_APP_JSON="$REPORT/source-sparkapplication.json"
APP_JSON="$REPORT/sparkapplication.json"
APP_FINAL_JSON="$REPORT/sparkapplication-final.json"
DRIVER_LOG="$REPORT/driver.log"

RAW_TSV="$REPORT/business-keys.raw.tsv"
CANONICAL_TSV="$REPORT/business-keys.canonical.tsv"

RESULT="$REPORT/result.json"
RUN_STATE="$REPORT/run-state.json"

echo '#### TASK003 STEP06B2 VISIT BUSINESS KEY SNAPSHOT OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B2_REPORT=$REPORT"
  echo "STEP06B2_SNAPSHOT=$SNAPSHOT"
  echo "STEP06B2_SNAPSHOT_META=$SNAPSHOT_META"
  echo "STEP06B2_SPARKAPPLICATION=$APP"
  echo "STEP06B2_CONFIGMAP=$CM"
  echo "STEP06B2_EXIT_CODE=$rc"

  echo '#### TASK003 STEP06B2 VISIT BUSINESS KEY SNAPSHOT OUTPUT END ####'

  exit "$rc"
}

trap finish EXIT

mkdir -p "$REPORT"
mkdir -p "$SNAPSHOT_DIR"

cd "$ROOT"

echo '=== 1. Verify STEP06A Git checkpoint ==='

HEAD="$(git rev-parse HEAD)"

REMOTE_MAIN="$(
  git ls-remote \
    origin \
    refs/heads/main \
  | awk '{print $1}'
)"

echo "CURRENT_HEAD=$HEAD"
echo "REMOTE_MAIN_HEAD=$REMOTE_MAIN"
echo "EXPECTED_HEAD=$EXPECTED_HEAD"

[[ "$HEAD" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: local HEAD drifted'
  exit 1
}

[[ "$REMOTE_MAIN" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: remote main drifted'
  exit 1
}

[[ -z "$(git status --porcelain)" ]] || {
  echo 'ERROR: working tree is not clean'
  git status --short
  exit 1
}

echo 'STEP06A_GIT_CHECKPOINT=PASS'
echo 'REMOTE_MAIN_MATCH=PASS'
echo 'WORKING_TREE_CLEAN=PASS'

echo '=== 2. Verify STEP06B1 mutation contract ==='

[[ -s "$B1_CONTRACT" && ! -L "$B1_CONTRACT" ]] || {
  echo 'ERROR: STEP06B1 mutation contract missing'
  exit 1
}

B1_SHA="$(
  sha256sum "$B1_CONTRACT" |
  awk '{print $1}'
)"

echo "MUTATION_CONTRACT_SHA256=$B1_SHA"
echo "EXPECTED_MUTATION_CONTRACT_SHA256=$EXPECTED_B1_SHA"

[[ "$B1_SHA" == "$EXPECTED_B1_SHA" ]] || {
  echo 'ERROR: STEP06B1 mutation contract SHA mismatch'
  exit 1
}

python3 - \
  "$B1_CONTRACT" \
  "$EXPECTED_HEAD" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_B1'
import json
import sys
from pathlib import Path

contract = json.loads(
    Path(sys.argv[1]).read_bytes()
)

expected_head = sys.argv[2]
expected_key_sha = sys.argv[3]

assert contract["task"] == "TASK-003"
assert contract["step"] == "STEP-06B1"

assert (
    contract["status"]
    == "VISIT_ID_MUTATION_CONTRACT_READY"
)

assert contract["git_checkpoint"] == expected_head

scope = contract["scope"]

assert scope["candidate_rows"] == 5799
assert scope["candidate_unique_business_keys"] == 5799
assert scope["candidate_business_key_sha256"] == expected_key_sha

transport = contract["candidate_key_transport"]

assert transport["required_before_mutation"] is True
assert transport["producer_step"] == "STEP-06B2"
assert transport["format"] == "UTF-8 TSV"

assert transport["columns"] == [
    "source_system",
    "source_encounter_id",
]

assert transport["ordering"] == [
    "source_system ASC",
    "source_encounter_id ASC",
]

assert transport["expected_rows"] == 5799
assert transport["expected_unique_rows"] == 5799

assert (
    transport["expected_business_key_sha256"]
    == expected_key_sha
)

assert (
    transport["database_ingest"]
    == "COPY temporary table FROM STDIN"
)

assert transport["persistent_staging_table"] is False

safety = contract["safety"]

assert safety["nextval_called"] is False
assert safety["setval_called"] is False
assert safety["visit_id_allocation_started"] is False
assert safety["visit_id_map_mutated"] is False
assert safety["sequence_advanced"] is False

print('STEP06B1_CONTRACT_GATE=PASS')
PY_B1

echo '=== 3. Check immutable snapshot destination ==='

if [[ -e "$SNAPSHOT" || -e "$SNAPSHOT_META" ]]; then
  echo 'EXISTING_SNAPSHOT_DETECTED=YES'
  echo 'Existing snapshot will only be accepted if byte-identical.'
else
  echo 'EXISTING_SNAPSHOT_DETECTED=NO'
fi

echo '=== 4. Load proven STEP06A3 Spark runtime ==='

kubectl -n "$NS" \
  get sparkapplication "$SOURCE_APP" \
  -o json \
  > "$SOURCE_APP_JSON"

python3 - \
  "$SOURCE_APP_JSON" \
  "$SOURCE_APP" \
  <<'PY_RUNTIME'
import json
import sys
from pathlib import Path

doc = json.loads(
    Path(sys.argv[1]).read_bytes()
)

expected_name = sys.argv[2]

assert doc["metadata"]["name"] == expected_name

state = (
    doc.get("status", {})
    .get("applicationState", {})
    .get("state")
)

assert state == "COMPLETED", state

blob = json.dumps(
    doc["spec"],
    sort_keys=True,
).lower()

assert "spark:3.5.7-python3" in blob
assert "s3a" in blob or "hadoop-aws" in blob

print('PROVEN_STEP06A3_SPARK_RUNTIME=PASS')
print('SOURCE_SPARKAPPLICATION_STATE=COMPLETED')
PY_RUNTIME

echo '=== 5. Build READ ONLY business-key extractor ==='

cat > "$DRIVER" <<'PY_DRIVER'
#!/usr/bin/env python3

import hashlib
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


EXPECTED_ROWS = 5799
EXPECTED_KEYS = 5799

EXPECTED_SOURCE_SYSTEM = "synthea"

EXPECTED_SHA = (
    "aa5be446a3fe0ce4688594db45db19a33"
    "ad9bb182cca61e6a19cdb69ff74f72e"
)

BEGIN_MARKER = (
    "TASK003_STEP06B2_BUSINESS_KEYS_BEGIN"
)

END_MARKER = (
    "TASK003_STEP06B2_BUSINESS_KEYS_END"
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    require(
        len(sys.argv) == 2,
        "Expected frozen Processed Candidate URI",
    )

    uri = sys.argv[1]

    spark = (
        SparkSession.builder
        .appName(
            "TASK003-STEP06B2-Visit-Business-Key-Snapshot"
        )
        .getOrCreate()
    )

    try:
        df = spark.read.parquet(
            uri
        )

        required = {
            "source_system",
            "source_encounter_id",
        }

        missing = (
            required
            - set(df.columns)
        )

        require(
            not missing,
            "Missing Candidate columns: "
            + repr(sorted(missing)),
        )

        candidate = (
            df.select(
                F.col(
                    "source_system"
                ).cast("string").alias(
                    "source_system"
                ),
                F.col(
                    "source_encounter_id"
                ).cast("string").alias(
                    "source_encounter_id"
                ),
            )
        )

        total_rows = candidate.count()

        require(
            total_rows == EXPECTED_ROWS,
            "Candidate row count mismatch",
        )

        invalid = (
            candidate
            .filter(
                F.col(
                    "source_system"
                ).isNull()
                | F.col(
                    "source_encounter_id"
                ).isNull()
                | (
                    F.length(
                        F.trim(
                            F.col(
                                "source_system"
                            )
                        )
                    )
                    == 0
                )
                | (
                    F.length(
                        F.trim(
                            F.col(
                                "source_encounter_id"
                            )
                        )
                    )
                    == 0
                )
                | F.col(
                    "source_system"
                ).contains("\t")
                | F.col(
                    "source_system"
                ).contains("\n")
                | F.col(
                    "source_system"
                ).contains("\r")
                | F.col(
                    "source_encounter_id"
                ).contains("\t")
                | F.col(
                    "source_encounter_id"
                ).contains("\n")
                | F.col(
                    "source_encounter_id"
                ).contains("\r")
            )
            .count()
        )

        require(
            invalid == 0,
            "Invalid business-key values",
        )

        systems = [
            row["source_system"]
            for row in (
                candidate
                .select(
                    "source_system"
                )
                .distinct()
                .collect()
            )
        ]

        require(
            systems == [
                EXPECTED_SOURCE_SYSTEM
            ],
            "Unexpected source systems: "
            + repr(systems),
        )

        unique = (
            candidate
            .distinct()
        )

        unique_rows = unique.count()

        require(
            unique_rows == EXPECTED_KEYS,
            "Unique business-key count mismatch",
        )

        duplicates = (
            candidate
            .groupBy(
                "source_system",
                "source_encounter_id",
            )
            .count()
            .filter(
                F.col("count") > 1
            )
            .count()
        )

        require(
            duplicates == 0,
            "Duplicate Candidate business keys",
        )

        rows = (
            unique
            .orderBy(
                F.col(
                    "source_system"
                ).asc(),
                F.col(
                    "source_encounter_id"
                ).asc(),
            )
            .collect()
        )

        lines = [
            (
                str(
                    row[
                        "source_system"
                    ]
                )
                + "\t"
                + str(
                    row[
                        "source_encounter_id"
                    ]
                )
            )
            for row in rows
        ]

        require(
            len(lines) == EXPECTED_KEYS,
            "Collected key count mismatch",
        )

        require(
            lines == sorted(lines),
            "Business-key ordering mismatch",
        )

        require(
            len(set(lines))
            == EXPECTED_KEYS,
            "Business-key uniqueness mismatch",
        )

        payload = (
            "\n".join(lines)
            + "\n"
        ).encode(
            "utf-8"
        )

        sha = hashlib.sha256(
            payload
        ).hexdigest()

        require(
            sha == EXPECTED_SHA,
            "Business-key fingerprint mismatch: "
            + sha,
        )

        print(
            "TASK003_STEP06B2_ROWS="
            + str(total_rows)
        )

        print(
            "TASK003_STEP06B2_UNIQUE_KEYS="
            + str(unique_rows)
        )

        print(
            "TASK003_STEP06B2_BUSINESS_KEY_SHA256="
            + sha
        )

        print(BEGIN_MARKER)

        for line in lines:
            print(line)

        print(END_MARKER)

        print(
            "TASK003_STEP06B2_RESULT=PASS"
        )

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
PY_DRIVER

chmod 0755 "$DRIVER"

python3 - \
  "$DRIVER" \
  <<'PY_STATIC'
import ast
import re
import sys
from pathlib import Path

source = Path(
    sys.argv[1]
).read_text()

ast.parse(source)

for pattern in (
    r'\bnextval\s*\(',
    r'\bsetval\s*\(',
    r'\bINSERT\s+INTO\b',
    r'\bUPDATE\s+',
    r'\bDELETE\s+FROM\b',
    r'\bTRUNCATE\b',
    r'\.write\.',
    r'\.save\s*\(',
    r'\.saveAsTable\s*\(',
    r'\.insertInto\s*\(',
):
    assert not re.search(
        pattern,
        source,
        re.IGNORECASE,
    ), pattern

for token in (
    "EXPECTED_ROWS = 5799",
    "EXPECTED_KEYS = 5799",
    "EXPECTED_SOURCE_SYSTEM = \"synthea\"",
    "TASK003_STEP06B2_BUSINESS_KEYS_BEGIN",
    "TASK003_STEP06B2_BUSINESS_KEYS_END",
    "TASK003_STEP06B2_RESULT=PASS",
):
    assert token in source, token

print('B2_EXTRACTOR_SYNTAX=PASS')
print('B2_EXTRACTOR_S3_READ_ONLY=PASS')
print('B2_DATABASE_ACCESS_PATH=ABSENT')
print('B2_S3_WRITE_PATH=ABSENT')
PY_STATIC

echo '=== 6. Create B2 runtime ConfigMap ==='

kubectl -n "$NS" \
  create configmap "$CM" \
  --from-file=extract_visit_business_keys.py="$DRIVER"

echo "B2_CONFIGMAP_CREATED=$CM"

echo '=== 7. Render B2 SparkApplication from proven runtime ==='

python3 - \
  "$SOURCE_APP_JSON" \
  "$APP_JSON" \
  "$APP" \
  "$CM" \
  "$PROCESSED_DATA_URI" \
  <<'PY_APP'
import copy
import json
import sys
from pathlib import Path


source = json.loads(
    Path(sys.argv[1]).read_bytes()
)

target = Path(sys.argv[2])

app_name = sys.argv[3]
configmap_name = sys.argv[4]
candidate_uri = sys.argv[5]


spec = copy.deepcopy(
    source["spec"]
)

spec[
    "mainApplicationFile"
] = (
    "local:///opt/spark/b2/"
    "extract_visit_business_keys.py"
)

spec[
    "arguments"
] = [
    candidate_uri,
]

spec[
    "restartPolicy"
] = {
    "type": "Never",
}


# A3 had its application code in a ConfigMap.
# Strip every ConfigMap-backed application volume
# and add only the B2 source.
old_volumes = spec.get(
    "volumes",
    [],
)

removed_configmaps = {
    volume.get("name")
    for volume in old_volumes
    if "configMap" in volume
}

spec["volumes"] = [
    volume
    for volume in old_volumes
    if volume.get("name")
    not in removed_configmaps
]

spec["volumes"].append(
    {
        "name":
            "b2-app",

        "configMap": {
            "name":
                configmap_name,
        },
    }
)


def clean_section(name):
    section = spec.setdefault(
        name,
        {},
    )

    mounts = section.get(
        "volumeMounts",
        [],
    )

    section["volumeMounts"] = [
        mount
        for mount in mounts
        if mount.get("name")
        not in removed_configmaps
        and mount.get("name")
        != "b2-app"
    ]

    section["volumeMounts"].append(
        {
            "name":
                "b2-app",

            "mountPath":
                "/opt/spark/b2",

            "readOnly":
                True,
        }
    )

    # A3 used the OMOP Secret through envFrom on both
    # driver and executor. STEP06B2 must retain only
    # non-database envFrom sources such as the S3 Secret.
    section["envFrom"] = [
        item
        for item in section.get(
            "envFrom",
            [],
        )
        if item.get(
            "secretRef",
            {},
        ).get(
            "name"
        )
        != "dw-spark-omop-secret"
    ]

    labels = section.setdefault(
        "labels",
        {},
    )

    labels["task"] = "task003"
    labels["step"] = "step06b2"

    return section


driver = clean_section(
    "driver"
)

executor = clean_section(
    "executor"
)


# STEP06B2 does not use PostgreSQL.
# Remove all A3 DB credential references.
driver["env"] = [
    item
    for item in driver.get(
        "env",
        [],
    )
    if not item.get(
        "name",
        "",
    ).startswith(
        "A3_DB_"
    )
]


driver.setdefault(
    "serviceAccount",
    "spark-job",
)


doc = {
    "apiVersion":
        source["apiVersion"],

    "kind":
        source["kind"],

    "metadata": {
        "name":
            app_name,

        "namespace":
            "dw-spark",

        "labels": {
            "task":
                "task003",

            "step":
                "step06b2",

            "purpose":
                "visit-business-key-freeze",
        },
    },

    "spec":
        spec,
}


blob = json.dumps(
    doc,
    sort_keys=True,
)

assert "A3_DB_" not in blob
assert "dw-spark-omop-secret" not in blob


target.write_text(
    json.dumps(
        doc,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)

print('B2_SPARKAPPLICATION_RENDER=PASS')
print('B2_DATABASE_SECRET_REFERENCE=ABSENT')
PY_APP

echo '=== 8. Validate rendered B2 SparkApplication ==='

python3 - \
  "$APP_JSON" \
  "$APP" \
  "$CM" \
  "$PROCESSED_DATA_URI" \
  <<'PY_CHECK'
import json
import sys
from pathlib import Path


doc = json.loads(
    Path(sys.argv[1]).read_bytes()
)

app = sys.argv[2]
cm = sys.argv[3]
uri = sys.argv[4]

assert doc["metadata"]["name"] == app

spec = doc["spec"]

assert (
    spec["mainApplicationFile"]
    == "local:///opt/spark/b2/extract_visit_business_keys.py"
)

assert spec["arguments"] == [
    uri
]

assert spec["restartPolicy"]["type"] == "Never"

volumes = {
    item["name"]: item
    for item in spec.get(
        "volumes",
        []
    )
}

assert (
    volumes[
        "b2-app"
    ][
        "configMap"
    ][
        "name"
    ]
    == cm
)

blob = json.dumps(
    doc,
    sort_keys=True,
)

assert "A3_DB_" not in blob
assert "dw-spark-omop-secret" not in blob

low = blob.lower()

assert "nextval(" not in low
assert "setval(" not in low

print('B2_SPARKAPPLICATION_STATIC_VALIDATION=PASS')
print('B2_DATABASE_ACCESS_CONFIGURATION=ABSENT')
print('B2_NEXTVAL_PATH=ABSENT')
print('B2_SETVAL_PATH=ABSENT')
PY_CHECK

echo '=== 9. Launch real Spark READ ONLY key extraction ==='

kubectl apply \
  -f "$APP_JSON"

echo "SPARKAPPLICATION_CREATED=$APP"

echo '=== 10. Observe SparkApplication ==='

FINAL_STATE=''

for _ in $(seq 1 180); do

  FINAL_STATE="$(
    kubectl -n "$NS" \
      get sparkapplication "$APP" \
      -o jsonpath='{.status.applicationState.state}' \
      2>/dev/null \
      || true
  )"

  case "$FINAL_STATE" in
    COMPLETED|FAILED|SUBMISSION_FAILED)
      break
      ;;
  esac

  sleep 5
done

echo "FINAL_STATE=$FINAL_STATE"

kubectl -n "$NS" \
  get sparkapplication "$APP" \
  -o json \
  > "$APP_FINAL_JSON"

DRIVER_POD="$(
  kubectl -n "$NS" \
    get sparkapplication "$APP" \
    -o jsonpath='{.status.driverInfo.podName}' \
    2>/dev/null \
    || true
)"

echo "DRIVER_POD=${DRIVER_POD:-UNKNOWN}"

if [[ -n "${DRIVER_POD:-}" ]]; then
  kubectl -n "$NS" \
    logs "$DRIVER_POD" \
    > "$DRIVER_LOG" \
    2>&1 \
    || true
fi

if [[ "$FINAL_STATE" != "COMPLETED" ]]; then

  tail -n 200 \
    "$DRIVER_LOG" \
    2>/dev/null \
    || true

  echo 'ERROR: STEP06B2 Spark extraction failed'
  echo 'FAILED_RUNTIME_RESOURCES_PRESERVED=YES'

  exit 1
fi

echo 'B2_SPARKAPPLICATION_COMPLETED=PASS'

echo '=== 11. Extract exact TSV bytes from driver log ==='

python3 - \
  "$DRIVER_LOG" \
  "$RAW_TSV" \
  <<'PY_EXTRACT'
import sys
from pathlib import Path


log_path = Path(sys.argv[1])
output = Path(sys.argv[2])

begin = (
    "TASK003_STEP06B2_BUSINESS_KEYS_BEGIN"
)

end = (
    "TASK003_STEP06B2_BUSINESS_KEYS_END"
)


lines = log_path.read_text(
    errors="replace"
).splitlines()


begin_indexes = [
    index
    for index, line in enumerate(lines)
    if line.strip() == begin
]

end_indexes = [
    index
    for index, line in enumerate(lines)
    if line.strip() == end
]


assert len(begin_indexes) == 1, begin_indexes
assert len(end_indexes) == 1, end_indexes

start = begin_indexes[0]
finish = end_indexes[0]

assert finish > start

payload_lines = [
    line.strip("\r")
    for line in lines[
        start + 1:
        finish
    ]
]

assert len(payload_lines) == 5799, (
    len(payload_lines)
)

payload = (
    "\n".join(
        payload_lines
    )
    + "\n"
)

output.write_text(
    payload,
    encoding="utf-8",
    newline="\n",
)

print('B2_DRIVER_LOG_TSV_EXTRACTION=PASS')
print('EXTRACTED_BUSINESS_KEYS=5799')
PY_EXTRACT

echo '=== 12. Canonicalize and validate business-key snapshot ==='

python3 - \
  "$RAW_TSV" \
  "$CANONICAL_TSV" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_CANON'
import hashlib
import sys
from pathlib import Path


source = Path(sys.argv[1])
target = Path(sys.argv[2])
expected_sha = sys.argv[3]


raw = source.read_bytes()

assert b"\r" not in raw

text = raw.decode(
    "utf-8"
)

assert text.endswith(
    "\n"
)

lines = text.splitlines()

assert len(lines) == 5799


parsed = []

for index, line in enumerate(
    lines,
    start=1,
):

    fields = line.split(
        "\t"
    )

    assert len(fields) == 2, (
        index,
        fields,
    )

    source_system = fields[0]
    encounter_id = fields[1]

    assert source_system == "synthea"
    assert encounter_id

    assert "\t" not in encounter_id
    assert "\r" not in encounter_id
    assert "\n" not in encounter_id

    parsed.append(
        (
            source_system,
            encounter_id,
        )
    )


assert len(set(parsed)) == 5799

sorted_rows = sorted(
    parsed
)

assert parsed == sorted_rows


payload = "".join(
    source_system
    + "\t"
    + encounter_id
    + "\n"
    for (
        source_system,
        encounter_id
    )
    in sorted_rows
).encode(
    "utf-8"
)


sha = hashlib.sha256(
    payload
).hexdigest()


assert sha == expected_sha, (
    sha,
    expected_sha,
)


target.write_bytes(
    payload
)


print('B2_TSV_SCHEMA=PASS')
print('B2_TSV_ROWS=5799')
print('B2_TSV_UNIQUE_KEYS=5799')
print('B2_TSV_SORT_ORDER=PASS')
print('B2_TSV_UTF8=PASS')
print('B2_TSV_HEADER=NO')
print('B2_BUSINESS_KEY_SHA256=' + sha)
PY_CANON

echo '=== 13. Verify Spark-reported fingerprint ==='

SPARK_ROWS="$(
  grep '^TASK003_STEP06B2_ROWS=' \
    "$DRIVER_LOG" \
  | tail -n 1 \
  | cut -d= -f2-
)"

SPARK_KEYS="$(
  grep '^TASK003_STEP06B2_UNIQUE_KEYS=' \
    "$DRIVER_LOG" \
  | tail -n 1 \
  | cut -d= -f2-
)"

SPARK_SHA="$(
  grep '^TASK003_STEP06B2_BUSINESS_KEY_SHA256=' \
    "$DRIVER_LOG" \
  | tail -n 1 \
  | cut -d= -f2-
)"

SPARK_RESULT="$(
  grep '^TASK003_STEP06B2_RESULT=' \
    "$DRIVER_LOG" \
  | tail -n 1 \
  | cut -d= -f2-
)"

echo "SPARK_REPORTED_ROWS=$SPARK_ROWS"
echo "SPARK_REPORTED_UNIQUE_KEYS=$SPARK_KEYS"
echo "SPARK_REPORTED_BUSINESS_KEY_SHA256=$SPARK_SHA"
echo "SPARK_REPORTED_RESULT=$SPARK_RESULT"

[[ "$SPARK_ROWS" == "5799" ]] || {
  echo 'ERROR: Spark row count mismatch'
  exit 1
}

[[ "$SPARK_KEYS" == "5799" ]] || {
  echo 'ERROR: Spark unique-key count mismatch'
  exit 1
}

[[ "$SPARK_SHA" == "$EXPECTED_KEY_SHA" ]] || {
  echo 'ERROR: Spark fingerprint mismatch'
  exit 1
}

[[ "$SPARK_RESULT" == "PASS" ]] || {
  echo 'ERROR: Spark extractor did not report PASS'
  exit 1
}

echo 'SPARK_REPORTED_SNAPSHOT_STATE=PASS'

echo '=== 14. Freeze immutable TSV snapshot ==='

if [[ -e "$SNAPSHOT" ]]; then

  if cmp -s \
    "$CANONICAL_TSV" \
    "$SNAPSHOT"
  then
    echo 'BUSINESS_KEY_SNAPSHOT_ALREADY_IDENTICAL=YES'
  else
    echo 'ERROR: existing immutable business-key snapshot differs'
    exit 1
  fi

else

  install \
    -m 0444 \
    "$CANONICAL_TSV" \
    "$SNAPSHOT"

  echo 'BUSINESS_KEY_SNAPSHOT_INSTALLED=YES'
fi

FINAL_SHA="$(
  sha256sum "$SNAPSHOT" |
  awk '{print $1}'
)"

FINAL_ROWS="$(
  wc -l < "$SNAPSHOT" |
  tr -d ' '
)"

echo "BUSINESS_KEY_SNAPSHOT_SHA256=$FINAL_SHA"
echo "BUSINESS_KEY_SNAPSHOT_ROWS=$FINAL_ROWS"

[[ "$FINAL_SHA" == "$EXPECTED_KEY_SHA" ]] || {
  echo 'ERROR: frozen snapshot SHA mismatch'
  exit 1
}

[[ "$FINAL_ROWS" == "5799" ]] || {
  echo 'ERROR: frozen snapshot row count mismatch'
  exit 1
}

echo 'IMMUTABLE_TSV_SNAPSHOT=PASS'

echo '=== 15. Build deterministic snapshot metadata ==='

TMP_META="$REPORT/snapshot.json"

python3 - \
  "$TMP_META" \
  "$EXPECTED_HEAD" \
  "$RUN_ID" \
  "$EXPECTED_B1_SHA" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_META'
import json
import sys
from pathlib import Path


output = Path(sys.argv[1])

checkpoint = sys.argv[2]
run_id = sys.argv[3]
b1_sha = sys.argv[4]
key_sha = sys.argv[5]


doc = {
    "task":
        "TASK-003",

    "step":
        "STEP-06B2",

    "status":
        "VISIT_BUSINESS_KEY_SNAPSHOT_FROZEN",

    "snapshot_version":
        "v1",

    "git_checkpoint":
        checkpoint,

    "run_id":
        run_id,

    "source":
        "frozen Processed visit_occurrence Candidate",

    "format": {
        "encoding":
            "UTF-8",

        "delimiter":
            "TAB",

        "line_ending":
            "LF",

        "header":
            False,

        "columns": [
            "source_system",
            "source_encounter_id"
        ],

        "ordering": [
            "source_system ASC",
            "source_encounter_id ASC"
        ]
    },

    "rows":
        5799,

    "unique_business_keys":
        5799,

    "source_system":
        "synthea",

    "business_key_sha256":
        key_sha,

    "snapshot_file_sha256":
        key_sha,

    "lineage": {
        "step06b1_mutation_contract_sha256":
            b1_sha,

        "step06a_candidate_business_key_sha256":
            key_sha,
    },

    "intended_database_transport": {
        "method":
            "COPY temporary table FROM STDIN",

        "persistent_stage":
            False
    },

    "safety": {
        "s3_access":
            "READ_ONLY",

        "database_access":
            "NONE",

        "nextval_called":
            False,

        "setval_called":
            False,

        "visit_id_allocation_started":
            False,

        "visit_id_map_mutated":
            False,

        "sequence_advanced":
            False,

        "cdm_visit_occurrence_write":
            False
    }
}


output.write_text(
    json.dumps(
        doc,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)

print('B2_SNAPSHOT_METADATA_BUILD=PASS')
PY_META

python3 - \
  "$TMP_META" \
  "$SNAPSHOT" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_META_VERIFY'
import hashlib
import json
import sys
from pathlib import Path


meta = json.loads(
    Path(sys.argv[1]).read_bytes()
)

snapshot = Path(sys.argv[2])

expected_sha = sys.argv[3]


actual_sha = hashlib.sha256(
    snapshot.read_bytes()
).hexdigest()


assert actual_sha == expected_sha

assert meta["task"] == "TASK-003"
assert meta["step"] == "STEP-06B2"

assert (
    meta["status"]
    == "VISIT_BUSINESS_KEY_SNAPSHOT_FROZEN"
)

assert meta["rows"] == 5799
assert meta["unique_business_keys"] == 5799

assert meta["business_key_sha256"] == expected_sha
assert meta["snapshot_file_sha256"] == expected_sha

assert meta["format"]["header"] is False
assert meta["format"]["delimiter"] == "TAB"
assert meta["format"]["line_ending"] == "LF"

assert (
    meta["intended_database_transport"]["method"]
    == "COPY temporary table FROM STDIN"
)

safety = meta["safety"]

assert safety["s3_access"] == "READ_ONLY"
assert safety["database_access"] == "NONE"
assert safety["nextval_called"] is False
assert safety["setval_called"] is False
assert safety["visit_id_allocation_started"] is False
assert safety["visit_id_map_mutated"] is False
assert safety["sequence_advanced"] is False
assert safety["cdm_visit_occurrence_write"] is False

print('B2_SNAPSHOT_METADATA_VERIFY=PASS')
PY_META_VERIFY

if [[ -e "$SNAPSHOT_META" ]]; then

  if cmp -s \
    "$TMP_META" \
    "$SNAPSHOT_META"
  then
    echo 'SNAPSHOT_METADATA_ALREADY_IDENTICAL=YES'
  else
    echo 'ERROR: existing immutable snapshot metadata differs'
    exit 1
  fi

else

  install \
    -m 0444 \
    "$TMP_META" \
    "$SNAPSHOT_META"

  echo 'SNAPSHOT_METADATA_INSTALLED=YES'
fi

echo '=== 16. Independent snapshot byte verification ==='

python3 - \
  "$SNAPSHOT" \
  "$SNAPSHOT_META" \
  "$EXPECTED_KEY_SHA" \
  <<'PY_FINAL'
import hashlib
import json
import sys
from pathlib import Path


snapshot = Path(sys.argv[1])
meta_path = Path(sys.argv[2])
expected_sha = sys.argv[3]


payload = snapshot.read_bytes()

sha = hashlib.sha256(
    payload
).hexdigest()

assert sha == expected_sha

assert payload.endswith(
    b"\n"
)

assert b"\r" not in payload


lines = payload.decode(
    "utf-8"
).splitlines()

assert len(lines) == 5799

assert lines == sorted(lines)

assert len(set(lines)) == 5799


for line in lines:

    fields = line.split(
        "\t"
    )

    assert len(fields) == 2

    assert fields[0] == "synthea"
    assert fields[1]


meta = json.loads(
    meta_path.read_bytes()
)

assert meta["snapshot_file_sha256"] == sha
assert meta["business_key_sha256"] == sha


print('INDEPENDENT_BUSINESS_KEY_SNAPSHOT_VERIFY=PASS')
print('BUSINESS_KEY_SNAPSHOT_ROWS=5799')
print('BUSINESS_KEY_SNAPSHOT_UNIQUE_KEYS=5799')
print('BUSINESS_KEY_SNAPSHOT_SHA256=' + sha)
PY_FINAL

echo '=== 17. Record unique B2 build evidence ==='

python3 - \
  "$RUN_STATE" \
  "$RESULT" \
  "$SNAPSHOT" \
  "$SNAPSHOT_META" \
  "$B1_CONTRACT" \
  "$APP" \
  "$CM" \
  "$SOURCE_APP" \
  <<'PY_STATE'
import hashlib
import json
import sys
from pathlib import Path


state_path = Path(sys.argv[1])
result_path = Path(sys.argv[2])

snapshot = Path(sys.argv[3])
snapshot_meta = Path(sys.argv[4])
b1_contract = Path(sys.argv[5])

app = sys.argv[6]
cm = sys.argv[7]
source_app = sys.argv[8]


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


result = {
    "task":
        "TASK-003",

    "step":
        "STEP-06B2",

    "status":
        "VISIT_BUSINESS_KEY_SNAPSHOT_BUILD_PASS",

    "rows":
        5799,

    "unique_business_keys":
        5799,

    "business_key_sha256":
        sha(snapshot),

    "snapshot_file_sha256":
        sha(snapshot),

    "snapshot_metadata_sha256":
        sha(snapshot_meta),

    "step06b1_mutation_contract_sha256":
        sha(b1_contract),
}


state = {
    **result,

    "source_sparkapplication":
        source_app,

    "sparkapplication":
        app,

    "runtime_configmap":
        cm,

    "s3_access":
        "READ_ONLY",

    "database_access":
        "NONE",

    "nextval_called":
        False,

    "setval_called":
        False,

    "visit_id_allocation_started":
        False,

    "visit_id_map_mutated":
        False,

    "sequence_advanced":
        False,

    "cdm_visit_occurrence_write":
        False,
}


result_path.write_text(
    json.dumps(
        result,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)

state_path.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)


print('STEP06B2_BUILD_EVIDENCE=PASS')

print(
    'STEP06B2_SNAPSHOT_METADATA_SHA256='
    + result[
        "snapshot_metadata_sha256"
    ]
)
PY_STATE

echo '=== 18. Final STEP06B2 verdict ==='

echo 'STEP06B2_VISIT_BUSINESS_KEY_SNAPSHOT=PASS'

echo 'SNAPSHOT_FORMAT=UTF-8_TSV'
echo 'SNAPSHOT_HEADER=NO'
echo 'SNAPSHOT_ORDER=source_system_ASC,source_encounter_id_ASC'

echo 'SNAPSHOT_ROWS=5799'
echo 'SNAPSHOT_UNIQUE_BUSINESS_KEYS=5799'

echo "BUSINESS_KEY_SNAPSHOT_SHA256=$FINAL_SHA"
echo "EXPECTED_BUSINESS_KEY_SHA256=$EXPECTED_KEY_SHA"

echo 'BUSINESS_KEY_FINGERPRINT_MATCH=YES'

echo "MUTATION_CONTRACT_SHA256=$EXPECTED_B1_SHA"

echo 'SNAPSHOT_IMMUTABLE=YES'
echo 'SNAPSHOT_READY_FOR_COPY_STDIN=YES'

echo 'S3_ACCESS=READ_ONLY'
echo 'DATABASE_ACCESS=NONE'

echo 'ADVISORY_LOCK_ACQUIRED=NO'
echo 'NEXTVAL_CALLED=NO'
echo 'SETVAL_CALLED=NO'

echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'GIT_COMMIT=NO'

echo 'NEXT_REQUIRED_STEP=STEP06B3_PRE_MUTATION_CANONICALIZATION'

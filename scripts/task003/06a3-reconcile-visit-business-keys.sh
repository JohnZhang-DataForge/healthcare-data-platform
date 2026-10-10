#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute this script with bash; do not source it'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

NS=dw-spark
DB_NS=dw-postgre
DB_POD=dw-postgre-database-0
DB=omop
DB_USER=omop_admin

EXPECTED_HEAD=4e1a7a8d3870141ec0f97ad515e8a0d6f13802d4

RUN_ID=visit-proc-20261009t192437z-2081886

PLAN="$ROOT/runtime/reports/task003/step06/visit-id-allocation-plans/$RUN_ID/plan.json"
EXPECTED_PLAN_SHA=28cf06fecb744c8da477221abde37e7afd72ba7d974ef2c93f847a3d79b63c93

PROCESSED_DATA_URI='s3a://health-processed/contract_version=v1/entity=visit_occurrence/source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=synthea-20261005-pop100-atlanta/raw_publish_run_id=encounter-raw-20261009T005128Z-1681690/run_id=visit-proc-20261009t192437z-2081886/data/'

EXPECTED_ROWS=5799
EXPECTED_KEYS=5799
EXPECTED_PERSONS=113

DB_SECRET=dw-spark-omop-secret

STAMP="$(date -u +%Y%m%dt%H%M%Sz)"
SUFFIX="${STAMP}-$$"

APP="visit-id-recon-${SUFFIX}"
CM="${APP}-app"

REPORT="$ROOT/runtime/reports/task003/step06/visit-id-reconciliation.${SUFFIX}"

DRIVER="$REPORT/reconcile_visit_id_keys.py"
SOURCE_APP_JSON="$REPORT/source-sparkapplication.json"
APP_JSON="$REPORT/sparkapplication.json"
APP_FINAL_JSON="$REPORT/sparkapplication-final.json"
DRIVER_LOG="$REPORT/driver.log"
RESULT_JSON="$REPORT/reconciliation-result.json"
DB_POSTCHECK="$REPORT/post-reconciliation-db-state.txt"
SECRET_MAP="$REPORT/db-secret-map.json"
RUN_STATE="$REPORT/run-state.json"

echo '#### TASK003 STEP06A3 VISIT BUSINESS KEY RECONCILIATION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06A3_REPORT=$REPORT"
  echo "STEP06A3_SPARKAPPLICATION=$APP"
  echo "STEP06A3_CONFIGMAP=$CM"
  echo "STEP06A3_EXIT_CODE=$rc"

  echo '#### TASK003 STEP06A3 VISIT BUSINESS KEY RECONCILIATION OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$REPORT"

cd "$ROOT"

echo '=== 1. Verify STEP05 final Git checkpoint ==='

HEAD="$(git rev-parse HEAD)"

echo "CURRENT_HEAD=$HEAD"
echo "EXPECTED_HEAD=$EXPECTED_HEAD"

[[ "$HEAD" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: Git HEAD drifted'
  exit 1
}

echo 'STEP05_FINAL_GIT_CHECKPOINT=PASS'

echo '=== 2. Verify authoritative STEP06A2 plan ==='

[[ -s "$PLAN" && ! -L "$PLAN" ]] || {
  echo 'ERROR: STEP06A2 plan missing or unsafe'
  exit 1
}

PLAN_SHA="$(
  sha256sum "$PLAN" |
  awk '{print $1}'
)"

echo "ALLOCATION_PLAN_SHA256=$PLAN_SHA"
echo "EXPECTED_PLAN_SHA256=$EXPECTED_PLAN_SHA"

[[ "$PLAN_SHA" == "$EXPECTED_PLAN_SHA" ]] || {
  echo 'ERROR: STEP06A2 plan SHA mismatch'
  exit 1
}

python3 - \
  "$PLAN" \
  "$EXPECTED_HEAD" \
  <<'PY_PLAN'
import json
import sys
from pathlib import Path

plan = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert plan['task'] == 'TASK-003'
assert plan['step'] == 'STEP-06A2'

assert (
    plan['status']
    == 'VISIT_ID_ALLOCATION_PLAN_READY'
)

assert plan['git_checkpoint'] == sys.argv[2]

candidate = plan['source_candidate']

assert candidate['rows'] == 5799
assert candidate['unique_business_keys'] == 5799
assert candidate['referenced_persons'] == 113
assert candidate['frozen'] is True

db = plan['database_snapshot']

assert db['visit_map_rows'] == 0
assert db['cdm_visit_rows'] == 0
assert db['person_map_rows'] == 113

seq = plan['sequence']

assert seq['last_value_direct'] == 1
assert seq['is_called'] is False

assert (
    seq['pg_get_serial_sequence_binding']
    == 'etl.visit_occurrence_id_map_visit_occurrence_id_seq'
)

assert (
    seq['sequence_column_binding_present']
    is True
)

assert seq['column_default'] is None
assert seq['automatic_default_nextval'] is False
assert seq['explicit_allocation_required'] is True

safety = plan['safety']

assert safety['transaction_read_only'] is True
assert safety['nextval_called'] is False
assert safety['sequence_advanced'] is False
assert safety['visit_id_map_mutated'] is False
assert safety['cdm_visit_occurrence_write'] is False
assert safety['s3_mutation'] is False

print('STEP06A2_PLAN_GATE=PASS')
PY_PLAN

echo '=== 3. Verify current PostgreSQL state before Spark reconciliation ==='

kubectl -n "$DB_NS" \
  exec -i "$DB_POD" -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB" \
    -A \
    -t \
    -F '|' \
    -P pager=off \
  > "$REPORT/pre-reconciliation-db-state.txt" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

SELECT
    (SELECT count(*)
       FROM etl.visit_occurrence_id_map),
    (SELECT count(*)
       FROM cdm.visit_occurrence),
    (SELECT count(*)
       FROM etl.person_id_map);

SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

SELECT
    current_setting('transaction_read_only');

ROLLBACK;
SQL

cat "$REPORT/pre-reconciliation-db-state.txt"

python3 - \
  "$REPORT/pre-reconciliation-db-state.txt" \
  <<'PY_PRE'
import sys
from pathlib import Path

rows = [
    line.strip()
    for line in Path(sys.argv[1]).read_text().splitlines()
    if line.strip()
    and line.strip() not in {
        'BEGIN',
        'SET',
        'ROLLBACK',
    }
]

assert rows == [
    '0|0|113',
    '1|f',
    'on',
], rows

print('PRE_RECONCILIATION_DB_STATE=PASS')
print('VISIT_MAP_ROWS_BEFORE_A3=0')
print('CDM_VISIT_ROWS_BEFORE_A3=0')
print('SEQUENCE_LAST_VALUE_BEFORE_A3=1')
print('SEQUENCE_IS_CALLED_BEFORE_A3=FALSE')
PY_PRE

echo '=== 4. Resolve PostgreSQL Secret key mapping without exposing values ==='

kubectl -n "$NS" \
  get secret "$DB_SECRET" \
  -o json \
  > "$REPORT/db-secret.json"

python3 - \
  "$REPORT/db-secret.json" \
  "$SECRET_MAP" \
  <<'PY_SECRET'
import json
import re
import sys
from pathlib import Path

secret = json.loads(
    Path(sys.argv[1]).read_bytes()
)

keys = sorted(
    secret.get('data', {}).keys()
)

assert keys, 'database Secret has no keys'

def norm(value):
    return re.sub(
        r'[^a-z0-9]',
        '',
        value.lower(),
    )

by_norm = {
    norm(key): key
    for key in keys
}

def choose(*candidates):
    for candidate in candidates:
        found = by_norm.get(
            norm(candidate)
        )
        if found:
            return found
    return None

mapping = {
    'jdbc_url': choose(
        'jdbc-url',
        'jdbc_url',
        'jdbcurl',
        'omop-jdbc-url',
        'database-jdbc-url',
    ),

    'username': choose(
        'username',
        'user',
        'db-user',
        'db_user',
        'postgres-user',
        'postgres_user',
        'PGUSER',
    ),

    'password': choose(
        'password',
        'pass',
        'db-password',
        'db_password',
        'postgres-password',
        'postgres_password',
        'PGPASSWORD',
    ),

    'host': choose(
        'host',
        'db-host',
        'db_host',
        'postgres-host',
        'postgres_host',
        'PGHOST',
    ),

    'port': choose(
        'port',
        'db-port',
        'db_port',
        'postgres-port',
        'postgres_port',
        'PGPORT',
    ),

    'database': choose(
        'database',
        'dbname',
        'db-name',
        'db_name',
        'postgres-db',
        'postgres_db',
        'PGDATABASE',
    ),
}

assert mapping['username'], (
    'unable to identify DB username Secret key: '
    + repr(keys)
)

assert mapping['password'], (
    'unable to identify DB password Secret key: '
    + repr(keys)
)

assert (
    mapping['jdbc_url']
    or mapping['host']
), (
    'unable to identify JDBC URL or DB host Secret key: '
    + repr(keys)
)

Path(sys.argv[2]).write_text(
    json.dumps(
        mapping,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print(
    'DB_SECRET_AVAILABLE_KEYS='
    + ','.join(keys)
)

for name in (
    'jdbc_url',
    'username',
    'password',
    'host',
    'port',
    'database',
):
    value = mapping[name]

    print(
        'DB_SECRET_MAPPING_'
        + name.upper()
        + '='
        + (
            value
            if value
            else 'NONE'
        )
    )

print('DB_SECRET_KEY_MAPPING=PASS')
print('DB_SECRET_VALUES_EXPOSED=NO')
PY_SECRET

rm -f "$REPORT/db-secret.json"

echo '=== 5. Select a proven TASK003 SparkApplication runtime template ==='

if kubectl -n "$NS" \
    get sparkapplication \
    visit-cand-check-20261009t192437z-2081886 \
    -o json \
    > "$SOURCE_APP_JSON" \
    2>/dev/null
then
  SOURCE_APP=visit-cand-check-20261009t192437z-2081886

else
  kubectl -n "$NS" \
    get sparkapplication \
    -o json \
    > "$REPORT/all-sparkapplications.json"

  SOURCE_APP="$(
    python3 - \
      "$REPORT/all-sparkapplications.json" \
      <<'PY_SELECT'
import json
import sys
from pathlib import Path

doc = json.loads(
    Path(sys.argv[1]).read_bytes()
)

items = doc.get(
    'items',
    []
)

prefixes = (
    'visit-cand-check-',
    'visit-proc-write-',
    'visit-raw-check-',
)

for prefix in prefixes:
    matches = sorted(
        (
            item
            for item in items
            if item.get(
                'metadata',
                {},
            ).get(
                'name',
                '',
            ).startswith(prefix)
        ),
        key=lambda item: item.get(
            'metadata',
            {},
        ).get(
            'creationTimestamp',
            '',
        ),
        reverse=True,
    )

    if matches:
        print(
            matches[0][
                'metadata'
            ][
                'name'
            ]
        )
        raise SystemExit(0)

raise SystemExit(
    'ERROR: no proven TASK003 SparkApplication runtime found'
)
PY_SELECT
  )"

  kubectl -n "$NS" \
    get sparkapplication "$SOURCE_APP" \
    -o json \
    > "$SOURCE_APP_JSON"
fi

echo "SOURCE_SPARKAPPLICATION=$SOURCE_APP"

python3 - \
  "$SOURCE_APP_JSON" \
  <<'PY_RUNTIME'
import json
import sys
from pathlib import Path

app = json.loads(
    Path(sys.argv[1]).read_bytes()
)

spec = app['spec']

blob = json.dumps(
    spec,
    sort_keys=True,
).lower()

assert (
    'spark:3.5.7-python3'
    in blob
), 'unexpected Spark image'

assert (
    's3a'
    in blob
    or 'hadoop-aws'
    in blob
), 'proven runtime does not contain S3A/Hadoop AWS configuration'

assert (
    'postgres'
    in blob
), 'proven runtime does not contain PostgreSQL/JDBC support'

print('PROVEN_SPARK_RUNTIME=PASS')
print(
    'SOURCE_SPARK_IMAGE='
    + str(spec.get('image'))
)
PY_RUNTIME

echo '=== 6. Build standalone READ ONLY reconciliation driver ==='

cat > "$DRIVER" <<'PY_DRIVER'
#!/usr/bin/env python3

import hashlib
import json
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


EXPECTED_ROWS = 5799
EXPECTED_KEYS = 5799
EXPECTED_PERSONS = 113

EXPECTED_SOURCE_SYSTEM = "synthea"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def normalize_jdbc_url(value):
    value = value.strip()

    if value.startswith(
        "jdbc:postgresql://"
    ):
        return value

    if value.startswith(
        "postgresql://"
    ):
        return (
            "jdbc:"
            + value
        )

    raise RuntimeError(
        "Unsupported JDBC URL format"
    )


def resolve_jdbc_url():
    direct = os.environ.get(
        "A3_DB_JDBC_URL",
        "",
    ).strip()

    if direct:
        return normalize_jdbc_url(
            direct
        )

    host = os.environ.get(
        "A3_DB_HOST",
        "",
    ).strip()

    port = os.environ.get(
        "A3_DB_PORT",
        "5432",
    ).strip() or "5432"

    database = os.environ.get(
        "A3_DB_NAME",
        "omop",
    ).strip() or "omop"

    require(
        bool(host),
        "Missing JDBC URL and DB host",
    )

    return (
        "jdbc:postgresql://"
        + host
        + ":"
        + port
        + "/"
        + database
    )


def business_key_fingerprint(rows):
    canonical = [
        (
            str(row["source_system"])
            + "\t"
            + str(
                row[
                    "source_encounter_id"
                ]
            )
        )
        for row in rows
    ]

    canonical.sort()

    payload = (
        "\n".join(
            canonical
        )
        + "\n"
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        payload
    ).hexdigest()


def mapping_fingerprint(rows):
    canonical = [
        (
            str(row["source_system"])
            + "\t"
            + str(
                row[
                    "source_encounter_id"
                ]
            )
            + "\t"
            + str(
                row[
                    "visit_occurrence_id"
                ]
            )
        )
        for row in rows
    ]

    canonical.sort()

    payload = (
        "\n".join(
            canonical
        )
        + (
            "\n"
            if canonical
            else ""
        )
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        payload
    ).hexdigest()


def main():
    require(
        len(sys.argv) == 2,
        "Expected frozen Candidate data URI",
    )

    candidate_uri = sys.argv[1]

    jdbc_url = resolve_jdbc_url()

    jdbc_user = os.environ.get(
        "A3_DB_USER",
        "",
    )

    jdbc_password = os.environ.get(
        "A3_DB_PASSWORD",
        "",
    )

    require(
        bool(jdbc_user),
        "Missing DB user",
    )

    require(
        bool(jdbc_password),
        "Missing DB password",
    )

    spark = (
        SparkSession.builder
        .appName(
            "TASK003-STEP06A3-Visit-ID-Reconciliation"
        )
        .getOrCreate()
    )

    try:
        candidate = spark.read.parquet(
            candidate_uri
        )

        required_columns = {
            "source_system",
            "source_encounter_id",
            "person_id",
        }

        missing = (
            required_columns
            - set(
                candidate.columns
            )
        )

        require(
            not missing,
            "Candidate missing columns: "
            + repr(
                sorted(missing)
            ),
        )

        candidate_rows = (
            candidate.count()
        )

        require(
            candidate_rows
            == EXPECTED_ROWS,
            "Candidate row count mismatch",
        )

        invalid_keys = (
            candidate.filter(
                F.col(
                    "source_system"
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
                | F.col(
                    "source_encounter_id"
                ).isNull()
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
            )
            .count()
        )

        require(
            invalid_keys == 0,
            "Candidate contains null/blank business keys",
        )

        source_systems = [
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
            source_systems
            == [
                EXPECTED_SOURCE_SYSTEM
            ],
            "Unexpected source systems: "
            + repr(
                source_systems
            ),
        )

        candidate_keys_df = (
            candidate
            .select(
                "source_system",
                "source_encounter_id",
            )
            .distinct()
        )

        candidate_unique_keys = (
            candidate_keys_df.count()
        )

        require(
            candidate_unique_keys
            == EXPECTED_KEYS,
            "Candidate business-key count mismatch",
        )

        duplicate_candidate_groups = (
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
            duplicate_candidate_groups == 0,
            "Duplicate Candidate business keys",
        )

        referenced_persons = (
            candidate
            .select(
                "person_id"
            )
            .distinct()
            .count()
        )

        require(
            referenced_persons
            == EXPECTED_PERSONS,
            "Referenced Person count mismatch",
        )

        jdbc_reader = (
            spark.read
            .format(
                "jdbc"
            )
            .option(
                "url",
                jdbc_url,
            )
            .option(
                "driver",
                "org.postgresql.Driver",
            )
            .option(
                "user",
                jdbc_user,
            )
            .option(
                "password",
                jdbc_password,
            )
            .option(
                "sessionInitStatement",
                "SET default_transaction_read_only = on",
            )
        )

        visit_map = (
            jdbc_reader
            .option(
                "dbtable",
                """(
                    SELECT
                        visit_occurrence_id,
                        source_system,
                        source_encounter_id
                    FROM etl.visit_occurrence_id_map
                ) AS visit_map"""
            )
            .load()
        )

        map_rows = (
            visit_map.count()
        )

        map_duplicate_business_keys = (
            visit_map
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

        map_duplicate_visit_ids = (
            visit_map
            .groupBy(
                "visit_occurrence_id"
            )
            .count()
            .filter(
                F.col("count") > 1
            )
            .count()
        )

        require(
            map_duplicate_business_keys == 0,
            "DB map contains duplicate business keys",
        )

        require(
            map_duplicate_visit_ids == 0,
            "DB map contains duplicate Visit IDs",
        )

        synthetic_map = (
            visit_map
            .filter(
                F.col(
                    "source_system"
                )
                == EXPECTED_SOURCE_SYSTEM
            )
        )

        synthetic_map_rows = (
            synthetic_map.count()
        )

        joined = (
            candidate_keys_df
            .alias(
                "c"
            )
            .join(
                synthetic_map.alias(
                    "m"
                ),
                on=(
                    (
                        F.col(
                            "c.source_system"
                        )
                        == F.col(
                            "m.source_system"
                        )
                    )
                    & (
                        F.col(
                            "c.source_encounter_id"
                        )
                        == F.col(
                            "m.source_encounter_id"
                        )
                    )
                ),
                how="left",
            )
            .select(
                F.col(
                    "c.source_system"
                ).alias(
                    "source_system"
                ),
                F.col(
                    "c.source_encounter_id"
                ).alias(
                    "source_encounter_id"
                ),
                F.col(
                    "m.visit_occurrence_id"
                ).alias(
                    "visit_occurrence_id"
                ),
            )
        )

        reconciled_rows = (
            joined.count()
        )

        require(
            reconciled_rows
            == EXPECTED_KEYS,
            "Reconciliation row count mismatch",
        )

        existing_mappings = (
            joined
            .filter(
                F.col(
                    "visit_occurrence_id"
                ).isNotNull()
            )
            .count()
        )

        new_mappings = (
            joined
            .filter(
                F.col(
                    "visit_occurrence_id"
                ).isNull()
            )
            .count()
        )

        require(
            (
                existing_mappings
                + new_mappings
            )
            == EXPECTED_KEYS,
            "Existing/new reconciliation total mismatch",
        )

        candidate_only_keys = (
            new_mappings
        )

        map_only_keys = (
            synthetic_map
            .alias(
                "m"
            )
            .join(
                candidate_keys_df.alias(
                    "c"
                ),
                on=(
                    (
                        F.col(
                            "m.source_system"
                        )
                        == F.col(
                            "c.source_system"
                        )
                    )
                    & (
                        F.col(
                            "m.source_encounter_id"
                        )
                        == F.col(
                            "c.source_encounter_id"
                        )
                    )
                ),
                how="left_anti",
            )
            .count()
        )

        candidate_key_rows = (
            candidate_keys_df
            .orderBy(
                "source_system",
                "source_encounter_id",
            )
            .collect()
        )

        candidate_key_sha = (
            business_key_fingerprint(
                candidate_key_rows
            )
        )

        existing_mapping_rows = (
            joined
            .filter(
                F.col(
                    "visit_occurrence_id"
                ).isNotNull()
            )
            .orderBy(
                "source_system",
                "source_encounter_id",
            )
            .collect()
        )

        existing_mapping_sha = (
            mapping_fingerprint(
                existing_mapping_rows
            )
        )

        sample_new_keys = [
            {
                "source_system":
                    row[
                        "source_system"
                    ],

                "source_encounter_id":
                    row[
                        "source_encounter_id"
                    ],
            }
            for row in (
                joined
                .filter(
                    F.col(
                        "visit_occurrence_id"
                    ).isNull()
                )
                .orderBy(
                    "source_system",
                    "source_encounter_id",
                )
                .limit(
                    10
                )
                .collect()
            )
        ]

        result = {
            "task":
                "TASK-003",

            "step":
                "STEP-06A3",

            "status":
                "VISIT_ID_BUSINESS_KEY_RECONCILIATION_PASS",

            "run_id":
                "visit-proc-20261009t192437z-2081886",

            "candidate": {
                "rows":
                    candidate_rows,

                "unique_business_keys":
                    candidate_unique_keys,

                "referenced_persons":
                    referenced_persons,

                "duplicate_business_key_groups":
                    duplicate_candidate_groups,

                "business_key_sha256":
                    candidate_key_sha,
            },

            "database_map": {
                "total_rows":
                    map_rows,

                "synthea_rows":
                    synthetic_map_rows,

                "duplicate_business_key_groups":
                    map_duplicate_business_keys,

                "duplicate_visit_id_groups":
                    map_duplicate_visit_ids,
            },

            "reconciliation": {
                "rows":
                    reconciled_rows,

                "existing_mappings":
                    existing_mappings,

                "new_mappings":
                    new_mappings,

                "candidate_only_keys":
                    candidate_only_keys,

                "map_only_synthea_keys":
                    map_only_keys,

                "existing_mapping_sha256":
                    existing_mapping_sha,

                "sample_new_keys":
                    sample_new_keys,
            },

            "safety": {
                "s3_read_only":
                    True,

                "jdbc_read_only":
                    True,

                "nextval_called":
                    False,

                "setval_called":
                    False,

                "sequence_advanced":
                    False,

                "visit_id_map_write":
                    False,

                "cdm_visit_occurrence_write":
                    False,
            },
        }

        print(
            "VISIT_ID_RECONCILIATION_RESULT="
            + json.dumps(
                result,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
            )
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

path = Path(sys.argv[1])
source = path.read_text()

ast.parse(source)

forbidden = (
    r'\bnextval\s*\(',
    r'\bsetval\s*\(',
    r'\bINSERT\s+INTO\b',
    r'\bUPDATE\s+',
    r'\bDELETE\s+FROM\b',
    r'\bTRUNCATE\b',
    r'\.write\b',
    r'\.save\s*\(',
    r'\.insertInto\s*\(',
    r'\.saveAsTable\s*\(',
)

for pattern in forbidden:
    assert not re.search(
        pattern,
        source,
        re.IGNORECASE,
    ), pattern

required = (
    'VISIT_ID_RECONCILIATION_RESULT=',
    'sessionInitStatement',
    'SET default_transaction_read_only = on',
    'source_encounter_id',
    'business_key_sha256',
    'existing_mappings',
    'new_mappings',
    'left_anti',
)

for token in required:
    assert token in source, token

print('A3_DRIVER_SYNTAX=PASS')
print('A3_DRIVER_STATIC_READ_ONLY=PASS')
print('A3_DRIVER_DB_WRITE_PATH=ABSENT')
print('A3_DRIVER_S3_WRITE_PATH=ABSENT')
PY_STATIC

echo '=== 7. Create reconciliation ConfigMap ==='

kubectl -n "$NS" \
  create configmap "$CM" \
  --from-file=reconcile_visit_id_keys.py="$DRIVER"

echo "A3_CONFIGMAP_CREATED=$CM"

echo '=== 8. Build SparkApplication from proven runtime ==='

python3 - \
  "$SOURCE_APP_JSON" \
  "$APP_JSON" \
  "$SECRET_MAP" \
  "$APP" \
  "$CM" \
  "$DB_SECRET" \
  "$PROCESSED_DATA_URI" \
  <<'PY_APP'
import copy
import json
import sys
from pathlib import Path

source_path = Path(
    sys.argv[1]
)

target_path = Path(
    sys.argv[2]
)

secret_map_path = Path(
    sys.argv[3]
)

app_name = sys.argv[4]
configmap_name = sys.argv[5]
db_secret = sys.argv[6]
candidate_uri = sys.argv[7]

source = json.loads(
    source_path.read_bytes()
)

mapping = json.loads(
    secret_map_path.read_bytes()
)

spec = copy.deepcopy(
    source[
        'spec'
    ]
)

spec[
    'mainApplicationFile'
] = (
    'local:///opt/spark/a3/'
    'reconcile_visit_id_keys.py'
)

spec[
    'arguments'
] = [
    candidate_uri,
]

spec[
    'restartPolicy'
] = {
    'type': 'Never',
}

# Remove old ConfigMap-backed runtime artifacts.
# Keep PVCs and Secrets because they may provide
# proven Spark/JAR/S3 runtime dependencies.
old_volumes = spec.get(
    'volumes',
    [],
)

removed_names = {
    volume.get(
        'name'
    )
    for volume in old_volumes
    if 'configMap' in volume
}

spec[
    'volumes'
] = [
    volume
    for volume in old_volumes
    if volume.get(
        'name'
    )
    not in removed_names
]

spec[
    'volumes'
].append(
    {
        'name':
            'a3-app',

        'configMap': {
            'name':
                configmap_name,
        },
    }
)

def remove_old_mounts(section):
    obj = spec.setdefault(
        section,
        {},
    )

    mounts = obj.get(
        'volumeMounts',
        [],
    )

    obj[
        'volumeMounts'
    ] = [
        mount
        for mount in mounts
        if mount.get(
            'name'
        )
        not in removed_names
        and mount.get(
            'name'
        )
        != 'a3-app'
    ]

    obj[
        'volumeMounts'
    ].append(
        {
            'name':
                'a3-app',

            'mountPath':
                '/opt/spark/a3',

            'readOnly':
                True,
        }
    )

    return obj


driver = remove_old_mounts(
    'driver'
)

executor = remove_old_mounts(
    'executor'
)

# The Python application only needs DB credentials
# in the driver. JDBC options are propagated by Spark.
driver_env = driver.setdefault(
    'env',
    [],
)

reserved_names = {
    'A3_DB_JDBC_URL',
    'A3_DB_USER',
    'A3_DB_PASSWORD',
    'A3_DB_HOST',
    'A3_DB_PORT',
    'A3_DB_NAME',
}

driver[
    'env'
] = [
    item
    for item in driver_env
    if item.get(
        'name'
    )
    not in reserved_names
]

def add_secret_env(
    env_name,
    secret_key,
):
    if not secret_key:
        return

    driver[
        'env'
    ].append(
        {
            'name':
                env_name,

            'valueFrom': {
                'secretKeyRef': {
                    'name':
                        db_secret,

                    'key':
                        secret_key,
                },
            },
        }
    )


add_secret_env(
    'A3_DB_JDBC_URL',
    mapping.get(
        'jdbc_url'
    ),
)

add_secret_env(
    'A3_DB_USER',
    mapping.get(
        'username'
    ),
)

add_secret_env(
    'A3_DB_PASSWORD',
    mapping.get(
        'password'
    ),
)

add_secret_env(
    'A3_DB_HOST',
    mapping.get(
        'host'
    ),
)

add_secret_env(
    'A3_DB_PORT',
    mapping.get(
        'port'
    ),
)

add_secret_env(
    'A3_DB_NAME',
    mapping.get(
        'database'
    ),
)

# Ensure Spark driver identity stays on the proven SA.
driver.setdefault(
    'serviceAccount',
    'spark-job',
)

# Remove old app-specific labels that can confuse
# evidence lookup, then add STEP06A3 identity.
for section in (
    driver,
    executor,
):
    labels = section.setdefault(
        'labels',
        {},
    )

    labels[
        'task'
    ] = 'task003'

    labels[
        'step'
    ] = 'step06a3'

doc = {
    'apiVersion':
        source[
            'apiVersion'
        ],

    'kind':
        source[
            'kind'
        ],

    'metadata': {
        'name':
            app_name,

        'namespace':
            'dw-spark',

        'labels': {
            'task':
                'task003',

            'step':
                'step06a3',

            'purpose':
                'visit-id-reconciliation',
        },
    },

    'spec':
        spec,
}

target_path.write_text(
    json.dumps(
        doc,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('A3_SPARKAPPLICATION_RENDER=PASS')
PY_APP

echo '=== 9. Validate rendered SparkApplication safety ==='

python3 - \
  "$APP_JSON" \
  "$APP" \
  "$CM" \
  "$PROCESSED_DATA_URI" \
  <<'PY_APP_CHECK'
import json
import sys
from pathlib import Path

doc = json.loads(
    Path(sys.argv[1]).read_bytes()
)

app_name = sys.argv[2]
cm_name = sys.argv[3]
candidate_uri = sys.argv[4]

assert doc['metadata']['name'] == app_name

spec = doc['spec']

assert (
    spec['mainApplicationFile']
    == 'local:///opt/spark/a3/reconcile_visit_id_keys.py'
)

assert spec['arguments'] == [
    candidate_uri
]

assert spec['restartPolicy']['type'] == 'Never'

volumes = {
    item['name']:
        item
    for item in spec.get(
        'volumes',
        []
    )
}

assert (
    volumes[
        'a3-app'
    ][
        'configMap'
    ][
        'name'
    ]
    == cm_name
)

driver_env = {
    item['name']:
        item
    for item in spec[
        'driver'
    ].get(
        'env',
        []
    )
}

assert 'A3_DB_USER' in driver_env
assert 'A3_DB_PASSWORD' in driver_env

assert (
    'A3_DB_JDBC_URL'
    in driver_env
    or 'A3_DB_HOST'
    in driver_env
)

blob = json.dumps(
    doc,
    sort_keys=True,
).lower()

assert 'nextval(' not in blob
assert 'setval(' not in blob

print('A3_SPARKAPPLICATION_STATIC_VALIDATION=PASS')
print('A3_DATABASE_SECRET_VALUE_EMBEDDED=NO')
print('A3_NEXTVAL_PATH=ABSENT')
print('A3_SETVAL_PATH=ABSENT')
PY_APP_CHECK

echo '=== 10. Launch real READ ONLY Spark reconciliation ==='

kubectl apply \
  -f "$APP_JSON"

echo "SPARKAPPLICATION_CREATED=$APP"

echo '=== 11. Observe SparkApplication ==='

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

if [[ "$FINAL_STATE" != "COMPLETED" ]]; then
  DRIVER_POD="$(
    kubectl -n "$NS" \
      get sparkapplication "$APP" \
      -o jsonpath='{.status.driverInfo.podName}' \
      2>/dev/null \
      || true
  )"

  echo "FAILED_DRIVER_POD=${DRIVER_POD:-UNKNOWN}"

  if [[ -n "${DRIVER_POD:-}" ]]; then
    kubectl -n "$NS" \
      logs "$DRIVER_POD" \
      > "$DRIVER_LOG" \
      2>&1 \
      || true

    tail -n 200 "$DRIVER_LOG" || true
  fi

  echo 'ERROR: STEP06A3 Spark reconciliation did not complete'
  echo 'FAILED_RUNTIME_RESOURCES_PRESERVED=YES'
  exit 1
fi

echo 'SPARK_RECONCILIATION_APPLICATION=COMPLETED'

echo '=== 12. Capture driver log and reconciliation result ==='

DRIVER_POD="$(
  kubectl -n "$NS" \
    get sparkapplication "$APP" \
    -o jsonpath='{.status.driverInfo.podName}'
)"

echo "DRIVER_POD=$DRIVER_POD"

kubectl -n "$NS" \
  logs "$DRIVER_POD" \
  > "$DRIVER_LOG"

grep \
  'VISIT_ID_RECONCILIATION_RESULT=' \
  "$DRIVER_LOG" \
  | tail -n 1 \
  > "$REPORT/result-marker.txt"

[[ -s "$REPORT/result-marker.txt" ]] || {
  echo 'ERROR: reconciliation result marker missing'
  exit 1
}

python3 - \
  "$REPORT/result-marker.txt" \
  "$RESULT_JSON" \
  <<'PY_RESULT'
import json
import sys
from pathlib import Path

line = Path(
    sys.argv[1]
).read_text().strip()

prefix = (
    'VISIT_ID_RECONCILIATION_RESULT='
)

assert line.startswith(
    prefix
)

result = json.loads(
    line[
        len(prefix):
    ]
)

Path(
    sys.argv[2]
).write_text(
    json.dumps(
        result,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

assert result['task'] == 'TASK-003'
assert result['step'] == 'STEP-06A3'

assert (
    result['status']
    == 'VISIT_ID_BUSINESS_KEY_RECONCILIATION_PASS'
)

candidate = result[
    'candidate'
]

assert candidate['rows'] == 5799
assert candidate['unique_business_keys'] == 5799
assert candidate['referenced_persons'] == 113

assert (
    candidate[
        'duplicate_business_key_groups'
    ]
    == 0
)

assert len(
    candidate[
        'business_key_sha256'
    ]
) == 64

db = result[
    'database_map'
]

assert db['total_rows'] == 0
assert db['synthea_rows'] == 0

assert (
    db[
        'duplicate_business_key_groups'
    ]
    == 0
)

assert (
    db[
        'duplicate_visit_id_groups'
    ]
    == 0
)

recon = result[
    'reconciliation'
]

assert recon['rows'] == 5799
assert recon['existing_mappings'] == 0
assert recon['new_mappings'] == 5799
assert recon['candidate_only_keys'] == 5799
assert recon['map_only_synthea_keys'] == 0

safety = result[
    'safety'
]

assert safety['s3_read_only'] is True
assert safety['jdbc_read_only'] is True
assert safety['nextval_called'] is False
assert safety['setval_called'] is False
assert safety['sequence_advanced'] is False
assert safety['visit_id_map_write'] is False
assert safety['cdm_visit_occurrence_write'] is False

print('A3_RECONCILIATION_RESULT=PASS')

print(
    'CANDIDATE_BUSINESS_KEY_SHA256='
    + candidate[
        'business_key_sha256'
    ]
)

print(
    'EXISTING_MAPPING_SHA256='
    + recon[
        'existing_mapping_sha256'
    ]
)

print('EXISTING_CANDIDATE_MAPPINGS=0')
print('NEW_CANDIDATE_MAPPINGS=5799')
print('CANDIDATE_ONLY_KEYS=5799')
print('MAP_ONLY_SYNTHEA_KEYS=0')
PY_RESULT

cat "$RESULT_JSON"

echo '=== 13. Independent post-Spark PostgreSQL immutability check ==='

kubectl -n "$DB_NS" \
  exec -i "$DB_POD" -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB" \
    -A \
    -t \
    -F '|' \
    -P pager=off \
  > "$DB_POSTCHECK" <<'SQL'
BEGIN;
SET TRANSACTION READ ONLY;

SELECT
    (SELECT count(*)
       FROM etl.visit_occurrence_id_map),
    (SELECT count(*)
       FROM cdm.visit_occurrence),
    (SELECT count(*)
       FROM etl.person_id_map);

SELECT
    last_value,
    is_called
FROM etl.visit_occurrence_id_map_visit_occurrence_id_seq;

SELECT
    current_setting('transaction_read_only');

ROLLBACK;
SQL

cat "$DB_POSTCHECK"

python3 - \
  "$DB_POSTCHECK" \
  <<'PY_POST'
import sys
from pathlib import Path

rows = [
    line.strip()
    for line in Path(sys.argv[1]).read_text().splitlines()
    if line.strip()
    and line.strip() not in {
        'BEGIN',
        'SET',
        'ROLLBACK',
    }
]

assert rows == [
    '0|0|113',
    '1|f',
    'on',
], rows

print('POST_A3_DATABASE_IMMUTABILITY=PASS')
print('VISIT_MAP_ROWS_AFTER_A3=0')
print('CDM_VISIT_ROWS_AFTER_A3=0')
print('PERSON_MAP_ROWS_AFTER_A3=113')
print('SEQUENCE_LAST_VALUE_AFTER_A3=1')
print('SEQUENCE_IS_CALLED_AFTER_A3=FALSE')
PY_POST

echo '=== 14. Record STEP06A3 evidence ==='

python3 - \
  "$RESULT_JSON" \
  "$RUN_STATE" \
  "$PLAN" \
  "$HEAD" \
  "$SOURCE_APP" \
  "$APP" \
  "$CM" \
  <<'PY_STATE'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

result_path = Path(
    sys.argv[1]
)

state_path = Path(
    sys.argv[2]
)

plan_path = Path(
    sys.argv[3]
)

head = sys.argv[4]
source_app = sys.argv[5]
app = sys.argv[6]
cm = sys.argv[7]

result = json.loads(
    result_path.read_bytes()
)

def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()

state = {
    'task':
        'TASK-003',

    'step':
        'STEP-06A3',

    'status':
        'VISIT_ID_BUSINESS_KEY_RECONCILIATION_VERIFIED',

    'run_id':
        'visit-proc-20261009t192437z-2081886',

    'git_checkpoint':
        head,

    'allocation_plan_sha256':
        sha(
            plan_path
        ),

    'reconciliation_result_sha256':
        sha(
            result_path
        ),

    'candidate_business_key_sha256':
        result[
            'candidate'
        ][
            'business_key_sha256'
        ],

    'candidate_rows':
        5799,

    'candidate_unique_business_keys':
        5799,

    'existing_candidate_mappings':
        0,

    'new_candidate_mappings':
        5799,

    'candidate_only_keys':
        5799,

    'map_only_synthea_keys':
        0,

    'source_sparkapplication':
        source_app,

    'sparkapplication':
        app,

    'runtime_configmap':
        cm,

    's3_read_only':
        True,

    'database_read_only':
        True,

    'visit_id_allocation_started':
        False,

    'visit_id_map_mutated':
        False,

    'sequence_advanced':
        False,

    'cdm_visit_occurrence_write':
        False,

    'observed_at_utc':
        datetime.now(
            timezone.utc
        ).isoformat(),
}

state_path.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('STEP06A3_RUN_STATE=PASS')

print(
    'STEP06A3_RESULT_SHA256='
    + state[
        'reconciliation_result_sha256'
    ]
)

print(
    'CANDIDATE_BUSINESS_KEY_SHA256='
    + state[
        'candidate_business_key_sha256'
    ]
)
PY_STATE

echo '=== 15. Final STEP06A3 verdict ==='

echo 'STEP06A3_VISIT_BUSINESS_KEY_RECONCILIATION=PASS'

echo 'FROZEN_CANDIDATE_ROWS=5799'
echo 'FROZEN_CANDIDATE_UNIQUE_KEYS=5799'
echo 'FROZEN_CANDIDATE_PERSONS=113'

echo 'EXISTING_CANDIDATE_MAPPINGS=0'
echo 'NEW_CANDIDATE_MAPPINGS=5799'
echo 'CANDIDATE_ONLY_KEYS=5799'
echo 'MAP_ONLY_SYNTHEA_KEYS=0'

echo 'BUSINESS_KEY_FINGERPRINT_CAPTURED=YES'

echo 'S3_ACCESS=READ_ONLY'
echo 'DATABASE_ACCESS=READ_ONLY'

echo 'NEXTVAL_CALLED=NO'
echo 'SETVAL_CALLED=NO'

echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'KUBERNETES_RUNTIME_RESOURCES_CREATED=YES'
echo 'RUNTIME_RESOURCES_AUTOMATIC_CLEANUP=NO'

echo 'GIT_COMMIT=NO'

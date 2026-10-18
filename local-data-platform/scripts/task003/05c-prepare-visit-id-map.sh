#!/usr/bin/env bash
set -Eeuo pipefail

echo '#### TASK003 STEP05C SOURCE INSTALL OUTPUT BEGIN ####'
STAGE=""
finish() {
    rc=$?
    trap - EXIT
    if [[ -n "${STAGE}" ]]; then
        rm -rf -- "${STAGE}"
    fi
    echo "INSTALL_EXIT_CODE=${rc}"
    echo '#### TASK003 STEP05C SOURCE INSTALL OUTPUT END ####'
    exit "${rc}"
}
trap finish EXIT

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
[[ -d "${ROOT}/scripts/task003" ]] || {
    echo 'ERROR: project missing'
    exit 1
}
STAGE="$(mktemp -d)"

cat > "${STAGE}/visit-id-map-foundation.sql" <<'SQL_FOUNDATION'
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL search_path = pg_catalog, public;

CREATE TEMP TABLE expected_visit_id_map (
    visit_occurrence_id integer GENERATED ALWAYS AS IDENTITY
        (MINVALUE 1 MAXVALUE 2147483647 NO CYCLE),
    source_system varchar(50) NOT NULL,
    source_encounter_id varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (visit_occurrence_id),
    UNIQUE (source_system, source_encounter_id),
    CHECK (visit_occurrence_id > 0),
    CHECK (btrim(source_system) <> ''),
    CHECK (btrim(source_encounter_id) <> '')
) ON COMMIT DROP;

DO $body$
DECLARE
    target regclass;
    expected regclass := 'pg_temp.expected_visit_id_map'::regclass;
    item regclass;
    seq_id regclass;
    expected_seq regclass;
    actual_columns jsonb;
    expected_columns jsonb;
    actual_constraints jsonb;
    expected_constraints jsonb;
    signature jsonb;
    seq_state jsonb;
    action text := 'REUSED';
    map_rows bigint;
    visit_rows bigint;
BEGIN
    -- Shared transaction lock name must also be used by the future allocator.
    PERFORM pg_advisory_xact_lock(3003, 5001);

    IF current_database() <> 'omop' THEN
        RAISE EXCEPTION 'Wrong database';
    END IF;

    LOCK TABLE cdm.visit_occurrence IN SHARE ROW EXCLUSIVE MODE;
    SELECT count(*) INTO visit_rows FROM cdm.visit_occurrence;
    target := to_regclass('etl.visit_occurrence_id_map');

    IF target IS NULL THEN
        IF visit_rows <> 0 THEN
            RAISE EXCEPTION
                'Visit data exists without ID map; stop for reconciliation';
        END IF;

        CREATE TABLE etl.visit_occurrence_id_map (
            visit_occurrence_id integer GENERATED ALWAYS AS IDENTITY
                (MINVALUE 1 MAXVALUE 2147483647 NO CYCLE),
            source_system varchar(50) NOT NULL,
            source_encounter_id varchar(255) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (visit_occurrence_id),
            UNIQUE (source_system, source_encounter_id),
            CHECK (visit_occurrence_id > 0),
            CHECK (btrim(source_system) <> ''),
            CHECK (btrim(source_encounter_id) <> '')
        );

        action := 'CREATED';
        target := 'etl.visit_occurrence_id_map'::regclass;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = target
          AND relkind = 'r'
          AND relpersistence = 'p'
          AND NOT relispartition
          AND NOT relrowsecurity
    ) OR EXISTS (
        SELECT 1 FROM pg_inherits
        WHERE inhrelid = target OR inhparent = target
    ) THEN
        RAISE EXCEPTION 'Unexpected Visit ID map relation type';
    END IF;

    LOCK TABLE etl.visit_occurrence_id_map
        IN SHARE ROW EXCLUSIVE MODE;

    FOREACH item IN ARRAY ARRAY[expected, target] LOOP
        SELECT jsonb_agg(jsonb_build_array(
            a.attname,
            format_type(a.atttypid, a.atttypmod),
            a.attnotnull,
            a.attidentity,
            a.attgenerated,
            pg_get_expr(d.adbin, d.adrelid)
        ) ORDER BY a.attnum)
        INTO actual_columns
        FROM pg_attribute a
        LEFT JOIN pg_attrdef d
          ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE a.attrelid = item
          AND a.attnum > 0
          AND NOT a.attisdropped;

        SELECT jsonb_agg(jsonb_build_array(
            contype,
            pg_get_constraintdef(oid),
            convalidated,
            condeferrable,
            condeferred
        ) ORDER BY contype, pg_get_constraintdef(oid))
        INTO actual_constraints
        FROM pg_constraint
        WHERE conrelid = item;

        IF item = expected THEN
            expected_columns := actual_columns;
            expected_constraints := actual_constraints;
        ELSIF actual_columns IS DISTINCT FROM expected_columns
           OR actual_constraints IS DISTINCT FROM expected_constraints
        THEN
            RAISE EXCEPTION
                'Existing Visit ID map schema differs; no automatic migration';
        END IF;
    END LOOP;

    IF EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = target AND NOT tgisinternal
    ) THEN
        RAISE EXCEPTION 'Unexpected custom trigger on Visit ID map';
    END IF;

    seq_id := pg_get_serial_sequence(
        'etl.visit_occurrence_id_map',
        'visit_occurrence_id'
    )::regclass;

    expected_seq := pg_get_serial_sequence(
        'pg_temp.expected_visit_id_map',
        'visit_occurrence_id'
    )::regclass;

    IF seq_id IS NULL OR NOT EXISTS (
        SELECT 1 FROM pg_sequence a, pg_sequence e
        WHERE a.seqrelid = seq_id
          AND e.seqrelid = expected_seq
          AND ROW(
              a.seqtypid, a.seqstart, a.seqincrement, a.seqmax,
              a.seqmin, a.seqcache, a.seqcycle
          ) = ROW(
              e.seqtypid, e.seqstart, e.seqincrement, e.seqmax,
              e.seqmin, e.seqcache, e.seqcycle
          )
    ) THEN
        RAISE EXCEPTION 'Unexpected Visit identity sequence definition';
    END IF;

    -- Reading these fields does not call nextval or advance the sequence.
    EXECUTE format(
        'SELECT jsonb_build_object(''last_value'',last_value,''is_called'',is_called) FROM %s',
        seq_id
    ) INTO seq_state;

    SELECT count(*) INTO map_rows
    FROM etl.visit_occurrence_id_map;

    signature := jsonb_build_object(
        'columns', actual_columns,
        'constraints', actual_constraints
    );

    PERFORM set_config(
        'healthcare.foundation_result',
        jsonb_build_object(
            'status', 'PASS',
            'action', action,
            'map_rows', map_rows,
            'cdm_visit_rows', visit_rows,
            'sequence', seq_id::text,
            'sequence_state', seq_state,
            'schema', signature,
            'ids_allocated', 0
        )::text,
        true
    );
END
$body$;

SELECT current_setting('healthcare.foundation_result');
COMMIT;
SQL_FOUNDATION

cat > "${STAGE}/05c-create-visit-id-map.sh" <<'SH_RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail

echo '#### TASK003 STEP05C ID MAP OUTPUT BEGIN ####'
trap 'rc=$?; echo "FOUNDATION_EXIT_CODE=${rc}"; echo "#### TASK003 STEP05C ID MAP OUTPUT END ####"; exit "${rc}"' EXIT

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ $# -eq 1 ]] || {
    echo "Usage: $0 STEP05B_BASELINE_JSON"
    exit 2
}

SQL="${ROOT}/sql/task003/visit-id-map-foundation.sql"
mkdir -p "${ROOT}/runtime/reports/task003/step05"
REPORT="$(mktemp -d "${ROOT}/runtime/reports/task003/step05/id-map.XXXXXX")"
echo "FOUNDATION_REPORT=${REPORT}"

python3 - "$1" "${REPORT}" "${ROOT}" <<'PY'
import hashlib, json, sys
from pathlib import Path

source, report, root = map(Path, sys.argv[1:])
raw = source.read_bytes()
b = json.loads(raw)

if (b.get('task'), b.get('step'), b.get('status')) != (
    'TASK-003', 'STEP-05B', 'CAPTURED'
):
    raise SystemExit('ERROR: invalid STEP05B baseline')

if (
    b['database']['read_only'] != 'on'
    or b['database']['database'] != 'omop'
):
    raise SystemExit('ERROR: unexpected baseline database')

query = root / 'sql/task003/visit-mapping-baseline.sql'
if hashlib.sha256(query.read_bytes()).hexdigest() != b['sql_sha256']:
    raise SystemExit('ERROR: baseline SQL changed')

(report / 'input-baseline.json').write_bytes(raw)
print('STEP05B_BASELINE=PASS')
PY

# Both executions use transactional DDL. No source keys are inserted.
for attempt in first replay; do
    echo "FOUNDATION_ATTEMPT=${attempt}"

    if kubectl exec -i -n dw-postgre dw-postgre-database-0 -- \
        psql -X -qAt -v ON_ERROR_STOP=1 -P pager=off \
        -U omop_admin -d omop \
        < "${SQL}" \
        > "${REPORT}/${attempt}.json" \
        2> "${REPORT}/${attempt}.stderr.log"
    then
        cat "${REPORT}/${attempt}.json"
    else
        cat "${REPORT}/${attempt}.stderr.log"
        exit 1
    fi
done

python3 - "${REPORT}" "${SQL}" <<'PY'
import hashlib, json, sys
from pathlib import Path

report, sql = map(Path, sys.argv[1:])
a = json.loads((report / 'first.json').read_text())
b = json.loads((report / 'replay.json').read_text())

if a.get('status') != 'PASS' or b.get('status') != 'PASS':
    raise SystemExit('ERROR: database validation failed')

if (
    a.get('action') not in ('CREATED', 'REUSED')
    or b.get('action') != 'REUSED'
):
    raise SystemExit('ERROR: unexpected replay action')

first_state = {k: v for k, v in a.items() if k != 'action'}
replay_state = {k: v for k, v in b.items() if k != 'action'}
if first_state != replay_state:
    raise SystemExit('ERROR: schema/rows/sequence changed between runs')

if a['ids_allocated'] != 0:
    raise SystemExit('ERROR: unexpected ID allocation')

if a['action'] == 'CREATED' and (
    a['map_rows'] != 0
    or a['cdm_visit_rows'] != 0
    or a['sequence_state'] != {'last_value': 1, 'is_called': False}
):
    raise SystemExit('ERROR: unexpected fresh foundation state')

state = dict(
    task='TASK-003',
    step='STEP-05C',
    status='PASS',
    scope='stable_id_map_foundation',
    first=a,
    replay=b,
    sql_sha256=hashlib.sha256(sql.read_bytes()).hexdigest(),
    input_baseline_sha256=hashlib.sha256(
        (report / 'input-baseline.json').read_bytes()
    ).hexdigest(),
    raw_remote_verified=False,
    cdm_write=False,
)
(report / 'run-state.json').write_text(
    json.dumps(state, indent=2) + '\n'
)

print('ID_MAP_SCHEMA=PASS')
print('ID_MAP_REPLAY=PASS')
print('SEQUENCE_UNCHANGED_ON_REPLAY=PASS')
print('MAP_ROWS=' + str(b['map_rows']))
print('CDM_VISIT_ROWS=' + str(b['cdm_visit_rows']))
print(
    'PERSISTENT_DDL='
    + ('CREATED' if a['action'] == 'CREATED' else 'REUSED')
)
PY

echo "RUN_STATE=${REPORT}/run-state.json"
echo 'IDS_ALLOCATED=0'
echo 'CDM_WRITE=NO'
echo 'S3_WRITE=NO'
echo 'REMOTE_RAW_REVALIDATION=PENDING'
SH_RUNNER

cp -- "${BASH_SOURCE[0]}" "${STAGE}/05c-prepare-visit-id-map.sh"

bash -n "${STAGE}/05c-create-visit-id-map.sh"
bash -n "${STAGE}/05c-prepare-visit-id-map.sh"

FILES=(
    sql/task003/visit-id-map-foundation.sql
    scripts/task003/05c-create-visit-id-map.sh
    scripts/task003/05c-prepare-visit-id-map.sh
)

for rel in "${FILES[@]}"; do
    target="${ROOT}/${rel}"
    if [[ -L "${target}" ]] || {
        [[ -e "${target}" ]] &&
        ! cmp -s "${STAGE}/${rel##*/}" "${target}"
    }; then
        echo "ERROR: existing source conflicts: ${rel}"
        exit 1
    fi
done

for rel in "${FILES[@]}"; do
    mkdir -p -- "$(dirname "${ROOT}/${rel}")"
    mode=644
    [[ "${rel}" != *.sh ]] || mode=755

    install -m "${mode}" \
        "${STAGE}/${rel##*/}" \
        "${ROOT}/${rel}"

    echo "SOURCE_READY=${rel}"
done

echo 'STEP05C_SOURCE_INSTALL=PASS'
echo 'DATABASE_WRITE=NO'

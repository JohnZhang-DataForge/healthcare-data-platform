#!/usr/bin/env bash
set -Eeuo pipefail

echo "#### TASK003 STEP05B SOURCE INSTALL OUTPUT BEGIN ####"

STAGE=""
finish() {
    rc=$?
    trap - EXIT
    if [[ -n "${STAGE}" ]]; then
        rm -rf -- "${STAGE}"
    fi
    echo "INSTALL_EXIT_CODE=${rc}"
    echo "#### TASK003 STEP05B SOURCE INSTALL OUTPUT END ####"
    exit "${rc}"
}
trap finish EXIT

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
[[ -d "${ROOT}/spark/contracts" ]] || {
    echo "ERROR: project root missing"
    exit 1
}
STAGE="$(mktemp -d)"

cat > "${STAGE}/visit-mapping-baseline.sql" <<'SQL_BASELINE'
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '30s';
SET LOCAL lock_timeout = '5s';

WITH wanted(name) AS (
    VALUES ('cdm.visit_occurrence'), ('etl.person_id_map'),
           ('etl.visit_occurrence_id_map')
), relations AS (
    SELECT name, to_regclass(name) AS oid FROM wanted
)
SELECT jsonb_build_object(
    'report', 'database_baseline',
    'database', current_database(),
    'captured_at', transaction_timestamp(),
    'read_only', current_setting('transaction_read_only'),
    'isolation', current_setting('transaction_isolation'),
    'person_rows', (SELECT count(*) FROM cdm.person),
    'synthea_person_map_rows',
        (SELECT count(*) FROM etl.person_id_map WHERE source_system = 'synthea'),
    'visit_rows', (SELECT count(*) FROM cdm.visit_occurrence),
    'max_visit_id', (SELECT max(visit_occurrence_id) FROM cdm.visit_occurrence),
    'tables', (
        SELECT jsonb_agg(jsonb_build_object(
            'name', r.name, 'exists', r.oid IS NOT NULL,
            'columns', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                    'position', a.attnum, 'name', a.attname,
                    'type', format_type(a.atttypid, a.atttypmod),
                    'nullable', NOT a.attnotnull, 'identity', a.attidentity,
                    'default', pg_get_expr(d.adbin, d.adrelid)
                ) ORDER BY a.attnum)
                FROM pg_attribute a
                LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                WHERE a.attrelid = r.oid AND a.attnum > 0 AND NOT a.attisdropped
            ), '[]'::jsonb),
            'constraints', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                    'name', c.conname, 'definition', pg_get_constraintdef(c.oid)
                ) ORDER BY c.conname)
                FROM pg_constraint c WHERE c.conrelid = r.oid
            ), '[]'::jsonb),
            'indexes', COALESCE((
                SELECT jsonb_agg(pg_get_indexdef(i.indexrelid) ORDER BY i.indexrelid)
                FROM pg_index i WHERE i.indrelid = r.oid
            ), '[]'::jsonb)
        ) ORDER BY r.name) FROM relations r
    ),
    'concepts', (
        SELECT jsonb_agg(jsonb_build_object(
            'requested_id', requested.id, 'found', c.concept_id IS NOT NULL,
            'name', c.concept_name, 'domain', c.domain_id,
            'standard', c.standard_concept, 'invalid_reason', c.invalid_reason,
            'valid_start_date', c.valid_start_date, 'valid_end_date', c.valid_end_date
        ) ORDER BY requested.id)
        FROM unnest(ARRAY[:concept_ids]::integer[]) AS requested(id)
        LEFT JOIN cdm.concept c ON c.concept_id = requested.id
    ),
    'visit_sequences', COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'schema', schemaname, 'name', sequencename,
            'type', data_type::text, 'start', start_value,
            'increment', increment_by, 'max', max_value,
            'last_value', last_value, 'cycle', cycle
        ) ORDER BY schemaname, sequencename)
        FROM pg_sequences
        WHERE schemaname IN ('etl', 'cdm')
          AND (sequencename ILIKE '%visit%' OR sequencename ILIKE '%encounter%')
    ), '[]'::jsonb)
);

-- Only generate a SELECT for an existing optional map; never create it here.
SELECT CASE WHEN to_regclass('etl.visit_occurrence_id_map') IS NULL THEN
    $$SELECT jsonb_build_object('report','visit_map_count','exists',false,'rows',NULL);$$
ELSE
    $$SELECT jsonb_build_object('report','visit_map_count','exists',true,'rows',count(*)) FROM etl.visit_occurrence_id_map;$$
END
\gexec

COMMIT;
SQL_BASELINE

cat > "${STAGE}/05b-inspect-visit-database.sh" <<'SH_RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_PAGER=cat

echo "#### TASK003 STEP05B DATABASE BASELINE OUTPUT BEGIN ####"
trap 'rc=$?; echo "BASELINE_EXIT_CODE=${rc}"; echo "#### TASK003 STEP05B DATABASE BASELINE OUTPUT END ####"; exit "${rc}"' EXIT

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ "$#" -eq 1 ]] || {
    echo "Usage: $0 INPUT_CONTEXT_JSON"
    exit 2
}
SQL="${ROOT}/sql/task003/visit-mapping-baseline.sql"
mkdir -p "${ROOT}/runtime/reports/task003/step05"
REPORT="$(mktemp -d "${ROOT}/runtime/reports/task003/step05/database.XXXXXX")"
echo "BASELINE_REPORT_DIR=${REPORT}"

CONCEPT_IDS="$(python3 - "${ROOT}" "$1" "${REPORT}" <<'PY_CONTEXT'
import hashlib, json, sys
from pathlib import Path

root, source, report = map(Path, sys.argv[1:])
raw = source.read_bytes()
context = json.loads(raw)

for key, value in dict(
    task="TASK-003", step="STEP-05A", status="PASS", source="synthea"
).items():
    if context.get(key) != value:
        raise SystemExit("ERROR: unexpected input context: " + key)

for name, key in (
    ("canonical/encounter-v1.json", "canonical_contract_sha256"),
    ("omop/visit-class-v1.json", "mapping_contract_sha256"),
):
    data = (root / "spark/contracts" / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != context[key]:
        raise SystemExit("ERROR: contract changed since STEP05A: " + name)

rule = json.loads(
    (root / "spark/contracts/omop/visit-class-v1.json").read_text()
)
ids = [x["concept_id"] for x in rule["class_to_visit_concept"].values()]
ids.append(rule["visit_type_concept_id"])
if any(type(x) is not int or not 0 < x <= 2147483647 for x in ids):
    raise SystemExit("ERROR: invalid concept ID")

(report / "input-context.json").write_bytes(raw)
print(",".join(map(str, sorted(set(ids)))))
PY_CONTEXT
)"

# Reuse the existing PostgreSQL Pod access from TASK003 discovery.
if kubectl exec -i -n dw-postgre dw-postgre-database-0 -- \
    psql -X -qAt -v ON_ERROR_STOP=1 -P pager=off \
    -v "concept_ids=${CONCEPT_IDS}" -U omop_admin -d omop \
    < "${SQL}" \
    > "${REPORT}/database.jsonl" \
    2> "${REPORT}/database.stderr.log"
then
    :
else
    cat "${REPORT}/database.stderr.log"
    exit 1
fi

python3 - "${REPORT}" "${SQL}" <<'PY_RESULT'
import hashlib, json, sys
from pathlib import Path

report, sql = map(Path, sys.argv[1:])
rows = [
    json.loads(line)
    for line in (report / "database.jsonl").read_text().splitlines()
    if line.strip()
]
if len(rows) != 2 or [r.get("report") for r in rows] != [
    "database_baseline", "visit_map_count"
]:
    raise SystemExit("ERROR: incomplete database baseline")

db, visit_map = rows
if (
    db.get("database") != "omop"
    or db.get("read_only") != "on"
    or db.get("isolation") != "repeatable read"
):
    raise SystemExit("ERROR: database/read-only transaction mismatch")

result = dict(
    task="TASK-003",
    step="STEP-05B",
    status="CAPTURED",
    validation_scope="database_inventory",
    database_write=False,
    input_context_sha256=hashlib.sha256(
        (report / "input-context.json").read_bytes()
    ).hexdigest(),
    sql_sha256=hashlib.sha256(sql.read_bytes()).hexdigest(),
    database=db,
    visit_id_map=visit_map,
)
(report / "baseline.json").write_text(
    json.dumps(result, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(result, indent=2))
print("DB_READ_ONLY=PASS")
print("DB_BASELINE_CAPTURE=PASS")
print("CDM_PERSON_ROWS=" + str(db["person_rows"]))
print("CDM_VISIT_ROWS=" + str(db["visit_rows"]))
print("VISIT_ID_MAP_EXISTS=" + str(visit_map["exists"]).lower())
print("VISIT_ID_MAP_ROWS=" + str(visit_map["rows"]))
PY_RESULT

echo "BASELINE_FILE=${REPORT}/baseline.json"
echo "STEP05_MAPPING_EXECUTED=NO"
echo "S3_WRITE=NO"
echo "DATABASE_WRITE=NO"
SH_RUNNER

cp -- "${BASH_SOURCE[0]}" "${STAGE}/05b-prepare-visit-db-baseline.sh"
bash -n "${STAGE}/05b-inspect-visit-database.sh"
bash -n "${STAGE}/05b-prepare-visit-db-baseline.sh"

FILES=(
    "sql/task003/visit-mapping-baseline.sql"
    "scripts/task003/05b-inspect-visit-database.sh"
    "scripts/task003/05b-prepare-visit-db-baseline.sh"
)

# Check every destination before installing any file.
for rel in "${FILES[@]}"; do
    target="${ROOT}/${rel}"
    if [[ -L "${target}" ]]; then
        echo "ERROR: refusing symlink: ${rel}"
        exit 1
    fi
    if [[ -e "${target}" ]] &&
       ! cmp -s "${STAGE}/${rel##*/}" "${target}"
    then
        echo "ERROR: existing source differs: ${rel}"
        exit 1
    fi
done

for rel in "${FILES[@]}"; do
    target="${ROOT}/${rel}"
    mkdir -p -- "$(dirname "${target}")"
    mode=644
    [[ "${rel}" != *.sh ]] || mode=755
    install -m "${mode}" "${STAGE}/${rel##*/}" "${target}"
    echo "SOURCE_READY=${rel}"
done

echo "STEP05B_SOURCE_INSTALL=PASS"
echo "DATABASE_WRITE=NO"
echo "S3_WRITE=NO"

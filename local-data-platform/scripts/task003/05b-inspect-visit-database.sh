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

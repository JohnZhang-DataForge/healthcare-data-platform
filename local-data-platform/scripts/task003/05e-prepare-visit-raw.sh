#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

echo '#### TASK003 STEP05E SOURCE INSTALL OUTPUT BEGIN ####'
STAGE=''
finish() {
    rc=$?
    trap - EXIT
    if [[ -n "${STAGE}" ]]; then rm -rf -- "${STAGE}"; fi
    echo "INSTALL_EXIT_CODE=${rc}"
    echo '#### TASK003 STEP05E SOURCE INSTALL OUTPUT END ####'
    exit "${rc}"
}
trap finish EXIT

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
for rel in \
    apps/task003/resolve_approved_encounter_raw.py \
    apps/task003/verify_encounter_remote_metadata.py \
    spark/common/canonical_gate.py \
    spark/contracts/canonical/encounter-v1.json \
    spark/contracts/omop/visit-class-v1.json \
    spark/manifests/task002/person-omop-map.yaml.tpl
do
    [[ -s "${ROOT}/${rel}" ]] || {
        echo "ERROR: missing dependency: ${rel}"
        exit 1
    }
done
STAGE="$(mktemp -d)"

cat > "${STAGE}/validate_encounter_raw_for_visit.py" <<'PY_APP'
"""Read-only Spark validation of approved Encounter Raw and Person references."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from pyspark.sql import SparkSession, functions as F
from canonical_gate import validate_contract, validate_metadata, validate_unique_key
from verify_encounter_remote_metadata import verify_metadata


def main():
    directory = Path(__file__).resolve().parent
    context = json.loads((directory / 'input-context.json').read_bytes())
    contracts = {}
    for filename, key in (
        ('encounter-v1.json', 'canonical_contract_sha256'),
        ('visit-class-v1.json', 'mapping_contract_sha256'),
    ):
        data = (directory / filename).read_bytes()
        if hashlib.sha256(data).hexdigest() != context[key]:
            raise ValueError('Mounted contract SHA mismatch: ' + filename)
        contracts[filename] = json.loads(data)

    spark = SparkSession.builder.appName('visit-raw-preflight').config(
        'spark.sql.session.timeZone', 'UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')

    try:
        def remote_bytes(uri):
            rows = spark.read.format('binaryFile').load(
                uri.replace('s3://', 's3a://', 1)
            ).select('content').collect()
            if len(rows) != 1:
                raise ValueError('Expected exactly one remote metadata object')
            return bytes(rows[0]['content'])

        mb = remote_bytes(context['raw_manifest_uri'])
        db = remote_bytes(context['dq_uri'])
        verify_metadata(context, mb, db)
        manifest = json.loads(mb)

        raw = spark.read.parquet(
            context['raw_data_uri'].replace('s3://', 's3a://', 1)
        ).cache()
        contract = contracts['encounter-v1.json']
        mapping = contracts['visit-class-v1.json']

        validate_contract(raw, contract)
        keys = validate_unique_key(raw, contract['primary_key'])
        if keys['rows'] != context['expected_rows']:
            raise ValueError('Raw row count differs from pinned manifest')

        metadata = dict(
            source_system=context['source'],
            source_version=context['source_version'],
            source_batch_id=context['batch_id'],
            source_ingest_date=context['ingest_date'],
            processing_run_id=context['processing_run_id'],
            source_file=manifest['source_file'],
            source_file_sha256=manifest['source_file_sha256'],
            source_file_size_bytes=manifest['source_file_size_bytes'],
            adapter_name='synthea_encounter_adapter',
            adapter_version='v1',
            canonical_version='v1',
        )
        validate_metadata(raw, metadata)

        for name in ('source_encounter_id', 'source_person_id', 'encounter_class'):
            if raw.filter(F.length(F.trim(F.col(name))) == 0).limit(1).count():
                raise ValueError('Blank required key/class: ' + name)

        if raw.filter(F.length(F.col('source_encounter_id')) > 255).limit(1).count():
            raise ValueError('Encounter key exceeds stable map column length')

        if raw.filter(
            F.col('end_datetime') < F.col('start_datetime')
        ).limit(1).count():
            raise ValueError('Encounter end precedes start')

        counts = {
            r['encounter_class']: r['count']
            for r in raw.groupBy('encounter_class').count().collect()
        }
        if set(counts) - set(mapping['class_to_visit_concept']):
            raise ValueError('Unmapped encounter class')

        if os.environ['PGDATABASE'] != 'omop':
            raise ValueError('Unexpected PostgreSQL database')

        def query(sql):
            return (
                spark.read.format('jdbc')
                .option(
                    'url',
                    'jdbc:postgresql://' + os.environ['PGHOST'] + ':'
                    + os.environ['PGPORT'] + '/' + os.environ['PGDATABASE'],
                )
                .option('user', os.environ['PGUSER'])
                .option('password', os.environ['PGPASSWORD'])
                .option('driver', 'org.postgresql.Driver')
                .option(
                    'sessionInitStatement',
                    'SET default_transaction_read_only = on',
                )
                .option('dbtable', '(' + sql + ') preflight')
                .load()
            )

        persons = query("""
            SELECT m.source_system, m.source_person_id, m.person_id,
                   p.person_id AS cdm_person_id
            FROM etl.person_id_map m
            LEFT JOIN cdm.person p ON p.person_id = m.person_id
            WHERE m.source_system = 'synthea'
        """).cache()

        joined = raw.join(
            persons, ['source_system', 'source_person_id'], 'left'
        ).cache()

        if joined.count() != keys['rows']:
            raise ValueError('Person join inflated Encounter rows')

        if joined.filter(
            F.col('person_id').isNull()
            | F.col('cdm_person_id').isNull()
            | (F.col('person_id') <= 0)
        ).limit(1).count():
            raise ValueError('Encounter lacks valid Person map/CDM reference')

        used_people = joined.select('person_id').distinct().count()
        domains = {
            v['concept_id']: 'Visit'
            for v in mapping['class_to_visit_concept'].values()
        }
        domains[mapping['visit_type_concept_id']] = 'Type Concept'
        if any(type(k) is not int or k <= 0 for k in domains):
            raise ValueError('Invalid mapped concept IDs')

        concepts = query(
            'SELECT concept_id, domain_id, standard_concept, invalid_reason, '
            'valid_start_date, valid_end_date FROM cdm.concept WHERE concept_id IN ('
            + ','.join(map(str, sorted(domains))) + ')'
        ).collect()

        if {r['concept_id'] for r in concepts} != set(domains):
            raise ValueError('Missing mapped concepts')

        for r in concepts:
            if (
                r['domain_id'] != domains[r['concept_id']]
                or r['standard_concept'] != 'S'
                or r['invalid_reason'] is not None
                or not (
                    r['valid_start_date']
                    <= datetime.now(timezone.utc).date()
                    <= r['valid_end_date']
                )
            ):
                raise ValueError('Invalid mapped concept: ' + str(r['concept_id']))

        # Recheck metadata pins before emitting successful validation evidence.
        verify_metadata(
            context,
            remote_bytes(context['raw_manifest_uri']),
            remote_bytes(context['dq_uri']),
        )
        result = dict(
            status='PASS',
            raw_rows=keys['rows'],
            raw_unique_keys=keys['unique_keys'],
            referenced_persons=used_people,
            encounter_classes=counts,
            raw_publish_run_id=context['raw_publish_run_id'],
            raw_manifest_sha256=context['raw_manifest_sha256'],
            dq_sha256=context['dq_sha256'],
            canonical_contract_sha256=context['canonical_contract_sha256'],
            mapping_contract_sha256=context['mapping_contract_sha256'],
            raw_schema='PASS',
            raw_metadata='PASS',
            person_references='PASS',
            concepts='PASS',
            postgresql_write=False,
            s3_write=False,
        )
        print(
            'VISIT_RAW_PREFLIGHT_RESULT=' + json.dumps(result, sort_keys=True),
            flush=True,
        )
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
PY_APP

cat > "${STAGE}/05e-validate-visit-raw.sh" <<'SH_RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

echo '#### TASK003 STEP05E SPARK RAW PREFLIGHT OUTPUT BEGIN ####'
trap 'rc=$?; echo "PREFLIGHT_EXIT_CODE=${rc}"; echo "#### TASK003 STEP05E SPARK RAW PREFLIGHT OUTPUT END ####"; exit "${rc}"' EXIT

[[ $# -eq 1 ]] || {
    echo "Usage: $0 STEP05D_RUN_STATE"
    exit 2
}
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT="$(mktemp -d "${ROOT}/runtime/reports/task003/step05/raw-preflight.XXXXXX")"
NAME="visit-raw-check-$(date -u +%Y%m%dt%H%M%Sz)-$$"
CM="${NAME}-app"

echo "PREFLIGHT_REPORT=${REPORT}"
echo "SPARK_APPLICATION=${NAME}"

PYTHONPATH="${ROOT}/apps/task003" \
python3 - "${ROOT}" "$1" "${REPORT}" "${NAME}" "${CM}" <<'PY'
import json, sys
from pathlib import Path
from resolve_approved_encounter_raw import resolve, require
from verify_encounter_remote_metadata import verify_metadata

root, statefile, report = map(Path, sys.argv[1:4])
name, cm = sys.argv[4:]
state = json.loads(statefile.read_bytes())

for key, value in dict(
    task='TASK-003', step='STEP-05D', status='PASS',
    validation_scope='remote_manifest_and_dq_bytes',
    remote_metadata_verified=True,
).items():
    require(state.get(key), value, key)

context = state['input_context']
require(
    context, resolve(root, context['raw_publish_run_id']),
    'fresh local evidence',
)
verify_metadata(
    context,
    (statefile.parent / 'manifest.remote.json').read_bytes(),
    (statefile.parent / 'dq.remote.json').read_bytes(),
)
(report / 'input-step05d.json').write_bytes(statefile.read_bytes())
(report / 'input-context.json').write_text(
    json.dumps(context, indent=2) + '\n'
)

template = (
    root / 'spark/manifests/task003/visit-raw-preflight.yaml.tpl'
).read_text()
for old, value in (('__APP_NAME__', name), ('__CONFIGMAP_NAME__', cm)):
    if template.count(old) != 1:
        raise ValueError('Unexpected template placeholder: ' + old)
    template = template.replace(old, value)
if '__' in template:
    raise ValueError('Unresolved template placeholder')
(report / 'sparkapplication.yaml').write_text(template)
print('PINNED_INPUT_CONTEXT=PASS')
PY

kubectl get secret dw-spark-s3-secret dw-spark-omop-secret \
    -n dw-spark >/dev/null
kubectl get serviceaccount spark-job -n dw-spark >/dev/null
kubectl apply --dry-run=client \
    -f "${REPORT}/sparkapplication.yaml" >/dev/null

kubectl create configmap "${CM}" -n dw-spark \
    --from-file="${ROOT}/spark/apps/visit/validate_encounter_raw_for_visit.py" \
    --from-file="${ROOT}/spark/common/canonical_gate.py" \
    --from-file="${ROOT}/apps/task003/verify_encounter_remote_metadata.py" \
    --from-file="${ROOT}/apps/task003/resolve_approved_encounter_raw.py" \
    --from-file="${ROOT}/spark/contracts/canonical/encounter-v1.json" \
    --from-file="${ROOT}/spark/contracts/omop/visit-class-v1.json" \
    --from-file="${REPORT}/input-context.json"

kubectl create -f "${REPORT}/sparkapplication.yaml"

FINAL_STATE=''
for ((attempt=0; attempt<180; attempt++)); do
    FINAL_STATE="$(kubectl get sparkapplication "${NAME}" -n dw-spark \
        -o jsonpath='{.status.applicationState.state}' 2>/dev/null || true)"
    case "${FINAL_STATE}" in
        COMPLETED|FAILED|FAILING|SUBMISSION_FAILED|UNKNOWN) break ;;
    esac
    sleep 5
done

echo "FINAL_STATE=${FINAL_STATE}"
kubectl logs -n dw-spark "${NAME}-driver" \
    > "${REPORT}/driver.log" 2>&1 || true

if [[ "${FINAL_STATE}" != COMPLETED ]]; then
    tail -160 "${REPORT}/driver.log"
    kubectl get sparkapplication "${NAME}" -n dw-spark -o yaml \
        > "${REPORT}/application-status.yaml" || true
    echo 'ERROR: Spark preflight did not complete'
    exit 1
fi

python3 - "${REPORT}" "${NAME}" "${CM}" <<'PY'
import json, sys
from pathlib import Path

report = Path(sys.argv[1])
prefix = 'VISIT_RAW_PREFLIGHT_RESULT='
lines = [
    line[len(prefix):]
    for line in (report / 'driver.log').read_text().splitlines()
    if line.startswith(prefix)
]
if len(lines) != 1:
    raise SystemExit('ERROR: missing or ambiguous Spark validation result')
r = json.loads(lines[0])
c = json.loads((report / 'input-context.json').read_text())

for key in (
    'raw_publish_run_id', 'raw_manifest_sha256', 'dq_sha256',
    'canonical_contract_sha256', 'mapping_contract_sha256',
):
    if r[key] != c[key]:
        raise SystemExit('ERROR: Spark result context mismatch: ' + key)

if (
    r['raw_rows'] != c['expected_rows']
    or r['raw_unique_keys'] != c['expected_rows']
):
    raise SystemExit('ERROR: Spark result row/key mismatch')

for key in ('status', 'raw_schema', 'raw_metadata', 'person_references', 'concepts'):
    if r.get(key) != 'PASS':
        raise SystemExit('ERROR: Spark check failed: ' + key)

if r.get('postgresql_write') is not False or r.get('s3_write') is not False:
    raise SystemExit('ERROR: unexpected write status')

state = dict(
    task='TASK-003', step='STEP-05E', status='PASS',
    spark_application=sys.argv[2], configmap=sys.argv[3],
    validation_scope='raw_parquet_and_person_references',
    raw_parquet_verified=True, input_context=c, result=r,
    ids_allocated=0, postgresql_write=False, s3_write=False,
)
(report / 'run-state.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(r, indent=2))
print('REMOTE_PARQUET_REVALIDATION=PASS')
print('PERSON_REFERENCES=PASS')
print('VISIT_MAPPING_CONCEPTS=PASS')
PY

echo "RUN_STATE=${REPORT}/run-state.json"
echo 'IDS_ALLOCATED=0'
echo 'DATABASE_WRITE=NO'
echo 'S3_WRITE=NO'
SH_RUNNER

python3 - "${ROOT}" "${STAGE}" <<'PY_TEMPLATE'
import ast, re, sys
from pathlib import Path

root, stage = map(Path, sys.argv[1:])
t = (root / 'spark/manifests/task002/person-omop-map.yaml.tpl').read_text()

for old, new in (
    ('healthcare-task: task002', 'healthcare-task: task003'),
    ('healthcare-domain: person', 'healthcare-domain: visit'),
    ('healthcare-step: omop-map', 'healthcare-step: raw-preflight'),
    ('map_canonical_patient_to_omop.py', 'validate_encounter_raw_for_visit.py'),
):
    if t.count(old) != 1:
        raise SystemExit('ERROR: unexpected base template: ' + old)
    t = t.replace(old, new)

t, count = re.subn(
    r'^  arguments:\n.*?(?=^  sparkVersion:)',
    '', t, flags=re.M | re.S,
)
if count != 1 or set(re.findall(r'__[A-Z_]+__', t)) != {
    '__APP_NAME__', '__CONFIGMAP_NAME__',
}:
    raise SystemExit('ERROR: unexpected generated template')

(stage / 'visit-raw-preflight.yaml.tpl').write_text(t)
ast.parse((stage / 'validate_encounter_raw_for_visit.py').read_text())
print('SPARK_SOURCE_SYNTAX=PASS')
PY_TEMPLATE

cp -- "${BASH_SOURCE[0]}" "${STAGE}/05e-prepare-visit-raw.sh"
bash -n "${STAGE}/05e-validate-visit-raw.sh"
bash -n "${STAGE}/05e-prepare-visit-raw.sh"

FILES=(
    spark/apps/visit/validate_encounter_raw_for_visit.py
    spark/manifests/task003/visit-raw-preflight.yaml.tpl
    scripts/task003/05e-validate-visit-raw.sh
    scripts/task003/05e-prepare-visit-raw.sh
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
    install -m "${mode}" "${STAGE}/${rel##*/}" "${ROOT}/${rel}"
    echo "SOURCE_READY=${rel}"
done

echo 'STEP05E_SOURCE_INSTALL=PASS'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'DATABASE_WRITE=NO'
echo 'S3_WRITE=NO'

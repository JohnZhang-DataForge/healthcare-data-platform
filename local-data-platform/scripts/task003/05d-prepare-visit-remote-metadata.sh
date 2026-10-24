#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

echo '#### TASK003 STEP05D SOURCE INSTALL OUTPUT BEGIN ####'
STAGE=''
finish() {
    rc=$?
    trap - EXIT
    if [[ -n "${STAGE}" ]]; then rm -rf -- "${STAGE}"; fi
    echo "INSTALL_EXIT_CODE=${rc}"
    echo '#### TASK003 STEP05D SOURCE INSTALL OUTPUT END ####'
    exit "${rc}"
}
trap finish EXIT

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
[[ -s "${ROOT}/apps/task003/resolve_approved_encounter_raw.py" ]] || {
    echo 'ERROR: STEP05A resolver missing'
    exit 1
}
STAGE="$(mktemp -d)"

cat > "${STAGE}/verify_encounter_remote_metadata.py" <<'PY_APP'
#!/usr/bin/env python3
"""Verify remote Encounter manifest/DQ bytes; does not verify Parquet contents."""
import argparse
import hashlib
import json
from pathlib import Path
from resolve_approved_encounter_raw import require, resolve


def verify_metadata(context, manifest_bytes, dq_bytes):
    for data, key in (
        (manifest_bytes, 'raw_manifest_sha256'),
        (dq_bytes, 'dq_sha256'),
    ):
        require(hashlib.sha256(data).hexdigest(), context[key], key)

    manifest, dq = json.loads(manifest_bytes), json.loads(dq_bytes)
    require(manifest.get('status'), 'APPROVED', 'manifest status')
    require(dq.get('status'), 'PASS', 'DQ status')

    for doc in (manifest, dq):
        for key in (
            'source', 'source_version', 'batch_id', 'ingest_date',
            'processing_run_id', 'raw_publish_run_id',
        ):
            require(doc.get(key), context[key], key)
        require(doc.get('entity'), 'encounter', 'entity')
        require(doc.get('canonical_version'), 'v1', 'canonical version')
        for key in ('expected_rows', 'raw_rows', 'raw_unique_keys'):
            require(doc.get(key), context['expected_rows'], key)

    require(manifest.get('data'), dict(
        uri=context['raw_data_uri'],
        format='parquet',
        row_count=context['expected_rows'],
        primary_key=['source_system', 'source_encounter_id'],
        unique_primary_keys=context['expected_rows'],
    ), 'manifest data')

    require(manifest.get('dq'), dict(
        status='PASS',
        uri=context['dq_uri'],
        sha256=context['dq_sha256'],
        readback_sha256='PASS',
    ), 'manifest DQ link')

    checks = (
        'canonical_schema canonical_required_fields canonical_metadata '
        'canonical_primary_key raw_write raw_readback'
    ).split()
    require(dq.get('checks'), {key: 'PASS' for key in checks}, 'DQ checks')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'verify'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--context', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()

    raw = args.context.read_bytes()
    context = json.loads(raw)
    fresh = resolve(args.root, context['raw_publish_run_id'])
    require(context, fresh, 'pinned STEP05A context vs current local evidence')

    saved = args.report / 'input-context.json'
    if args.phase == 'prepare':
        saved.write_bytes(raw)
        plan = '\n'.join([
            context['raw_manifest_uri'] + '\tmanifest.remote.json',
            context['dq_uri'] + '\tdq.remote.json',
        ]) + '\n'
        (args.report / 'download-plan.tsv').write_text(plan)
        print('PINNED_LOCAL_INPUT_REVALIDATED=PASS')
        return

    require(saved.read_bytes(), raw, 'input context unchanged during download')
    verify_metadata(
        context,
        (args.report / 'manifest.remote.json').read_bytes(),
        (args.report / 'dq.remote.json').read_bytes(),
    )

    state = dict(
        task='TASK-003',
        step='STEP-05D',
        status='PASS',
        validation_scope='remote_manifest_and_dq_bytes',
        input_context=context,
        input_context_sha256=hashlib.sha256(raw).hexdigest(),
        remote_metadata_verified=True,
        remote_parquet_verified=False,
        postgresql_write=False,
        s3_write=False,
    )
    (args.report / 'run-state.json').write_text(
        json.dumps(state, indent=2) + '\n'
    )
    print('REMOTE_MANIFEST_SHA256=PASS')
    print('REMOTE_DQ_SHA256=PASS')
    print('REMOTE_METADATA_LINEAGE=PASS')
    print('REMOTE_METADATA_REVALIDATION=PASS')
    print('MANIFEST_DECLARED_ROWS=' + str(context['expected_rows']))
    print('RAW_PUBLISH_RUN_ID=' + context['raw_publish_run_id'])
    print('REMOTE_PARQUET_REVALIDATION=PENDING')


if __name__ == '__main__':
    main()
PY_APP

cat > "${STAGE}/test_encounter_remote_metadata.py" <<'PY_TEST'
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'apps/task003'))
from verify_encounter_remote_metadata import verify_metadata


class RemoteMetadataTests(unittest.TestCase):
    def setUp(self):
        self.context = dict(
            source='synthea', source_version='v3.3.0',
            batch_id='test', ingest_date='2026-10-08',
            processing_run_id='processing-test',
            raw_publish_run_id='raw-test', expected_rows=3,
            raw_data_uri='s3://health-raw/test/data/',
            dq_uri='s3://health-raw/test/dq/result.json',
        )
        common = {k: self.context[k] for k in (
            'source', 'source_version', 'batch_id', 'ingest_date',
            'processing_run_id', 'raw_publish_run_id',
        )}
        common.update(
            entity='encounter', canonical_version='v1',
            expected_rows=3, raw_rows=3, raw_unique_keys=3,
        )
        checks = (
            'canonical_schema canonical_required_fields canonical_metadata '
            'canonical_primary_key raw_write raw_readback'
        ).split()
        self.dq = dict(
            common, status='PASS', checks={k: 'PASS' for k in checks}
        )
        self.manifest = dict(common, status='APPROVED', data=dict(
            uri=self.context['raw_data_uri'], format='parquet', row_count=3,
            primary_key=['source_system', 'source_encounter_id'],
            unique_primary_keys=3,
        ))
        self.seal()

    def seal(self):
        self.db = json.dumps(self.dq).encode()
        self.context['dq_sha256'] = hashlib.sha256(self.db).hexdigest()
        self.manifest['dq'] = dict(
            status='PASS', uri=self.context['dq_uri'],
            sha256=self.context['dq_sha256'], readback_sha256='PASS',
        )
        self.mb = json.dumps(self.manifest).encode()
        self.context['raw_manifest_sha256'] = hashlib.sha256(self.mb).hexdigest()

    def test_valid_metadata(self):
        verify_metadata(self.context, self.mb, self.db)

    def test_tampered_download(self):
        with self.assertRaises(ValueError):
            verify_metadata(self.context, self.mb + b' ', self.db)
        with self.assertRaises(ValueError):
            verify_metadata(self.context, self.mb, self.db + b' ')

    def test_reject_semantic_changes_even_with_matching_hashes(self):
        for doc, key, value in (
            ('manifest', 'status', 'DRAFT'),
            ('manifest', 'raw_publish_run_id', 'other-run'),
            ('manifest', 'raw_rows', True),
            ('dq', 'status', 'FAIL'),
        ):
            with self.subTest(doc=doc, key=key):
                self.setUp()
                getattr(self, doc)[key] = value
                self.seal()
                with self.assertRaises(ValueError):
                    verify_metadata(self.context, self.mb, self.db)


if __name__ == '__main__':
    unittest.main()
PY_TEST

cat > "${STAGE}/visit-raw-metadata-reader.yaml.tpl" <<'YAML_POD'
apiVersion: v1
kind: Pod
metadata:
  name: __POD_NAME__
  namespace: dw-spark
  labels:
    healthcare-task: task003
    healthcare-purpose: visit-raw-metadata-reader
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  activeDeadlineSeconds: 600
  containers:
    - name: aws
      image: amazon/aws-cli:2.15.57
      imagePullPolicy: IfNotPresent
      command: ["/bin/sh", "-c", "sleep 600"]
      envFrom:
        - secretRef:
            name: dw-spark-s3-secret
YAML_POD

cat > "${STAGE}/05d-verify-visit-remote-metadata.sh" <<'SH_RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

echo '#### TASK003 STEP05D REMOTE METADATA OUTPUT BEGIN ####'
POD=''
finish() {
    rc=$?
    trap - EXIT
    if [[ -n "${POD}" ]]; then
        if kubectl delete pod "${POD}" -n dw-spark \
            --ignore-not-found --wait=false \
            > "${REPORT}/pod-cleanup.log" 2>&1
        then
            echo 'UTILITY_POD_DELETE_REQUESTED=YES'
        else
            echo "WARNING: cleanup failed; inspect ${REPORT}/pod-cleanup.log"
        fi
    fi
    echo "VERIFY_EXIT_CODE=${rc}"
    echo '#### TASK003 STEP05D REMOTE METADATA OUTPUT END ####'
    exit "${rc}"
}
trap finish EXIT

[[ $# -eq 1 ]] || {
    echo "Usage: $0 STEP05A_INPUT_CONTEXT"
    exit 2
}
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP="${ROOT}/apps/task003/verify_encounter_remote_metadata.py"
TEMPLATE="${ROOT}/spark/manifests/task003/visit-raw-metadata-reader.yaml.tpl"

mkdir -p "${ROOT}/runtime/reports/task003/step05"
REPORT="$(mktemp -d "${ROOT}/runtime/reports/task003/step05/remote-metadata.XXXXXX")"
echo "VERIFY_REPORT=${REPORT}"

python3 "${APP}" prepare \
    --root "${ROOT}" --context "$1" --report "${REPORT}"

kubectl get secret dw-spark-s3-secret -n dw-spark >/dev/null

POD="visit-raw-meta-$(date -u +%Y%m%dt%H%M%Sz)-$$"
sed "s/__POD_NAME__/${POD}/g" "${TEMPLATE}" \
    > "${REPORT}/utility-pod.yaml"

kubectl create -f "${REPORT}/utility-pod.yaml"
kubectl wait --for=condition=Ready \
    "pod/${POD}" -n dw-spark --timeout=180s

while IFS=$'\t' read -r uri filename; do
    kubectl exec -n dw-spark "${POD}" -- \
        aws --no-cli-pager \
        --endpoint-url http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333 \
        s3 cp "${uri}" - --only-show-errors \
        > "${REPORT}/${filename}" \
        2> "${REPORT}/${filename}.stderr.log" || {
            cat "${REPORT}/${filename}.stderr.log"
            exit 1
        }
    echo "REMOTE_DOWNLOADED=${filename}"
done < "${REPORT}/download-plan.tsv"

python3 "${APP}" verify \
    --root "${ROOT}" --context "$1" --report "${REPORT}"

echo "RUN_STATE=${REPORT}/run-state.json"
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
SH_RUNNER

cp -- "${BASH_SOURCE[0]}" \
    "${STAGE}/05d-prepare-visit-remote-metadata.sh"

bash -n "${STAGE}/05d-verify-visit-remote-metadata.sh"
bash -n "${STAGE}/05d-prepare-visit-remote-metadata.sh"

PYTHONPATH="${STAGE}:${ROOT}/apps/task003" \
    python3 "${STAGE}/test_encounter_remote_metadata.py"
echo 'REMOTE_METADATA_TESTS=PASS'

FILES=(
    apps/task003/verify_encounter_remote_metadata.py
    tests/task003/test_encounter_remote_metadata.py
    spark/manifests/task003/visit-raw-metadata-reader.yaml.tpl
    scripts/task003/05d-verify-visit-remote-metadata.sh
    scripts/task003/05d-prepare-visit-remote-metadata.sh
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

echo 'STEP05D_SOURCE_INSTALL=PASS'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'

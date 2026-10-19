#!/usr/bin/env bash
set -Eeuo pipefail
# Read-only, fail-closed audit: no create/patch/delete/apply/exec/cp.
: "${KUBE_CONTEXT:?Set KUBE_CONTEXT to the explicitly approved read-only context}"
: "${AIRFLOW_NAMESPACE:?Set AIRFLOW_NAMESPACE}"
: "${SPARK_NAMESPACE:?Set SPARK_NAMESPACE}"
: "${SPARK_CONFIGMAP:?Set SPARK_CONFIGMAP to the exact rendered Spark ConfigMap name}"
: "${EXPECTED_SPARK_FILE:?Set EXPECTED_SPARK_FILE to the expected Git source path}"
: "${REPORT_DIR:?Set REPORT_DIR (outside tracked source)}"
[[ -f "${EXPECTED_SPARK_FILE}" ]] || { echo "EXPECTED_SPARK_FILE_MISSING"; exit 2; }
mkdir -p "${REPORT_DIR}"
umask 077
echo "#### LOCAL_DP_PROVENANCE_OUTPUT_BEGIN ####"
echo "KUBE_CONTEXT=${KUBE_CONTEXT}"
echo "GIT_HEAD=$(git rev-parse HEAD)"
echo "EXPECTED_SPARK_SOURCE_SHA256=$(sha256sum "${EXPECTED_SPARK_FILE}" | cut -d' ' -f1)"
kubectl --context "${KUBE_CONTEXT}" -n "${AIRFLOW_NAMESPACE}" get pods -o json > "${REPORT_DIR}/airflow-pods.json"
kubectl --context "${KUBE_CONTEXT}" -n "${SPARK_NAMESPACE}" get configmap "${SPARK_CONFIGMAP}" -o json > "${REPORT_DIR}/spark-configmap.json"
python3 - "${REPORT_DIR}" "${EXPECTED_SPARK_FILE}" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
expected = pathlib.Path(sys.argv[2])
pods = json.loads((root/'airflow-pods.json').read_text())
cm = json.loads((root/'spark-configmap.json').read_text())
print('AIRFLOW_POD_COUNT=' + str(len(pods.get('items',[]))))
for pod in pods.get('items',[]):
    spec = pod.get('spec',{})
    name = pod.get('metadata',{}).get('name','')
    for c in spec.get('initContainers',[]) + spec.get('containers',[]):
        print('POD_CONTAINER=' + name + '/' + c.get('name',''))
        for mount in c.get('volumeMounts',[]):
            if 'dag' in mount.get('mountPath','').lower():
                print('DAG_MOUNT=' + name + ':' + mount.get('mountPath',''))
        for env in c.get('env',[]):
            if any(k in env.get('name','').upper() for k in ('GIT_SYNC','DAGS_FOLDER')):
                print('CONFIG_ENV_KEY=' + env.get('name',''))
data = cm.get('data',{})
name = expected.name
if name not in data:
    raise SystemExit('SPARK_CONFIGMAP_SOURCE_NOT_FOUND=' + name)
actual = hashlib.sha256(data[name].encode()).hexdigest()
wanted = hashlib.sha256(expected.read_bytes()).hexdigest()
print('SPARK_CONFIGMAP_KEY=' + name)
print('SPARK_CONFIGMAP_SHA256=' + actual)
print('EXPECTED_GIT_SOURCE_SHA256=' + wanted)
print('SPARK_CONTENT_MATCH=' + ('PASS' if actual == wanted else 'FAIL'))
if actual != wanted: raise SystemExit(3)
print('GITSYNC_ACTIVE_CHECKOUT=NOT_VERIFIED')
print('LIVE_POD_IMPORT_PATH=NOT_VERIFIED')
PY
echo "#### LOCAL_DP_PROVENANCE_OUTPUT_END ####"

#!/usr/bin/env bash
# Route A Marquez deployment on dedicated PG14. Run only on trusted dw-runner-set.
# Explicit scope: dw-marquez namespace and dedicated PostgreSQL14 read-only baseline.
# Never touch dw-postgre/OMOP/Airflow/Synthea. Do not print secrets.
set -Eeuo pipefail
umask 077
NAMESPACE=dw-marquez
RELEASE=marquez
VALUES=kubernetes/marquez/values-pg14.yaml
CHART_VERSION=0.51.1
REPORT_DIR="$RUNNER_TEMP/marquez-install"
mkdir -p "$REPORT_DIR"
echo "MARQUEZ_RELEASE_VERSION=$CHART_VERSION"
echo "TARGET_NAMESPACE=$NAMESPACE"
echo "SOURCE_POSTGRES_NAMESPACE=dw-postgre14"

for x in kubectl helm curl python3 base64; do
  command -v "$x" >/dev/null || { echo "REQUIRED_TOOL_MISSING=$x"; exit 1; }
done
test -f "$VALUES"
test "$(kubectl get pod dw-postgre14-database-0 -n dw-postgre14 -o jsonpath='{.status.phase}')" = Running
test "$(kubectl get pvc dw-postgre14-data -n dw-postgre14 -o jsonpath='{.status.phase}')" = Bound
test "$(kubectl get svc dw-postgre14 -n dw-postgre14 -o jsonpath='{.spec.type}')" = ClusterIP
test "$(kubectl get secret postgres-secret -n dw-postgre14 -o jsonpath='{.type}')" = Opaque

# No environment secret data, no unrestricted echo or shell xtrace.
kubectl exec -n dw-postgre14 dw-postgre14-database-0 -- sh -c \
  'psql -X -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT current_database()||chr(124)||current_user||chr(124)||current_setting('\''server_version_num'\'');"' \
  > "$REPORT_DIR/db-before.txt"
test "$(cat "$REPORT_DIR/db-before.txt")" = "marquez|marquez|140024"
echo PG14_ISOLATED_DATABASE_PREFLIGHT=PASS

kubectl get svc -A -o json | python3 -c \
  'import sys,json; a=json.load(sys.stdin)["items"]; v=[x for x in a if any(p.get("nodePort")==30999 for p in x.get("spec",{}).get("ports",[]))]; assert not v or all(x["metadata"]["namespace"]=="dw-marquez" and x["metadata"]["name"]=="marquez-web-lan" for x in v), "NODEPORT_30999_CONFLICT"; print("MARQUEZ_30999_PORT_GATE=PASS")'
kubectl get nodes -o json | python3 -c \
  'import sys,json; a=json.load(sys.stdin)["items"]; ext=[(n["metadata"]["name"],v["address"]) for n in a for v in n.get("status",{}).get("addresses",[]) if v.get("type")=="ExternalIP"];assert not ext,"EXTERNAL_NODE_IP_REQUIRES_FIREWALL_REVIEW";print("MARQUEZ_NODE_EXTERNALIP_GATE=PASS")'

if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  kubectl create namespace "$NAMESPACE"
fi
if ! kubectl get secret marquez-db -n "$NAMESPACE" >/dev/null 2>&1; then
  # Copy precisely the existing Secret key through stdin INSIDE the runner.
  # No password is written to the repository, a YAML file or the job log.
  kubectl get secret postgres-secret -n dw-postgre14 -o jsonpath='{.data.POSTGRES_PASSWORD}' |
    base64 -d |
    kubectl create secret generic marquez-db -n "$NAMESPACE" --from-file=marquez-db-password=/dev/stdin >/dev/null
  echo MARQUEZ_DB_SECRET_CREATED=YES
else
  echo MARQUEZ_DB_SECRET_CREATED=ALREADY_EXISTS
fi
test "$(kubectl get secret marquez-db -n "$NAMESPACE" -o jsonpath='{.data.marquez-db-password}' | wc -c)" -gt 0
echo MARQUEZ_DB_SECRET_PRESENT=PASS

helm repo add marquez https://marquezproject.github.io/marquez --force-update >/dev/null
helm repo update marquez >/dev/null
helm show chart marquez/marquez --version "$CHART_VERSION" > "$REPORT_DIR/chart.yaml"
grep -q '^name: marquez$' "$REPORT_DIR/chart.yaml"
echo MARQUEZ_CHART_PIN=PASS

# Confirm both chart services are internal before mutating anything.
helm template "$RELEASE" marquez/marquez --version "$CHART_VERSION" \
  --namespace "$NAMESPACE" -f "$VALUES" > "$REPORT_DIR/rendered.yaml"
python3 - "$REPORT_DIR/rendered.yaml" <<'PY'
import sys
from pathlib import Path
txt=Path(sys.argv[1]).read_text()
assert 'kind: Deployment' in txt and 'kind: Service' in txt
assert 'dw-postgre14.dw-postgre14.svc.cluster.local' in txt
assert 'type: ClusterIP' in txt
assert 'kind: StatefulSet' not in txt
assert 'image: postgres:' not in txt
assert 'nodePort: 30999' not in txt
assert 'marquez-db' in txt
print('MARQUEZ_HELM_RENDER_NO_BUNDLED_DB_NO_NODEPORT=PASS')
PY

helm upgrade --install "$RELEASE" marquez/marquez \
  --namespace "$NAMESPACE" --version "$CHART_VERSION" \
  -f "$VALUES" --wait --timeout 9m \
  --history-max 5
echo MARQUEZ_HELM_RELEASE_APPLIED=YES
kubectl rollout status deployment/marquez -n "$NAMESPACE" --timeout=180s
kubectl rollout status deployment/marquez-web -n "$NAMESPACE" --timeout=180s
test "$(kubectl get svc marquez -n "$NAMESPACE" -o jsonpath='{.spec.type}')" = ClusterIP
test "$(kubectl get svc marquez-web -n "$NAMESPACE" -o jsonpath='{.spec.type}')" = ClusterIP
echo MARQUEZ_API_WEB_ROLLOUT=PASS

# Verify first migration actually created schema in the dedicated database.
kubectl exec -n dw-postgre14 dw-postgre14-database-0 -- sh -c \
  'psql -X -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='\''public'\'';"' \
  > "$REPORT_DIR/table-count.txt"
python3 - "$REPORT_DIR/table-count.txt" <<'PY'
from pathlib import Path
import sys
n=int(Path(sys.argv[1]).read_text().strip())
assert n>3,"MARQUEZ_METADATA_SCHEMA_MISSING"
print('MARQUEZ_SCHEMA_TABLE_COUNT='+str(n))
print('MARQUEZ_SCHEMA_MIGRATION=PASS')
PY

# Helm sets BOTH upstream services to ClusterIP. Expose ONLY the web selector
# through a separate K8s NodePort after DB + API + Web are Healthy.
kubectl get svc marquez-web -n "$NAMESPACE" -o json |
  python3 -c '
import sys,json
s=json.load(sys.stdin)
selector=s["spec"]["selector"]
assert selector.get("app.kubernetes.io/component")=="web", "BAD_WEB_SELECTOR"
assert all("api" not in str(k).lower() for k in selector), "UNEXPECTED_WEB_SELECTOR"
payload={
  "apiVersion":"v1","kind":"Service",
  "metadata":{"name":"marquez-web-lan","namespace":"dw-marquez",
              "labels":{"app.kubernetes.io/part-of":"marquez"}},
  "spec":{"type":"NodePort","selector":selector,
          "ports":[{"name":"http","protocol":"TCP","port":80,"targetPort":"http","nodePort":30999}]}
print(json.dumps(payload))
' | kubectl apply -f -
test "$(kubectl get svc marquez-web-lan -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}')" = 30999
test "$(kubectl get svc marquez -n "$NAMESPACE" -o jsonpath='{.spec.type}')" = ClusterIP
echo MARQUEZ_WEB_NODEPORT_30999=PASS

# Verify the Service endpoints match ready web pods; this does not prove WAN NAT.
kubectl get endpointslice -n "$NAMESPACE" -l kubernetes.io/service-name=marquez-web-lan -o json |
  python3 -c 'import json,sys; x=json.load(sys.stdin)["items"]; assert x and any(e.get("conditions",{}).get("ready") is True for s in x for e in s.get("endpoints",[])), "WEB_NODEPORT_NO_READY_ENDPOINTS";print("MARQUEZ_WEB_NODEPORT_ENDPOINTS=PASS")'
kubectl get pods,svc -n "$NAMESPACE" -o wide | cut -c1-180
echo MARQUEZ_PG14_API_WEB_DEPLOYMENT=PASS
echo OMOP_AIRFLOW_SYNTHEA_MUTATION=NO
echo NODEPORT_EXTERNAL_NAT_STATUS=NOT_VERIFIED

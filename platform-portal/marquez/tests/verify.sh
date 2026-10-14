#!/usr/bin/env bash
# Metadata-only live acceptance; no seed dataset and no database mutation.
set -Eeuo pipefail
NAMESPACE=dw-marquez
kubectl rollout status deployment/marquez -n "$NAMESPACE" --timeout=180s
kubectl rollout status deployment/marquez-web -n "$NAMESPACE" --timeout=180s
test "$(kubectl get svc marquez -n "$NAMESPACE" -o jsonpath='{.spec.type}')" = ClusterIP
test "$(kubectl get svc marquez-web -n "$NAMESPACE" -o jsonpath='{.spec.type}')" = ClusterIP
echo PORTAL_API_WEB_DEPLOYMENT_READY=PASS
kubectl exec -n dw-postgre14 dw-postgre14-database-0 -- sh -c 'psql -X -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='\''public'\'';"' | grep -E '^[1-9][0-9]*$'
echo PORTAL_PG14_TABLES_PRESENT=PASS
# Port forwards are temporary processes on the trusted Runner; no WAN exposure.
kubectl port-forward -n "$NAMESPACE" service/marquez-web 19199:80 >/dev/null 2>&1 &
p=$!
trap 'kill "$p" 2>/dev/null || true' EXIT
for n in $(seq 1 30); do
  if curl --max-time 2 -fsS http://127.0.0.1:19199/healthcheck > /dev/null; then break; fi
  sleep 1
done
test "$(curl --max-time 8 -fsS http://127.0.0.1:19199/healthcheck)" = OK
echo PORTAL_WEB_HTTP_HEALTH=PASS
code="$(curl --max-time 15 -s -o /dev/null -w '%{http_code}' http://127.0.0.1:19199/api/v1/namespaces)"
test "$code" = 200
echo PORTAL_WEB_API_PROXY_HTTP_200=PASS

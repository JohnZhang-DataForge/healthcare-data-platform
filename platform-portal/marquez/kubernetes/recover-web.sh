#!/usr/bin/env bash
# Complete ONLY the Web LAN Service and HTTP gates for an already Ready Marquez release.
# Does not run helm upgrade, DB migrations, or modify postgres/OMOP.
set -Eeuo pipefail
NAMESPACE=dw-marquez
NODENAME=marquez-web-lan
test "$(kubectl get pod dw-postgre14-database-0 -n dw-postgre14 -o jsonpath='{.status.phase}')" = Running
test "$(kubectl get pvc dw-postgre14-data -n dw-postgre14 -o jsonpath='{.status.phase}')" = Bound
kubectl rollout status deployment/marquez -n "$NAMESPACE" --timeout=180s
kubectl rollout status deployment/marquez-web -n "$NAMESPACE" --timeout=180s
test "$(kubectl get svc marquez -n "$NAMESPACE" -o jsonpath='{.spec.type}')" = ClusterIP
test "$(kubectl get svc marquez-web -n "$NAMESPACE" -o jsonpath='{.spec.type}')" = ClusterIP
echo PORTAL_MARQUEZ_EXISTING_API_WEB_READY=PASS
kubectl exec -n dw-postgre14 dw-postgre14-database-0 -- sh -c 'psql -X -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='\''public'\'';"' |
  python3 -c 'import sys; n=int(sys.stdin.read().strip()); assert n>=30, "MARQUEZ_METADATA_TABLES_MISSING";print("PORTAL_MARQUEZ_METADATA_TABLES="+str(n))'
kubectl get svc -A -o json |
  python3 -c 'import sys,json; a=json.load(sys.stdin)["items"]; xs=[s for s in a if any(p.get("nodePort")==30999 for p in s.get("spec",{}).get("ports",[]))]; assert not xs or all(s["metadata"]["namespace"]=="dw-marquez" and s["metadata"]["name"]=="marquez-web-lan" for s in xs),"NODEPORT_COLLISION";print("PORTAL_NODEPORT_COLLISION_GATE=PASS")'
kubectl get nodes -o json |
  python3 -c 'import sys,json; a=json.load(sys.stdin)["items"]; x=[n for n in a for v in n.get("status",{}).get("addresses",[]) if v.get("type")=="ExternalIP"]; assert not x,"NODE_EXTERNAL_IP_NEEDS_ACCESS_REVIEW";print("PORTAL_EXTERNAL_NODE_IP_COUNT=0")'
kubectl get svc marquez-web -n "$NAMESPACE" -o json |
  python3 -c 'import sys,json; s=json.load(sys.stdin); expected={"app.kubernetes.io/component":"web","app.kubernetes.io/instance":"marquez","app.kubernetes.io/name":"marquez"}; assert s["spec"]["selector"]==expected,"WEB_SELECTOR_DRIFT"; print("PORTAL_WEB_SELECTOR_GATE=PASS")'
kubectl apply -f platform-portal/marquez/kubernetes/web-nodeport.yaml
test "$(kubectl get svc "$NODENAME" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}')" = 30999
test "$(kubectl get svc marquez -n "$NAMESPACE" -o jsonpath='{.spec.type}')" = ClusterIP
kubectl get endpointslice -n "$NAMESPACE" -l kubernetes.io/service-name="$NODENAME" -o json |
  python3 -c 'import sys,json; a=json.load(sys.stdin)["items"]; assert any(e.get("conditions",{}).get("ready")==True for s in a for e in s.get("endpoints",[])), "NO_READY_WEB_SERVICE_ENDPOINT"; print("PORTAL_WEB_NODEPORT_ENDPOINTS=PASS")'
bash platform-portal/marquez/tests/verify.sh
echo PORTAL_WEB_NODEPORT_30999_AND_API_HTTP=PASS
echo OMOP_POSTGRES17_AND_TASK004_MUTATION=NO
echo INTERNET_NAT_REACHABILITY=NOT_VERIFIED

# Public read-only Marquez Web

Source of the public UI overlay and dedicated image, derived from official Marquez Web 0.51.1 (Apache-2.0, digest pinned). Original private LAN Web is unchanged. No local tunnel, gateway configuration, credentials, network addresses or real metadata are stored here.

The public variant hides Delete Job/Dataset, Edit Tag, Tag Submit/deletion, Tag editing input and raw Events navigation (currently denied by Gateway). Dashboard, Jobs, Datasets, Run History, Table/Column Lineage, filters, refresh, zoom and navigation stay available.

**UI hiding is not authorization.** A visitor can bypass browser JavaScript. Gateway must still reject all writing methods and unapproved endpoints and sensitive GET content must be reviewed.

Test: node --test platform-portal/portal/web/tests/*.test.cjs

Build: docker build -t healthcare-portal-public-web:test platform-portal/portal/web

CI builds on PR without publishing; Main push/dispatch publishes ghcr.io/johnzhang-dataforge/healthcare-portal-public-web:sha-<commit>.

Deploy this independently to a new Web Service with MARQUEZ_HOST, MARQUEZ_PORT and WEB_PORT configured privately. Gateway must be intentionally switched from existing Marquez Web to the new service after approved tests. Publishing the image does NOT deploy it and does NOT touch the original LAN NodePort.

Upstream: https://github.com/MarquezProject/marquez/tree/0.51.1/web

## Isolated LAN trial (no Cloudflare switch)

Kubernetes source: [kubernetes/lan.yaml](kubernetes/lan.yaml). It creates only three named resources in `dw-marquez`: `Deployment/marquez-public-web`, `Service/marquez-public-web` (ClusterIP) and `Service/marquez-public-web-lan` (NodePort **31080**). Selectors use the separate label `app.kubernetes.io/name=marquez-public-web`, distinct from the Helm original `marquez-web` and LAN NodePort 30999.

Upstream API is the existing cluster-local Marquez port 80; this Deployment does not run an API, connect to PG14 directly or change original API/Web/Cloudflare Gateway/Secret. The image is pinned to the verified GHCR manifest digest. No Helm upgrade, existing Service patch, Cloudflare change or business data operation is part of this rollout.

After an authorized preflight, run the pinned manifest with `kubectl apply -f platform-portal/portal/web/kubernetes/lan.yaml` on the trusted runner, check rollout and independent Service endpoints. LAN-only address is `http://<existing-private-k8s-node-address>:31080/` after verifying local firewall/NAT. The test must include `/healthcheck`, GET `/api/v1/namespaces`, Table/Column Lineage, Run History, original 30999 unchanged and Gateway upstream unchanged. A new NodePort may still be reachable outside LAN if separate router/firewall rules exist; do not equate absent Kubernetes ExternalIP with firewall proof.

**Revert without touching original Web/PG:** remove only these three resources after specific authorization, or leave them isolated if validation fails. Do not remove original 30999, the Gateway or the Tunnel. This test does not imply public cutover.

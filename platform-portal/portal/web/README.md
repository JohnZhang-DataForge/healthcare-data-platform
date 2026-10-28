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

## Public Datasets presentation (Marquez 0.51.1)

Only when a visitor enters `/datasets` without a previously saved Namespace selection, the public overlay selects `s3://health-processing` through the original MUI/Redux dropdown. Explicitly selected namespaces remain authoritative, and no automatic selection runs on the Jobs route.

For a table of fully parseable **Landing or Processing** dataset IDs, the public columns become **Dataset, Batch, Ingest Date, Updated At, Quality, Column Lineage**. Processing Dataset cells show `entity=patient/encounter` and exact `run_id`. Landing Dataset cells display the *real filenames* `manifest.json`, `encounters.csv`, or `patients.csv` as readable file types, with a File subtitle (Landing has no processing `run_id`); the batch cell shortens the known `synthea-new-only-gh-` prefix without changing identifiers. The original Dataset hyperlink and exact full path are retained. Different run IDs remain distinguishable.

Marquez **Namespace** groups datasets while Marquez **Source** describes registered origin. They can have identical values (`s3://health-processing`) in our real metadata but are not equivalent concepts. The public list eliminates the redundant visible columns only for this known schema. Tooltips separately retain the original Namespace, original Marquez Source, and the actual Producer parsed from `source=synthea`. Other namespaces or paths without required identity fields fall back to the native Marquez table.

Implementation: `public-datasets.js` and `public-datasets.css`, injected after the existing read-only controls but before the pinned upstream bundle. This is client-side display logic, not a security boundary or database/data lineage rename. Run `node --test platform-portal/portal/web/tests/*.test.cjs`; real MUI dropdown/browser E2E and a distinct immutable image digest require subsequent LAN verification. Source-only PRs do not deploy to 31080 and do not change the Cloudflare Gateway.

### Public Landing verification (2026-10-28 UTC)

GET-only audit of the existing public Marquez API [Self-Runner #40768910661](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40768910661) returned exactly 12 Landing datasets: **four batches** with **three filenames per batch** (`manifest.json`, `encounters.csv`, `patients.csv`). All 12 carried `source`, `source_version`, `ingest_date`, `batch_id`; none had `entity` or `run_id` nor a `columnLineage` mapping. Processing had eight records, with `entity` and `run_id` and actual column lineage. The public UI presenter now uses these verified distinct schemas. Landing `N/A` Column Lineage remains accurate; use Processing to inspect field mapping. Other unrecognized files/IDs remain in the original Marquez representation. Public API inspection was GET-only; no patient values or raw file contents were fetched.

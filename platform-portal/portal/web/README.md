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

Opening the public site root `/` navigates in the browser to `/datasets` and selects the real `s3://health-landing` Namespace, including a visitor who previously selected Processing. A one-shot same-tab session marker is consumed after the Landing dropdown choice; the visitor can then manually select `s3://health-processing` without being switched back. A direct `/datasets` or `/datasets/` visit without a prior section choice defaults to Landing; a direct bookmark with a previously chosen useful `s3://health-processing` still respects that selection. Jobs, dataset/column-level lineage deep links, and other routes do not redirect. Root query parameters such as UTM are preserved. This is an overlay browser navigation, **not an HTTP 3xx at the Gateway**, and does not change any dataset identity or API.


### Section-specific nonempty namespace defaults (Jobs / Datasets)

The stock Marquez 0.51.1 namespace selector stores a **single global** `selectedNamespace`. This caused first-time visitors to see an empty Jobs page after arriving at the default Landing Datasets. Live GET-only [Self-Runner #41960755696](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41960755696) confirmed `s3://health-landing` has Datasets but no Jobs, while `healthcare-platform-airflow` has real Jobs (including `new_only_omop_consumer`); `healthcare-platform-spark-business` is another nonempty Jobs fallback.

The public-only overlay now chooses **Jobs → `healthcare-platform-airflow`** (if that option is unavailable, use `healthcare-platform-spark-business`); **Datasets → `s3://health-landing`** unless the visitor explicitly chose Processing. It stores namespace preferences independently for Jobs and Datasets in browser-tab `sessionStorage` and uses the native MUI selector rather than patching Redux. A visitor manually switching to Spark Business Jobs or Processing Datasets is respected on return; direct Jobs after prior Landing global selection gets a useful Jobs view. The overlay does not inject fake data or edit real namespace identifiers and is inactive on individual Job/Dataset/Lineage detail routes.

The section-independent default is a **frontend convenience**, not an OpenLineage collector or a backend authorization mechanism. Existing GET-only Gateway policy remains authoritative. Regressions must test `/jobs`, `/jobs/`, `/datasets`, `/datasets/`, root, manual toggles and deep links. Public browser/retained cache acceptance is a separate live gate from a successful Node unit test and pinned GHCR rollout.

**Deployed public Web image (2026-11-04 US Eastern)**: Healthcare [PR #684](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/684) Main `413695e9`, [GHCR build #41961798047](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41961798047) new image digest `sha256:a58d9550a16c97535ed24cdfdcabb3668ad94adb7c01e9d892abd206663260c0`; [Self-Runner image-only rollout #41962002716](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41962002716) SUCCESS. The live Public Web/Gateway GET readback proved the new overlay is served and the Airflow Jobs/Landing Datasets APIs each have real content; Gateway write rejection remained intact. Real browser tab-switch interaction and cache acceptance are still pending.


For a table of fully parseable **Landing or Processing** dataset IDs, the public columns become **Dataset, Batch, Ingest Date, Updated At, Quality, Column Lineage**. Processing Dataset cells show `entity=patient/encounter` and exact `run_id`. Landing Dataset cells display the *real filenames* `manifest.json`, `encounters.csv`, or `patients.csv` as readable file types, with a File subtitle (Landing has no processing `run_id`); the batch cell shortens the known `synthea-new-only-gh-` prefix without changing identifiers. The original Dataset hyperlink and exact full path are retained. Different run IDs remain distinguishable.

Marquez **Namespace** groups datasets while Marquez **Source** describes registered origin. They can have identical values (`s3://health-processing`) in our real metadata but are not equivalent concepts. The public list eliminates the redundant visible columns only for this known schema. Tooltips separately retain the original Namespace, original Marquez Source, and the actual Producer parsed from `source=synthea`. Other namespaces or paths without required identity fields fall back to the native Marquez table.

Implementation: `public-datasets.js` and `public-datasets.css`, injected after the existing read-only controls but before the pinned upstream bundle. This is client-side display logic, not a security boundary or database/data lineage rename. Run `node --test platform-portal/portal/web/tests/*.test.cjs`; real MUI dropdown/browser E2E and a distinct immutable image digest require subsequent LAN verification. Source-only PRs do not deploy to 31080 and do not change the Cloudflare Gateway.

### Public Landing verification (2026-10-28 UTC)

GET-only audit of the existing public Marquez API [Self-Runner #40768910661](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40768910661) returned exactly 12 Landing datasets: **four batches** with **three filenames per batch** (`manifest.json`, `encounters.csv`, `patients.csv`). All 12 carried `source`, `source_version`, `ingest_date`, `batch_id`; none had `entity` or `run_id` nor a `columnLineage` mapping. Processing had eight records, with `entity` and `run_id` and actual column lineage. The public UI presenter now uses these verified distinct schemas. Landing `N/A` Column Lineage remains accurate; use Processing to inspect field mapping. Other unrecognized files/IDs remain in the original Marquez representation. Public API inspection was GET-only; no patient values or raw file contents were fetched.

### Browser cache on public frontend overlays

A production Chrome screenshot (2026-10-28) showed the original NAME/NAMESPACE/SOURCE for both Landing and Processing even though a fresh browser passed the visual test. GET-only public browser diagnostic [Self-Runner #40776772416](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40776772416) reproduced the exact screenshot URL including `?utm_source=chatgpt.com`, confirmed the **upstream server caches `/public-datasets.js` for 14,400 seconds (4 hours)** while HTML has `max-age=0`. A brand-new browser receives the correct overlay and can maintain it for 16+ seconds through Namespace switches and reload; existing browsers may re-use an older same-URL script across GHCR image releases.

The image installer now fingerprints all four custom public overlay JS/CSS URLs by their SHA-256 content (first 20 hex characters), e.g. `/public-datasets.js?v=<content-hash>`. The new index.html references a different URL for every changed asset; native upstream `bundle.js` is untouched. The upstream static caching policy may remain 4 hours because the browser cache key is now version-specific. The Main index HTML must continue to revalidate and the public Gateway must pass query parameters for these static resources. Release acceptance must include real Chrome and the screenshot URL, verify fingerprinted script URL, compare JavaScript SHA, and test both Landing/Processing with persisted namespace selections. Browser pass in a clean profile alone is insufficient.

---
status: active
scope: local-atlas3-webapi3-source-map
last_verified: 2026-11-10
---

# ATLAS3 / WebAPI3 — CODE and ownership map

This source map owns **the new OHDSI ATLAS research consumer only**. It does not own Local OMOP Writer, the existing PostgreSQL17 StatefulSet/PVC, Marquez deployments, or the Cloudflare public ingress.

| Maintained source | Purpose / safety |
| --- | --- |
| [Namespace](../../../../local-data-platform/kubernetes/manifests/atlas/namespace.yaml) | `dw-atlas`; add only after a live collision check |
| [Services](../../../../local-data-platform/kubernetes/manifests/atlas/services.yaml) | ATLAS3 and WebAPI3 ClusterIP only |
| [ATLAS3 UI Deployment](../../../../local-data-platform/kubernetes/manifests/atlas/atlas3-ui-deployment.yaml.tpl) | immutable image placeholder, mandatory worker03 placement, bounded resources |
| [WebAPI3 Deployment](../../../../local-data-platform/kubernetes/manifests/atlas/webapi3-deployment.yaml.tpl) | immutable WebAPI image placeholder, PG17 ClusterIP hostname placeholder, secret refs, startup gates |
| [Internal UI gateway](../../../../local-data-platform/kubernetes/manifests/atlas/frontend-gateway-configmap.yaml) | private Caddy path routing; not the shared Marquez Nginx Gateway |
| [WebAPI3 NetworkPolicy](../../../../local-data-platform/kubernetes/manifests/atlas/webapi3-networkpolicy.yaml) | Restrict ingress to Atlas3 UI pods only |
| [Atlas3 UI Dockerfile](../../../../local-data-platform/images/atlas3-ui/Dockerfile) | builds only pinned upstream OHDSI/Atlas3 v3.0.0 SHA, not a floating branch |
| [Application schema SQL](../../../../local-data-platform/atlas/sql/prepare-webapi-schemas.sql) | transactional **authorized-only** WebAPI / Results / Temp preparation; **never execute directly during source validation** |
| [Runtime contract](../../../../local-data-platform/atlas/config/runtime-contract.json) | pinned version/digest and actual 2026-11-10 deploy/Source/Concept readback status |
| [Source guard tests](../../../../.github/quality/tests/data-platform/atlas/test_atlas_p2p4_static.py) | path, worker03 and existing SQL ownership scope, actual deployment contract |
| [LOCAL_OMOP Source definition](../../../../local-data-platform/atlas/config/local-omop-source.json) | WebAPI3 Source key + v3 ordinal CDM/Vocabulary/Results/Temp Daimons; **no credentials in Git** |
| [Authenticated Source registration](../../../../local-data-platform/atlas/config/register_local_omop_source.py) | WebAPI3 `POST /WebAPI/source` one-time, read-only PG17 source drift checks, idempotent no-replay, independent SQL/HTTP Vocabulary verification |
| [Source compatibility tests](../../../../.github/quality/tests/data-platform/atlas/test_atlas_source_registration_static.py) | v3 REST JSON fields, isolated Source config and security guarantees |
| [Atlas image build CI](../../../../.github/workflows/atlas3-ui-image-build.yml) | PR: build/inspect only; Main: immutable GHCR publication |
| [Static tests CI](../../../../.github/workflows/atlas-p2p4-static.yml) | no Kubernetes/PG/Cloudflare mutation |
| [ACHILLES one-shot Job](../../../../local-data-platform/kubernetes/manifests/atlas/achilles-local-omop-once-job.yaml) | official image digest pinned after actual Docker Hub lookup; generates real OMOP Data Sources summaries in atlas_results only; manual launch, no CDM write |
| [ACHILLES job contract tests](../../../../.github/quality/tests/data-platform/atlas/test_atlas_achilles_job_contract.py) | immutable digest, secret refs, dedicated result schema, resource caps and no auto-deploy |

## Actual runtime / acceptance as of 2026-11-10

- **Deployment already completed; do not run initial schema SQL or repeat K8s rollout.** [Self-Runner #42840709079](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42840709079) validates ATLAS3+WebAPI3 on worker03, immutable images, internal same-origin proxy, HTTPS `/atlas/` and `/WebAPI/info`, anonymous sensitive API 401. User confirmed browser login with `atlas_admin`.
- **PG17 accurate local audit**: [Self-Runner #42897172846](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42897172846) verifies 39 CDM tables, 432 columns, Person 1,394, Visit 200,556, Observation Period **0**, Concept 1,952,609, Concept Relationship 13,150,960, Concept Ancestor 10,958,071, other vocabulary rows; 87 WebAPI application tables. These are PG17 counts, not Fabric counts.
- **Source registration accepted**: [initial native POST #42899903741](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42899903741) yielded HTTP 200 and `webapi.source` ID **1**, `LOCAL_OMOP`, four Daimons (CDM=0/`cdm`, Vocabulary=1/`cdm`, Results=2/`atlas_results`, Temp=5/`atlas_temp`). That run's final status was failed only because subsequent concept check expected wrong JSON field names. [Full readback #42901169254](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42901169254) was PASS: existing Source matched and was NOT recreated, SQL Daimon and API Source/priority readback PASS, Concept GET HTTP200 with PG17 `CONCEPT_ID` match, and SQL-backed `POST /vocabulary/LOCAL_OMOP/search` HTTP200, two Gender matches.
- **WebAPI 3.0 compatibility**: `SourceRequest` requires `krbAuthMethod=default` even for PostgreSQL due to upstream converter null handling. `ConceptSearch` uses uppercase `QUERY`, `VOCABULARY_ID`, `IS_LEXICAL` JSON keys, and Concept response keys including `CONCEPT_ID` are uppercase. Do not change these to camelCase. Upstream GET `/vocabulary/LOCAL_OMOP/search?query=Male` uses a separate SearchProvider/indexed path and was observed to timeout; **do not claim indexed GET or full UI search performance is complete** based on SQL-backed POST success.
- **Security and data**: initial Source uses existing dedicated `atlas_webapi` DB role, which is `SELECT` only on `cdm.*` and writable only within ATLAS app/Results/Temp schemas. Separate future CDM-only reader role remains a hardening option, not a verified fact. Credentials/JWT are read only from existing Kubernetes Secrets at runtime. The `cdm` business rows are never migrated by ATLAS.
- **Open**: `cdm.observation_period=0`, `cdm.cdm_source=0`, `atlas_results` has no tables yet. Do not claim Concept Set → Cohort Generation/Results physical readback. Application/Results backup and source query/index tuning remain open.
- **Public boundary**: `runtime-contract.public_route_enabled=false` means this repository does not manage or activate an external Cloudflare route; `public_route_verified=true` records the separate, already active route's independent HTTP proof. `atlas.johnzhang-dataforge.site` uses existing `healthcare-marquez-public` Tunnel and private ATLAS ClusterIP services; user chose **no Cloudflare Access application**, so WebAPI native DB authentication + RBAC guards sensitive APIs. Do not alter Marquez Nginx or create a parallel Tunnel.

[Active OpenSpec](../../../../openspec/changes/deploy-local-ohdsi-atlas/tasks.md) · [Local DP catalog](../README.md).

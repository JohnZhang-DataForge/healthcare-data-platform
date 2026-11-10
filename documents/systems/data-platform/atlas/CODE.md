---
status: active
scope: local-atlas3-webapi3-source-map
last_verified: 2026-11-09
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
| [Runtime contract](../../../../local-data-platform/atlas/config/runtime-contract.json) | version/source/worker/namespace and unexecuted status |
| [Source guard tests](../../../../.github/quality/tests/data-platform/atlas/test_atlas_p2p4_static.py) | path, private exposure, worker and SQL scope |
| [Atlas image build CI](../../../../.github/workflows/atlas3-ui-image-build.yml) | PR: build/inspect only; Main: immutable GHCR publication |
| [Static tests CI](../../../../.github/workflows/atlas-p2p4-static.yml) | no Kubernetes/PG/Cloudflare mutation |

## Runtime caveats

- **Not a deployment receipt.** Manifest templates contain unresolved image-digest and PG-service parameters and MUST NOT be directly applied.
- Existing Kubernetes roles/Secrets for `atlas_webapi` and `atlas_migrator` are not created by static tests. Runtime setup must make them mutually consistent and provide secret references without printing passwords.
- Existing PG17 data and its PV stay in `dw-postgre`. The P2–P4 one-pass operation must refuse to migrate until verified database recoverability, independent PG17 real-state readback, and safe operation locks are satisfied.
- The real 2026-11-09 EST GET-only [Self-Runner readiness Run #42756234158](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42756234158) confirmed PG17 17.11, 39 CDM tables, existing local vocabulary estimates, worker03 readiness and no `dw-atlas` Namespace. It did not prove PG17 backup, accurate counts, or runtime installation.
- Client WebAPI authentication and future Cloudflare Access are independent. Public hostname activation is **not** part of P2–P4.

[Active OpenSpec](../../../../openspec/changes/deploy-local-ohdsi-atlas/tasks.md) · [Local DP catalog](../README.md).

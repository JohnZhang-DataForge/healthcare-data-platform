# Design — Fabric component ownership and safe path migration

## Final logical ownership

| Responsibility | Canonical owner |
| --- | --- |
| Fabric native item definitions and executable native Notebook body | `azure-fabric/workspaces/healthcare-omop/<item>.<type>/` (Fabric Git item format unchanged) |
| Versioned deployable SQL schemas/metadata and platform integration configuration | `azure-fabric/deployment/warehouse/`, `deployment/openlineage/`, other `deployment/<component>/` as needed |
| Deployment orchestration/verification adapters owned by Healthcare | `azure-fabric/deployment/<component>/*.py` (future code, not copied from private Self-Runner) |
| Warehouse OMOP Writer / identity planner | `azure-fabric/warehouse/omop-foundation/writer/` |
| OpenLineage event Publisher/integration logic | `azure-fabric/openlineage/publisher.py` |
| Terraform infra | `azure-fabric/infra-terraform/` |
| Generic FHIR/OMOP transformation Python | `shared-data-engine/src/healthcare_data_engine/` |
| CI trigger / offline tests / docs | `.github/workflows/`, `.github/quality/tests/`, `documents/` |

`deployment/common/` is reserved for code truly shared across deploy adapters; no premature second Fabric client/authentication stack. A tracked owner registry must define all seven component paths, so absent empty Git directories are intentional.

## Exact candidate physical moves (do not execute in this planning PR)

1. `azure-fabric/warehouse/omop-cdm-5.4/**` → `azure-fabric/deployment/warehouse/omop-cdm-5.4/**` (manifest + upstream source + 39 table SQL; retain source-pinned OHDSI blob and 39/432 fidelity).
2. `azure-fabric/warehouse/omop-foundation/{manifest.json,identity-key-v1.json,sql/**}` → `azure-fabric/deployment/warehouse/omop-foundation/` (same exact five empty management-table schema files).
3. `azure-fabric/openlineage/compatibility.py` → `azure-fabric/deployment/openlineage/compatibility.py` (offline Listener configuration only).
4. **No move** for `azure-fabric/warehouse/omop-foundation/writer/*.py`, `azure-fabric/openlineage/publisher.py`, Fabric Native items or Wheel.

These are candidate destinations pending dependency inventory; do not treat any source move as a new Fabric resource, cloud deployment, or accepted runtime outcome.

## Dependency and migration order

- Phase 0: verify current main/open PRs; inventory source blob SHA and all consumer path references (Healthcare CI/imports, CODE/docs, active OpenSpec, Self-Runner current-main scripts and SHA-pinned historical workflows).
- Phase 1: establish owner registry, architecture spec and target-path positive/negative tests. Preserve trusted gate and frozen 185 historical-baseline bytes; an ordinary PR cannot mutate protected policy files. Report Required Check status honestly.
- Phase 2: modify current-main Self-Runner Warehouse deployment consumers to support **both old and new** source layout, add offline tests; merge runner compatibility before moving Healthcare SQL. Do not alter pinned historical checkout/ref to retroactively change evidence.
- Phase 3: move exact assets without changing content; update Healthcare imports, test discovery/paths, CI triggers, CODE maps, operational documentation and active contracts. Guard against re-creating retired paths. Verify the target Git blobs equal original blobs, test counts at least 2 CDM / 31 Foundation / 8 OpenLineage, and static path/link/OpenSpec checks. No live execution.
- Phase 4: remove obsolete current-main path fallback **only after** verified compatibility and independent audit; keep historical evidence and frozen paths inspectable by fixed SHA. Archive change and update adopted specs only when requirements are met.

## Rejection and hold gates

- If an unpinned Self-Runner consumer still requires an old path, do not remove that path. A temporary compatibility release may be required before the move.
- No code or script may call Azure/Fabric/SQL/Blob or trigger `Self-Runner` as part of a path-only acceptance test.
- If canonical URLs, OpenSpec and CODE references cannot be updated without breaking historical reproducibility, document exact immutable historical links separately and keep active links valid.
- Existing trusted policy files are protected. Expand a trusted check only through its approved governance procedure; a merely new CI workflow is not yet a Required Check.
- SQL DDL source content, Writer public APIs, OpenLineage event schema and native Notebook logicalId must remain unchanged.

## Rollback

Revert each bounded migration PR restoring exact previous Git paths and updating imports/workflows/docs in the same revert. Private Self-Runner compatibility support is additive and may remain during rollback. Runtime state is unchanged by design.

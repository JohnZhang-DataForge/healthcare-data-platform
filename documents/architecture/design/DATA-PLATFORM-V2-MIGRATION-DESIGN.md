---
status: draft
scope: data-platform-v2-repository-and-application-refactor
last_verified: 2026-10-17
source_sha: 664dfed06a206ff20822a118c8f04771a307452b
evidence: []
---

# Data Platform V2 — Repository Migration and Modular Rebuild Design

> **Status: DRAFT / PROPOSAL — not approved for implementation or deployment.** This document describes the desired end state and a migration approach, not a completed refactor. It does not supersede the [current system overview](../SYSTEM-OVERVIEW.md), [active component documentation](../../systems/data-platform/README.md), or [legacy migration rules](../../engineering/development/LEGACY-CODE-REFACTOR-PLAN.md).
>
> **Verification scope:** read-only repository inspection of Healthcare `main` at `664dfed06a206ff20822a118c8f04771a307452b` on 2026-10-17, plus previously recorded acceptance evidence. No live Kubernetes, Airflow, Spark, S3, PostgreSQL, GitHub Actions, or Azure execution was performed for this proposal.

## 1. Executive summary

Rebuild the maintained **local** data-processing system under `data-platform/` using component-first organization, reusable contracts, and a controlled transition from the accepted Person/Visit implementation. Do **not** blindly copy every legacy Task/Step implementation, and do **not** discard validated business behavior. This is a selective, incremental rebuild with old/new comparison and an explicit cutover.

The repository will have **four primary project directories**: `data-platform/`, `azure-fabric/`, `platform-portal/`, and `documents/`. Repository-level files and `.github/` remain at the root. The obsolete `azure/` source is a **retirement candidate** to remove only after verifying no unique active source, workflow, or Terraform-state dependency remains.

**Design goals:**
1. Preserve the already accepted independent Synthea NEW_ONLY → SeaweedFS S3 → Airflow → Spark Person/Visit → PostgreSQL OMOP behavior.
2. Replace new maintained `taskNNN/stepNNN` source names with component and capability names.
3. Extract proven common behavior for future Condition, Procedure, Drug, and other domains without a large speculative framework.
4. Separate repository source paths, platform working roots, container runtime paths, and durable data identifiers.
5. Keep Azure/Fabric analytics and Portal observability as independent sibling systems.
6. Ship through small, reversible, tested PRs rather than a single rewrite or uncontrolled live switch.

## 2. Scope and non-goals

**In scope:** local Synthea producer, landing/discovery/claim, Airflow orchestration, Spark canonical/domain logic, reconciliation, OMOP writer, their Contracts, SQL, image definitions, Kubernetes manifests, scripts, component tests, CODE maps, and their affected CI/Self-Runner integration. Include repository navigation/link changes and a guarded plan for retiring `azure/`.

**Out of scope for this migration:** introducing new business domains as delivered features; changing current S3/Azure landing semantics; creating or replacing Azure/Fabric resources; changing Portal deployment; migrating historical PostgreSQL data; running production-like batch replays; initializing OpenSpec; and renaming database schema objects purely for cosmetics.

Condition is a **design consumer** of the shared interfaces, not a claim that Condition is implemented. UPDATE_ONLY and MIX_DATA remain separate future work and must not be treated as equivalent to accepted NEW_ONLY behavior.

## 3. Target repository layout

```text
healthcare-data-platform/
├── .github/                          # Repository-level workflows and cross-system quality gates
├── .gitignore
├── AGENTS.md                         # Global agent entry
├── README.md                         # Project-level navigation
├── data-platform/                    # Local Kubernetes / S3 / Airflow / Spark / OMOP system
│   ├── airflow/
│   │   └── dags/
│   ├── apps/
│   │   ├── synthea/
│   │   ├── landing_discovery/
│   │   ├── landing_claim/
│   │   └── omop_writer/
│   ├── config/
│   ├── contracts/
│   ├── images/
│   ├── kubernetes/
│   ├── scripts/                      # Maintained component/capability operations
│   ├── spark/
│   │   ├── apps/
│   │   │   ├── person/
│   │   │   ├── visit/
│   │   │   └── condition/            # Future, not implemented by this proposal
│   │   └── common/
│   ├── sql/
│   └── tests/
├── azure-fabric/                     # Existing independent Azure/Fabric source
│   ├── infra-terraform/
│   └── workspaces/
├── platform-portal/                  # Existing OpenLineage / Marquez source
└── documents/                        # Project-wide documentation
    ├── architecture/
    │   ├── design/                   # Proposals, not approved ADRs
    │   └── decisions/                # Approved long-lived decisions
    ├── systems/
    └── engineering/
```

**Not a fifth project subsystem:** `.github/` and root-level agent/README files are GitHub/repository infrastructure, not application components. The location of global quality tooling (currently `scripts/quality/` and `tests/quality/`) needs one explicit decision: `.github/quality/` is a *candidate*, not an approved final path. These checks must continue to protect the entire repository, including Azure and Portal.

Keep `azure-fabric/` and `platform-portal/` at the root. Do not put them inside `data-platform/`. Maintain `documents/` as the single project documentation root, with architecture proposals separate from accepted decisions and component CODE maps.

## 4. Baseline: existing working system

The accepted local NEW_ONLY path has an independent Synthea producer, immutable manifest-backed S3 landing, a guarded/manual Airflow consumer, Spark Person and Visit processing, reconciliation, and an atomic, fenced PostgreSQL OMOP writer. Previously accepted new-batch commit and same-batch skip are historical facts for their original source and input versions, **not** acceptance of V2.

Key legacy source anchors (present in the inspected baseline; paths will change only after the corresponding PR):
- `airflow/dags/new_only_omop_consumer.py` and its routing/handoff helpers.
- `apps/synthea/new_only/`, `apps/landing_discovery/`, `apps/landing_claim/`, and `apps/omop_writer/`.
- `apps/task004/`, `spark/apps/task004/`, `airflow/dags/task004_cdm_*.py` and legacy `scripts/task004/`.
- `spark/apps/person/`, `spark/apps/visit/`, `spark/common/`, and their Contract/manifest sources.
- `images/new-only-omop-writer/Dockerfile`, `images/task004-runtime/Dockerfile`, and its source-generating `scripts/task004/06a-prepare-unified-runtime-image.sh`.
- `apps/task003/build_visit_processed_runtime_bundle.py`, `apps/task003/prepare_visit_processed_write_intent.py`, and `spark/apps/visit/run_visit_processed_writer.py`.

The [active legacy refactor plan](../../engineering/development/LEGACY-CODE-REFACTOR-PLAN.md) enumerates old task-named dependencies; use it for detailed preflight, not as a directive to bulk rename persistent interfaces.

## 5. Architectural boundaries and reusable capabilities

```text
Independent Synthea Producer
          |
   READY manifest + immutable batch identity
          v
S3 Landing <--> Discovery / Claim / Fencing
          |
          v
Airflow: select, route, authorize, observe (not transform/write rows)
          |
          v
Spark domain processing: Person | Visit | (future) Condition
          |         shared validation / canonical contracts / DQ
          v
Reconciliation and immutable writer handoff
          |
          v
OMOP Writer: transaction, ID mapping, staging, ledger, fencing
          |
          v
PostgreSQL OMOP (authoritative local data)
```

| Owner | Candidate reusable interface | Ownership boundary |
| --- | --- | --- |
| Synthea / Landing | Batch identity, immutable manifest, checksum verification, publication policy | Producer publishes; Consumer does not regenerate a batch |
| Landing / Claim | Discovery result, claim status, lease/fence verification | Discovery never silently authorizes OMOP commit |
| Airflow | Typed invocation arguments and route/branch decisions | Scheduling and orchestration only; no duplicated Spark or SQL business logic |
| Spark common | Canonical schema validation, deterministic source keys, DQ result, common Spark application parameters | Reuse proven primitives; domain adapters own clinical mapping |
| Spark domain | A small domain-specific adapter contract for Person/Visit and future domains | Domain owns source mapping, vocabulary and FK semantics |
| Reconciliation | Counts, identifiers, completeness, and persisted readback expectations | Results remain explicit gates, not just log strings |
| OMOP Writer | Batch fence, stage/write plan, transaction, stable ID map, atomic commit, idempotent replay decision | No Spark component directly commits to OMOP tables |
| Infrastructure | Image build, K8s submission, secrets references, health checks | Application logic remains independent of a particular shell step |

**Proposed interface vocabulary (design-level, not implemented):** `BatchIdentity`, `ManifestReference`, `ClaimDecision`, `CanonicalResult`, `DomainMappingResult`, `WriterHandoff`, `CommitResult`, and `ReconciliationResult`. Establish their exact fields and serialization from *existing* Contracts and verified behavior; do not invent new persisted schema versions or duplicate competing contract registries.

Domain development should require **mapping and domain rules**, not a copy of the entire Task004 pipeline. Prefer small explicit domain adapters over a generic reflection/plugin framework unless real reuse justifies added complexity.

## 6. Task004 naming and compatibility policy

**Rename maintainable source code by component/capability:** new files and migrated implementation locations under `apps/`, `spark/`, `images/`, `scripts/`, `sql/`, and `tests/` must follow the [component naming standard](../../engineering/development/CODE-ORGANIZATION-AND-NAMING.md). Reuse existing module owners when possible. A migration may temporarily expose an old-named thin adapter while consumers are transitioned.

**Do not mass-rename accepted runtime/persistence identifiers:**
- Keep the Airflow DAG ID `new_only_omop_consumer` stable through cutover.
- Preserve existing database APIs such as `etl.task004_batch_ledger`, `etl.task004_batch_stage`, `etl.task004_batch_commit`, and the writer fencing functions until a separately versioned database migration is approved.
- Preserve `batch_id`, immutable Manifest URI/SHA, checkpoint and ledger identities, stable OMOP IDs, previously written S3 object keys, and existing published image digests.
- Existing `/opt/task004/` paths and `task004_cdm_*.py` imports can be retained *inside a compatibility runtime image* during transition; renaming their source locations is not permission to change image internals.
- Historical Task/Step-named run evidence and scripts remain traceable in Git history; an archive policy should distinguish required recovery tooling from obsolete experiments.

**Important:** simply moving legacy files is seen by the current `check_new_code_names.py` diff mode (`--no-renames`) as new additions. The CI migration exception must be constrained to an audited old-path → new-path manifest with identical content/approved changes, not a blanket bypass of naming policy.

## 7. Path and packaging strategy

| Layer | Example | Rule |
| --- | --- | --- |
| Repository root | `healthcare-data-platform/` | Owns all four subsystems, docs and root CI |
| Local platform source root | `healthcare-data-platform/data-platform/` | `PLATFORM_ROOT` for source-side apps, tests, contracts and scripts |
| Image build context | repository root, e.g. `docker build -f data-platform/images/.../Dockerfile .` | Docker `COPY` references newly prefixed source paths; validate builder context |
| Container runtime paths | `/opt/task004/`, `/opt/spark/app/`, `/airflow/xcom/` | Do not rewrite solely because GitHub directories moved |
| Kubernetes/runtime workspace | current installed/mounted app paths | Change only with deployment-specific smoke and compatibility proof |
| Durable business references | `s3://...`, batch/manifest, Writer ledger, source fingerprint | Preserve semantics; any serialized path change requires contract/version review |

In new source-level code, prefer resolving `PLATFORM_ROOT` explicitly and then using relative paths such as `spark/apps/visit/...`. `Path(__file__).resolve().parents[2]` is context-dependent: it can still resolve to `data-platform/` after a whole-tree move but must be tested in both source checkouts and generated images. Do **not** globally replace every `spark/` or `apps/` string: some strings appear in approved policy artifacts, fingerprints, source maps, and historical evidence.

Specific hotspots to audit:
1. `apps/task003/build_visit_processed_runtime_bundle.py`: project-root discovery, Python `sys.path`, code bundle source lists.
2. `apps/task003/plan_visit_processed.py` and `apps/task003/prepare_visit_processed_write_intent.py`: file hashes and serialized source-relative names.
3. `spark/apps/visit/run_visit_processed_writer.py`: matching input source names, hash assertions, and runtime bundle entries.
4. `scripts/task004/05c-05f*.sh` and `images/task004-runtime/entrypoint.sh`: `PROJECT_ROOT` and Spark/YAML/script paths.
5. `scripts/task004/06a-prepare-unified-runtime-image.sh`: source generator must be updated with its generated Dockerfile and tests **together**.
6. All Dockerfiles: `COPY` paths and CI build contexts; preserve required destination paths.
7. Airflow GitSync subPath/DAG discovery, Self-Runner checkout/work directories, source-root-dependent GitHub Actions `paths` filters.
8. Component CODE.md links, Markdown link CI, repository-wide naming/ownership gates and unit-test fixture paths.

## 8. Recommended implementation: selective incremental rebuild

Avoid both extremes: (A) copying the whole tree unchanged then restructuring everything again and (B) implementing new code without comparing against accepted behavior. Adopt a **parallel-source, contract-compatible rebuild** with a single active writer at cutover.

| Phase | Deliverable | Exit criterion / evidence | Live mutation |
| --- | --- | --- | --- |
| P0 — Inventory & freeze | Path/dependency manifest, active/legacy/retire classification, root/file ownership, source SHA; legacy acceptance references | Every critical DAG, Docker image, shell generator, Contract, CODE map, Self-Runner Workflow and stateful identifier accounted for | None |
| P1 — Scaffold | New `data-platform/` package tree and global quality-tooling decision; minimal root navigation | Static path checks, quality gate behavior, import discovery; no current deployment replaced | None |
| P2 — Shared contracts | Extract/relocate Manifest, batch identity, common DQ/validation, claim decision and Writer handoff behind compatible interfaces | Positive/negative/replay tests against fixed legacy fixtures; unchanged serialized identity | None |
| P3 — Domain modules | Migrate Person and Visit adapters, Spark bundle builder, reconciliation and OMOP Writer composition; component naming | Old/new deterministic outputs match for frozen synthetic fixtures; no duplicate stage/commit | None |
| P4 — Packaging & CI | New Docker contexts, image builds, component CODE maps, Airflow DAG imports, all relevant Healthcare + Self-Runner paths | CI unit/contract/build gates green on exact candidate SHA; new image introspection and immutability checks | Build/package only |
| P5 — Controlled cutover | Single explicitly approved Airflow/Writer routing switch, a uniquely identified *new* test batch, independent S3/PG readback | New-batch E2E and safe same-batch skip; rollback route proven; no dual writer | **Requires separate authorization** |
| P6 — Retirement | Remove unused old source/Task shells and `azure/` only after usage/state/link audit | No stale navigation, imports, workflows or missing unique Terraform code; rollback evidence retained | Source deletion via reviewed PR only |

Each phase should be one or more bounded PRs; split heavy P2/P3/P4 changes by component. New code paths must come with owner `documents/systems/data-platform/<component>/CODE.md` updates in the same PR. Do not advertise P5 complete just because P1–P4 CI is green.

### P0 inventory classifications

For every legacy file classify **KEEP AS-IS**, **MOVE/ADAPT**, **EXTRACT SHARED**, **COMPATIBILITY WRAPPER**, **HISTORY ONLY**, or **RETIRE AFTER ACCEPTANCE**. Record: old path, proposed path, consumers, import/runtime/image dependencies, persisted identifiers, test coverage, and rollback dependency. Never assume every historical `scripts/taskNNN/` file belongs in V2.

### P2/P3 API-design checks

- Can Person and Visit call the same manifest/claim/handoff validators with their existing payloads?
- What logic is truly common, and which DQ or vocabulary rules must stay domain-specific?
- Is the source path inside a signed/hashed/serialized contract? If yes, plan a compatibility read path or explicitly version the contract.
- Are there old Python module names copied into immutable images? Preserve tested adapters until the image switch is approved.
- Can the existing Writer enforce one active claim, idempotency and atomicity for new domain modules without reimplementing guardrails?

## 9. Verification matrix and acceptance

| Gate | Minimum test / assertion |
| --- | --- |
| Source inventory | Old→new mapping covers all maintained consumers; no lost or duplicated function owners |
| Python and packages | Import smoke and unit/contract tests on exact PR SHA |
| Airflow | DagBag import and dependency graph; DAG IDs/schedules/paused safety expectations unchanged |
| Spark | Canonical Person/Visit schema, source key, row/DQ/reconciliation equivalence; wrong-schema negative cases |
| Writer | Duplicate batch skip, incompatible manifest rejection, role/fencing denial, stable ID/FK preservation, no unapproved writes |
| Images | All Docker `COPY` entries exist; generated and checked-in Dockerfile equivalence; test actual entrypoint in candidate image |
| CI / paths | `.github` workflows trigger for `data-platform/**`; quality scripts/tests still enforce naming, CODE maps and Markdown links |
| Self-Runner | Healthcare checkout, relative working-directory assumptions and reproducible script execution verified |
| Terraform | `azure-fabric/` continues independently; `azure/` deletion requires parity/state audit; no `apply` or `destroy` in migration validation |
| Approved runtime | Unique authorized test batch, S3 evidence, Airflow and Spark run evidence, independent PostgreSQL ledger/stage/CDM readback |
| Cutover / rollback | Exactly one Writer route authorized; no replay of accepted historical batch; can restore previous pinned image/DAG source |

Test **failure paths** as well as happy paths: invalid/mismatched hashes, stale claims, missing mounted source files, failed Spark result, partially prepared writer state, and already-completed batch handling. A green workflow or image build is **not** a durable OMOP acceptance result. Follow [Testing and Evidence](../../engineering/development/TESTING-AND-EVIDENCE.md).

## 10. Deployment, rollback, and data safety

- V2 source may coexist with V1 in Git; do **not** let both versions submit a Writer for the same batch. P5 chooses exactly one production-equivalent consumer/writer route.
- Keep the previously verified DAG ID and pinned image/digest available for fallback until V2 is accepted. Rollback of *code/routing* must not involve reverting committed business data by default.
- Persisted Claim/Stage/Checkpoint/ID Map and Source Manifest are immutable or versioned protocol state, not refactorable filenames.
- For unknown Writer outcomes, stop and perform independent **read-only** ledger/Claim/Checkpoint/PG checks before any retry. Retain old S3 READY batches and source SHA provenance.
- Shared K8s/PG/S3/Marquez operations require [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md) and [Session Coordination](../../engineering/development/SESSION-COORDINATION.md). This draft authorizes none of those operations.

## 11. Azure and Portal separation

**Azure Fabric:** leave `azure-fabric/infra-terraform/` and `workspaces/` as independent siblings. The separate Self-Runner Azure Infra workflow currently resolves `healthcare/azure-fabric/infra-terraform/components/$COMPONENT`; it should remain unchanged by the local V2 path migration. Compare `azure/` against `azure-fabric/` and check references, Terraform backends, state keys, code uniqueness, documentation and deployment ownership before deleting `azure/`. No implicit resource destruction or state recreation.

**Platform Portal:** leave `platform-portal/` in place. Migrate only local Airflow/Spark integration imports or packaging that depend on moved sources. Preserve the distinction between accepted Airflow lineage smoke, independent Spark smoke, and **not yet verified** full application Job/Run/Dataset I/O lineage.

**Documentation:** keep `documents/architecture/` for cross-system designs and decisions; `documents/systems/data-platform/<component>/CODE.md` is the unique source-map authority, and `documents/engineering/status/PROJECT-STATUS.md` remains the only current project status authority. This draft is not a second status log or an approved architecture decision.

## 12. Risks, mitigations and open decisions

| Risk / open item | Proposed handling |
| --- | --- |
| Legacy Writer/PG API names mistaken for ordinary file names | Freeze persistent interfaces; use compatible adapters and separate schema proposal if needed |
| Serialized source-relative paths change the replay/fingerprint contract | Inventory/hash fixtures and compatibility tests before moving consumers |
| Dockerfile regenerated with obsolete paths | Update generator, generated output and source-equivalence test in one PR |
| Airflow DAG disappears after GitSync subPath move | Confirm actual deployment config and parse/import before separate cutover |
| CI views `git mv` legacy task files as newly forbidden names | Audited move manifest, scoped exception; retain checks for genuinely new files |
| Global quality tooling ownership ambiguous | Decide repository-wide `.github/quality/` vs. another neutral location at P0 |
| `azure/` may contain unique Terraform implementation or documentation | Diff, confirm active root/state and update inbound links before deleting |
| Parallel old/new writers cause duplicate durable effects | Single active route, manual gate, independent readback, documented rollback |
| Shared framework becomes more complex than Person/Visit | Extract only verified duplication; keep domain mappings explicit |

**Decisions to finalize before implementation:**
1. Exact component package API/Contract versions and boundaries.
2. Placement of repository-wide `quality` scripts/tests; CI ownership and migration exception.
3. Which old scripts/images are maintained fallback assets versus history-only files.
4. How old source-relative metadata will remain readable after changing `PLATFORM_ROOT`.
5. How to validate the deployment-time Airflow GitSync path and switch one Writer route.
6. Evidence for retiring `azure/` without changing existing Azure state or resources.

## 13. Definition of done (for the future migration)

V2 is complete only after (a) all four top-level project directories and root CI links are correct; (b) maintained local code and component CODE maps are aligned; (c) Task/Step-named legacy source has been migrated or explicitly justified as compatibility/history; (d) common modules support Person/Visit without duplicating Writer/Claim safety logic; (e) CI, images, DAG and domain contracts pass; (f) a separately authorized V2 E2E proves Person/Visit durable commit and same-batch skip with independent readback; (g) rollback and old-source retirement are documented; and (h) any deletion of `azure/` is independently validated.

**This document delivers only the design proposal. No migration, rename, deployment, data write, Terraform apply, or legacy directory deletion is claimed.**

## 14. References

- [Current System Overview](../SYSTEM-OVERVIEW.md)
- [Architecture Decision Index](../decisions/README.md)
- [Local Data Platform component map](../../systems/data-platform/README.md)
- [Component-first code naming](../../engineering/development/CODE-ORGANIZATION-AND-NAMING.md)
- [Legacy Task-named Code Migration Plan](../../engineering/development/LEGACY-CODE-REFACTOR-PLAN.md)
- [Documentation Governance](../../engineering/development/DOCUMENTATION-GOVERNANCE.md)
- [Testing and Evidence](../../engineering/development/TESTING-AND-EVIDENCE.md)
- [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md)
- [Current Project Status](../../engineering/status/PROJECT-STATUS.md)

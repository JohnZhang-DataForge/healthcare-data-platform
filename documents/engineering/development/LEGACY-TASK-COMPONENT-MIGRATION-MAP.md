# Local Data Platform — Task-number path migration matrix (read-only baseline)

> Snapshot: Healthcare main `335fde4c87307e185836154abeae0c4afaaa56ae`; Self-Runner main `3faa9c243e07f62d96474b1989c2ad0ed831d9e3`. The [exact inventory](LEGACY-TASK-GIT-INVENTORY-20261105.json) stores **223 old-path Git blob SHA records**, not invented runtime states.

**This is an implementation-routing artifact, not evidence that executable paths were moved.** Current production-like Local DP still uses historical Docker COPY/PYTHONPATH, Airflow operator names, PG function names, K8s ServiceAccounts and GHCR image names. Do **not** replace task004 strings mechanically.

## Current physical subtrees and proposed functional owners

| Existing source subtree | Files | Human meaning | Proposed direction / gate |
| --- | ---: | --- | --- |
| `apps/task001` | undefined | Landing intake / Synthea Manifest | Candidate apps/landing_intake; review actual caller and CODE owner |
| `apps/task003` | undefined | Encounter Raw, Visit DQ, processed writer, ID planning | Split by business capability: visit, identity, reservation and OMOP Writer |
| `apps/task004` | undefined | NEW_ONLY runtime / CDM writer adapters / Synthea | Split into existing omop_writer and synthea adapters after Image/DAG graph |
| `kubernetes/manifests/task004` | undefined | Task004 Control and Synthea K8s | Function-first manifests under relevant workload; preserve namespace, SA, Secret names |
| `scripts/task001` | undefined | Intake and Landing historic operations | Classify read-only/one-shot/destructive before semantic scripts/landing route |
| `scripts/task002` | undefined | Person Canonical + OMOP historic operations | Classify before scripts/person and scripts/omop |
| `scripts/task003` | undefined | Visit Processed/ID/Writer reservations | Decompose by visit processing, identity, writer; many old one-shot recovery scripts |
| `scripts/task004` | undefined | NEW_ONLY generation / publishing / reconciliation | Owner by Synthea, Landing, Airflow, OMOP; avoid renaming executable calls |
| `spark/apps/task004` | undefined | Person/Visit reconciliation | Candidate spark/apps/reconciliation after imports and runner tests |
| `spark/manifests/task002` | undefined | Person Spark jobs | Candidate spark/manifests/person after job reference readback |
| `spark/manifests/task003` | undefined | Visit Spark jobs | Candidate spark/manifests/visit after K8s/Image consumers |
| `spark/manifests/task004` | undefined | Reconciliation Spark job | Candidate spark/manifests/reconciliation |
| `sql/task002` | undefined | Person CDM upsert | Candidate SQL by domain, but PG SQL function names stay pinned until migration |
| `sql/task003` | undefined | Visit ID, schema and mapping baseline | OMOP/Identity owner; schema contract approval first |
| `sql/task004` | undefined | CDM transaction, readiness and readbacks | Writer schema/read-only query split; live PG objects are not filenames |
| `tests/task001` | undefined | Intake/landing tests | New quality owner .github/quality/tests/data-platform/landing; existing frozen test discovery retained |
| `tests/task002` | undefined | Person/Canonical tests | New quality owner .github/quality/tests/data-platform/person; frozen tests only moved with CI updates |
| `tests/task003` | undefined | Visit/Identity/Writer tests | Split by capability and adjust relative repository roots, discovery and CODE map |
| `tests/task004` | undefined | NEW_ONLY/Airflow/Writer tests | Split by owning modules with full 8-image and DAG checks |

**By task:** Task001 12, Task002 19, Task003 121, Task004 71; total 223. There are also Task-numbered **filenames** outside these directories; this file intentionally inventories only directories containing an actual `taskNNN/` component and does not claim otherwise.

## Verified concrete consumer hazards

- [NEW_ONLY Writer Dockerfile](../../../local-data-platform/images/new-only-omop-writer/Dockerfile) uses a pinned Task004 CDM runtime parent image, `WORKDIR /opt/task004`, multiple COPY destinations `/opt/task004`, `PYTHONPATH` and fixed Python ENTRYPOINT. Renaming even a Python module can break an image without matching clean rebuild, immutable Digest and real rollout verification.
- [Airflow NEW_ONLY consumer](../../../local-data-platform/airflow/dags/new_only_omop_consumer.py) references existing Task004 image, PostgreSQL ledger, Kubernetes ServiceAccount and Writer Secret/env vars. DAG IDs / task_id / XCom source expectations are separate persisted identities.
- [OMOP Writer source](../../../local-data-platform/apps/omop_writer/new_only_airflow_writer.py) calls `etl.task004_batch_ledger`, `etl.task004_batch_stage`, `etl.task004_batch_commit` and `task004_writer_fence.assert_active_claim`. SQL renaming requires DB migration, not a Git folder move.
- [Local DP eight-image Workflow](../../../.github/workflows/local-dp-image-rebuild.yml) names Task004 images and discovers `tests/task004`. Git main code moving without workflow adaptation invalidates current-build packages and runtime deployments.
- [Self-Runner current main](https://github.com/JohnZhang-DataForge/Self-Runner/tree/3faa9c243e07f62d96474b1989c2ad0ed831d9e3) has 545 tracked files; **134 file paths have a Task001–004 substring**, including 55 workflow paths and 25 scripts. This is a **path-name signal**, not proof each contains a current reference; exact current-main file contents, historical SHA-pinned checkouts and live consumers still require a complete separately verified inventory.

## Existing approved OpenSpec decision takes precedence

[modernize-legacy-task-code](../../../openspec/changes/modernize-legacy-task-code/tasks.md) (2026-10-22) explicitly adopted a **Clean Slate target** for reproducible Synthea dev business state: new isolated PG business DB/S3 prefix, new functions/DAGs/images, two new Batch COMMIT+SKIP E2Es and an exact retirement allowlist. It did **not** authorize a blind, destructive PG/S3 reset. [relocate-local-data-platform](../../../openspec/changes/relocate-local-data-platform/tasks.md) still has separate historical resource/GHCR HOLDs.

The human-first layout Change must **not silently change this approved execution strategy** into a promise of dual-path runtime compatibility only. In the implementation phase, preserve the legacy running system while building the approved clean-slate replacement **in isolation**, then retire exact old consumers after authorized acceptance; adapt individual paths before actual clean-slate cutover only where independently reviewed. This keeps the user-facing Git tree tidy when finished and avoids dual permanent implementations.

## Required execution order (OPEN / HOLD)

1. Freeze dual-repo current SHA and inventory **all 223 Git source paths + all 545 Self-Runner files** by exact content, including historical pinned refs. Verify actual live Airflow DAG, K8s/Pods/Image Digest, PG function/table/view/role grants and S3 Prefix (read-only). Current JSON is only a Git tree snapshot.
2. Build exact per-file *old → new* and package/import/SQL/Workflow map; choose isolated Path A or approved exclusive Path B in the existing Clean Slate Change. Identify any non-replayable or protected data despite synthetic-source assumptions.
3. Add source and test migrations in bounded PRs, update all CODE maps, DAG/import/Docker/K8s/SQL/CI paths, and independently prove 8/8 clean container build and negative tests; do not add an extra authoritative source copy.
4. With separate live authorization, deploy to isolated data/compute, produce at least two genuinely new end-to-end Synthea batches with PG/S3 independent readback, same-batch SKIP and no duplicate writes, then issue explicit old-resource delete allowlist.
5. After verified complete cutover and post-delete regression, remove Task-number directories and residual authorized old runtime references; preserve immutable evidence in Git history. Do not mark P4 fully accepted before this point.

**Runtime action authorization:** This documentation-only inventory does not authorize K8s, GHCR, PostgreSQL, S3, Airflow or Fabric mutations, new costs, or producer replays. Existing CURRENT/PENDING progress belongs to the relevant active OpenSpec tasks; full migration remains HOLD.

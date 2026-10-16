# Healthcare Data Platform — Public Read-Only Demo Architecture v2.0

**Date:** 2026-10-13 · **Status:** PROPOSED / documentation only · **Canonical location:** `healthcare-data-platform/docs/demo-plan/`  
**Supersedes for new planning:** public-demo-plan v1.1 documents in Self-Runner, retained as historical source. **TASK004 IN PROGRESS; TASK005 ON HOLD.**

## Purpose and verified facts

Build an unauthenticated, strictly read-only portfolio page enabling reviewers to understand the real system in 30–60 seconds, inspect verified Spark/data lineage in 3–5 minutes, and follow evidence to exact Git and Self-Runner runs. Never expose operational APIs. Main and real workflow results outrank historical NEXT sections.

- **Independent producer:** `dw-synthea` NEW_ONLY Job on worker01; `synthea-local` Retain 5Gi bound PVC; real Synthea v3.3.0 generated **73 Person / 12159 Encounter / 18 CSV**, and a second Pod safely reused the frozen request ([Run 38484300008](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38484300008)). **Not yet:** globally collision-free, dedicated published image digest or immutable S3 READY. EXISTING_ONLY/MIXED remain on hold.
- **Immutable exchange boundary:** producer publishes a versioned, checksummed SeaweedFS S3 Manifest *last*. Airflow only discovers existing READY batches; it never invokes or retries Synthea. Producer and consumer are independently scheduled.
- **Consumer:** `landing_batch_discovery` runs every 15 minutes; PostgreSQL Claim Guard is wired but persistence disabled; controlled historical manual Spark Person/Visit and Processing Reconciliation were verified ([Run 38476079452](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38476079452)). Real automatic new-batch claim and writer COMMIT are not done.
- **Database:** real S3 Parquet → PostgreSQL Writer correctly rejected existing source-person drift and retained zero business changes ([Run 38479591382](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479591382)). This is a **successful expected safety rejection**, not a successful positive ROLLBACK or COMMIT. Full fresh-batch ROLLBACK, fencing, COMMIT and independent DB reconciliation remain pending.
- At audit time [PR #89](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/89) for versioned NEW_ONLY CSV and source key prepublication checks was open, **not a merged acceptance**.

## Target architecture

```text
worker01 / dw-synthea             worker02 / dw-airflow + dw-spark
NEW_ONLY Job (standalone)         landing_batch_discovery (scheduled)
  -> LocalPath stable request      -> read verified S3 manifest
  -> CSV contract + identity      -> Claim Guard (persistence OFF)
  -> S3 immutable READY [pending] -> manual Spark Person/Visit + reconcile (PASS)
                 |                            |
        SeaweedFS/S3                        |
                 +----------------------------+
                              |
                   OMOP PostgreSQL worker03
             drift protection (PASS) -> fresh commit (PENDING)

Observability sidecar, not a business orchestrator:
Airflow OL provider + Spark OL agent -> private Marquez API + separate DB
                                           -> reviewed snapshots/export
                                           -> external static HTTPS demo
                         [Superset optional after verified DB commit]
```

OpenLineage is an event standard/instrumentation ecosystem, **not** a separately required server; Marquez is the receiver, store and internal UI. Airflow and Spark emitters do not automatically stitch a complete graph: actual dataset namespaces, run linkage, S3A inputs, Spark Parquet outputs and PostgreSQL commit events require verification. Only observed edges qualify as verified; explicit custom lineage must represent real operations.

## Milestones and acceptance

| Stage | Scope | Gate |
| --- | --- | --- |
| D0 | Runner read-only inventory: node/PVC/resource capacity, Airflow/Spark/Java/OpenLineage versions, networking, evidence datasets, redaction risks | Exact-SHA compatibility/resource/security report, no mutation |
| D1 | Static public evidence MVP: architecture, run cards, code links, versioned partial/verified labels | Static build, anonymous browser, links, leakage scan |
| D2 | Private Marquez in `dw-demo`, pinned version, ClusterIP, standalone metadata DB/user, restart-safe state | Synthetic **test** event persisted, no changes to OMOP/Airflow |
| D3 | Spark agent on an already proven historical Person Processing-only run | Real run → actual S3 input → actual output dataset visible, no DB mutation |
| D4 | Airflow provider on existing `landing_batch_discovery`, real emitter/stitch audit; producer evidence only after S3 READY validation | Authenticated event evidence; missing links honestly labeled |
| D5 | Approved sanitized Marquez exports / screenshots linked from static site | Anonymous **read-only**, zero private API exposure, rollback |
| D6 | Optional demo-only PostgreSQL views/Superset | Only after actual fresh-batch COMMIT + independent DB replay evidence and security review |

**Evidence identity:** `main_sha + workflow_run_id + batch_id + manifest_sha256 + entity + processing_run_id` (explicitly unknown where unavailable); classify `LIVE_PASS`, `EXPECTED_BLOCK`, and `PENDING` separately. Old committed OMOP totals must be identified as historical and never presented as committed results of the new NEW_ONLY batch. Do not equate Spark PASS, a refusal PASS, or a transaction ROLLBACK with database COMMIT.

## Security and governance

Keep Marquez UI/API, Airflow, Spark, SeaweedFS, PostgreSQL, Kubernetes, secrets and the self-hosted Runner private. A public static site serves only reviewed synthetic aggregates, redacted snapshots and linked public evidence. No public reverse proxy to Marquez APIs; no SQL execution, Job triggers or control operations; HTTPS/CSP and a tested publication rollback. Use separate Marquez database/role (reuse existing PG *instance* only after capacity and migration review; never the `omop` or `airflow` databases). Stateful volume affinity constrains scheduling; no assumed auto-rebalance. OpenMetadata, Kafka, Kinesis, live public Marquez and Superset are not the first MVP.

Demo planning proceeds in its own PRs without touching TASK004 writer safety or the in-flight NEW_ONLY PR. Per implementation round: feature PR, exact-SHA Self-Runner validation, artifact/evidence, merge Main; stop after three repeat failures. **Next recommended work is D0 read-only audit**, then public static scaffold while private lineage integration is gated by capacity checks.

## References

- [Full authoritative Chinese v2.0](./PUBLIC-DEMO-ARCHITECTURE-v2.0.zh-CN.md)
- [Original English v1.1](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/healthcare-data-platform-public-demo-plan.md)
- [Original Chinese v1.1](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/healthcare-data-platform-public-demo-plan-v1.1-zh-CN.md)
- [Local NEW_ONLY verified checkpoint](../tasks/SYNTHEA-NEW-ONLY-LOCAL-GENERATOR-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)

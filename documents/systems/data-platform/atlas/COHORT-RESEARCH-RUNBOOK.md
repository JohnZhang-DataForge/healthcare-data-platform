# Local ATLAS3 — synthetic OMOP Cohort operations and safe refresh

> Owner: `deploy-local-ohdsi-atlas` (ATLAS research consumer) plus
> `derive-local-omop-observation-period` (CDM business writer).
> Last physical review: 2026-11-11, ET.
> This is a research-grade **synthetic** EHR demonstration, not real patient enrollment.

## 1. Data and limits

- ATLAS3/WebAPI3 `v3.0.0` pinned, private `dw-atlas` on worker03, browser `https://atlas.johnzhang-dataforge.site/atlas/`.
- Native WebAPI source `LOCAL_OMOP` ID 1 points CDM/Vocabulary to `cdm`, Results to `atlas_results`, Temp to `atlas_temp`; database authentication and RBAC gate protected endpoints.
- PG17 `omop` has 1,394 `cdm.person`, 200,556 `cdm.visit_occurrence`, 1,394 **real committed** `cdm.observation_period`, vocabulary 44814724 valid, 26 `atlas_results` tables, and pre-existing ACHILLES 294 analysis / 1,393 results / 45 distributions. Evidence: [OP COMMIT and independent readback](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43014735694), [Results tables transaction](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42984162727).
- `observation_period` **is inferred**: per person `start=MIN(visit_start_date)`, `end=MAX(visit_end_date)`, period type 44814724 (Period covering healthcare encounters). This interval does *not* prove uninterrupted insurance coverage, continuous EHR capture or complete lifelong medical history. Two records cover fewer than 30 days. Studies requiring lookback should set an explicit minimum-observation rule.
- ETL historical source exceptions remain: 113 Person / 5,799 Visit pre-Stage but ID-mapped; 1 of 19 Task004 batches has no matching Landing Manifest SHA (its Stage 23 Person / 3,592 Visit). Treat as provenance exceptions, not a reason to synthesize missing Manifest or duplicate business rows.

## 2. Source and backup evidence

1. Current generated OP SQL: [OMOP Writer v1](../../../../local-data-platform/apps/omop_writer/observation_period_encounter_v1.sql). The source lives with OMOP, not ATLAS, FHIR or HL7 adapters.
2. Prewrite **single-table** snapshot in private Azure Blob: `landing/omop/observation-period/encounter-v1/backups/run-43013745100/`, archive `observation_period.dump`, SHA256 `d3045d23f19a4819031d0c5d68c7b92618eec8b83d07af9da1e60910adbc899f`; [snapshot/GET/`pg_restore --list` acceptance](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43013745100). It is an **empty target-table prewrite** snapshot, **not** a backup of the newly committed 1,394 rows, nor a full current CDM backup.
3. [Full DML in explicit ROLLBACK](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43014233113) PASS and [one-shot COMMIT](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43014735694) PASS. **Never rerun** either as a way to fix a later issue; original once-only executor fails on nonempty target.
4. The separate ATLAS app/Results/Temp **pre-Results-DDL** private Azure snapshot is at `landing/atlas/backups/pg17-research/run-42982698266/` with SHA256 `5624643d1255757e6836dcecd56e641685eb8d51ef8c1e85b7a27279a3a3c340`. Neither pre-migration archive proves a full post-Cohort restore has been tested. A new post-study backup and isolated restore exercise are still required.

## 3. Safe Cohort study procedure

- Use an authenticated WebAPI3 admin identity to select `LOCAL_OMOP` and create a minimal synthetic Visit cohort. A read-only `atlas_demo` login is not an authoring account; do not change its fixed password or grant write privileges for a demo.
- [Official Circe cohort SQL compiler](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43015271347) returned HTTP200/5,207-byte template from a VisitOccurrence first-event rule with no inclusion/exclusion and zero prior/post observation window. The compiler did **not** execute the cohort.
- Native WebAPI3 saved **Cohort Definition ID 1** named `LOCAL_OMOP Synthetic Visit Cohort 20261111`, as [independently verified by read-only GET and PG SELECT](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43016245774). On save, WebAPI3 normalizes `VisitOccurrence` to include `VisitTypeExclude=false`, an equivalent default; do not demand byte-for-byte JSON equivalence or blindly create another ID.
- A **side-effectful** GET `/WebAPI/cohortdefinition/{id}/generate/LOCAL_OMOP` launches a new batch Job; this is not a status endpoint. Only execute via a single reviewed one-shot workflow when the definition, no previous Job, pre-existing Cohort Results count, bounded resources and needed privileges are confirmed. Never use a recurring probe or HTTP retry on `generate`.
- Read-only status: `/WebAPI/cohortdefinition/{id}/info` and `/WebAPI/job/execution/{executionId}` with authenticated JWT. Actual success requires `COMPLETED` and **independent PostgreSQL SELECT** of `atlas_results.cohort` by `cohort_definition_id`: number of distinct subjects, valid dates, no unmatched person, all cohort dates within the committed Observation Period, plus original Person/Visit/ACHILLES counts unchanged.
- Browser validation with the real `atlas_demo` user remains separate: a valid WebAPI API response does not prove the Data Sources / Cohort UI is rendered correctly.

## 4. After new synthetic batches or failures

- A new CDM Person/Visit batch invalidates the original **1,394-person fixed-snapshot OP writer contract**. Do **not** rerun its one-shot workflow. Submit a new OpenSpec change for incremental encounter-bound periods with stable identity, no overlap and independent source audit, then adapt cohort rules.
- Do not replay the prior official ACHILLES K8s Job: its JSON export failed *after* physical results tables were populated. Independently decide whether aggregate refresh is necessary, and use a fresh authorized, non-destructive operation (source unchanged does not justify refresh).
- Never delete/truncate existing Cohort Results or restore the entire prewrite database merely to clear a failed job. Check the actual `cohort_definition_id`, native job status, PG catalog and source-of-truth first.
- Keep secrets and generated patient-level records out of repositories and Actions logs; only publish safe row counts, job IDs, SQL digests and immutable archive identifiers.

# TASK004 STEP04F — Dynamic PostgreSQL Writer / Live ROLLBACK Acceptance

**Status: DYNAMIC PG WRITER TRANSACTION VERIFIED IN REAL DATABASE (ROLLBACK); NEW-BATCH COMMIT DISABLED; AIRFLOW AUTO-LOAD NOT YET INTEGRATED.**

## What was built
- `airflow/dags/task004_cdm_dynamic_pg_writer.py` exposes pure `render(context, rows, entity, allow_commit=False)` for Person or Visit.
- Batch identifiers, incoming row counts and source Processing URIs come from the validated Airflow dynamic plan, **not** fixed 23/3592 counts, fixed dates or old 113/5799 historical totals.
- Transaction includes batch-scoped ledger, canonical stage, stable OMOP ID mapping, CDM target load, source/target field equality checks and verified commit checkpoint.
- Source business keys, row fingerprints, payload shapes and batch plan digest are checked before SQL rendering. Ledger replay identity and stage conflict are checked transactionally. Valid standard OMOP vocabulary concept IDs are checked before writes.
- Visit additionally requires the same batch's verified Person commit and a live Person ID Map/CDM foreign-key match.
- Existing mapped target rows are never updated; if content differs the entire transaction fails. Identity columns allocate stable mapping IDs; no sequence resets.
- **Default output explicitly ends in `ROLLBACK;`.** SQL ending `COMMIT;` requires an explicit Python `allow_commit=True` option and is not exposed to the Airflow DAG. This is only a SQL generator; neither the Airflow DAG nor existing image executes it.

## Evidence
- [Self-Runner Run 38404502391](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38404502391) **SUCCESS**.
- Pinned Healthcare source SHA `1daf8e2aff28ca4d8c6055c04c055dd60843394d`.
- Eight Python unit tests for rollback-by-default, target conflict guards, dynamic count/plan drift, parent FK checks, invalid digest and explicit COMMIT opt-in.
- Real PostgreSQL `omop` in `dw-postgre`, test A: synthetic Person → full ledger/stage/map/target/commit statements → ROLLBACK → independent new session confirms no synthetic ledger/map and historical Person/Visit counts unchanged.
- Test B: synthetic Person→synthetic Visit in the **same PostgreSQL transaction**, including Visit FK and verified Person checkpoint → ROLLBACK → independent new session verifies synthetic ledger, stage, commit all zero.
- Markers: `DYNAMIC_PERSON_REAL_POSTGRESQL_ROLLBACK=PASS`, `DYNAMIC_PERSON_VISIT_REAL_POSTGRESQL_ROLLBACK=PASS`, `DYNAMIC_PERSON_VISIT_NO_PERSISTENT_MUTATION=PASS`. Original Person=136 and Visit=9391 unchanged.
- Initial real rollback run [38404029089](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38404029089) caught a SQL dollar-quoting typo and stopped transaction; corrected in SHA `1daf8e2...` and verified by subsequent PASS. No synthetic commit survived.

## Important limitations / next step
1. This validates dynamically *generated SQL and transactions* against actual PostgreSQL but does **not** mean the new-batch Airflow end-to-end writer is deployed or enabled.
2. Before COMMIT: implement a privileged-but-minimal worker with authenticated S3+Parquet source fetch, plan/source hash verification, PostgreSQL connectivity and secret handling, image pinned by immutable digest; integrate it as sequential Airflow tasks and add readback.
3. Generalized multi-batch and parallel replay recovery semantics, additional concurrency safety across writers, source row fingerprint recomputation and explicit per-batch authorization / bounds remain to be reviewed.
4. Airflow DAG `task004_processing_pipeline` still ends at `cdm_materialization_plan` and does not invoke this SQL renderer. Fixed batch Person=136, Visit=9391 from last verified DB readback unchanged.
5. STEP04G end-to-end DAG replay/unknown-commit recovery pending; TASK005 ON HOLD.

**This step is a successful complete implementation + real rollback test loop, not an authorized new-batch COMMIT.**

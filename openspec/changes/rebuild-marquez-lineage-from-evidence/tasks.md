# Tasks — Rebuild Marquez lineage from evidence

## 1. Recovery inventory and provenance
- [x] 1.1 Reconfirm Marquez retention disabled, original PG14 volume still bound, historical metadata rows zero.
- [x] 1.2 Examine K8s backup/snapshot resource inventory, archived GitHub P5 evidence, SeaweedFS Filer named archive buckets and raw lineage prefixes.
- [x] 1.3 Record strict distinction between exact restored history and newly executed genuine events.

## 2. Bounded actual OpenLineage run
- [x] 2.1 Preflight existing Airflow `platform_portal_openlineage_probe` DAG and no-retention live config.
- [x] 2.2 Execute exactly one opt-in Airflow real two-task run with unique ID; no synthetic `/lineage` HTTP POST.
- [x] 2.3 Independently verify Marquez Job/Event counts and linked task records; report success or failure without rewriting historical proof.

Actual Airflow live evidence: [Self-Runner Run #41858128218](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41858128218), 2026-11-04 15:29 UTC: retention off, source SHA, no active DAG, true DagRun SUCCESS, Marquez PG14 counts Jobs 0→3, Lineage Events 0→6, Datasets 0→0. These are newly executed Airflow events, NOT recovered historical Patient/Encounter events.

## 3. Bounded real Spark fixture lineage (not historical Patient/Encounter)
- [x] 3.1 Preflight no active TASK004 Spark, the pinned local fixture, and permanent no-retention.
- [x] 3.2 Execute one isolated portal-a4 Spark probe with synthetic 3-row CSV, unique ConfigMap/PVC and no S3 or OMOP access.
- [x] 3.3 Verify genuine Spark Job/Event + Input CSV / Output Parquet Datasets are durably stored in Marquez; record exact run and PV.
- [x] 3.4 Do not label synthetic probe datasets as previously deleted Patient/Encounter lineage.

Actual Spark fixture: [Self-Runner #41858844788](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41858844788), 2026-11-04 15:34 UTC: 3-row synthetic input, isolated PVC `portal-a4-r41858844788-output`, SparkApplication `portal-a4-r41858844788` COMPLETED, PG14 Jobs 3→7, Datasets 0→2, Events 6→18. No S3, OMOP or Writer mutation. THIS IS NOT ORIGINAL OCTOBER PATIENT/ENCOUNTER HISTORY.

## 4. Future historical Patient/Encounter recovery
- [ ] 4.1 If original committed raw events / verified PG14 dump found, replay/restore in provenance-controlled fashion with independent readback.
- [ ] 4.2 Rebuild Patient/Encounter graph only from actual new Spark execution or byte-exact old OpenLineage, under a separate stage gate; never re-run committed Writer.


## 5. New Patient / Encounter / Reconcile Spark-only regeneration (P3)
- [ ] 5.1 Read-only live preflight: current SHAs, DAG GitSync, no-retention, active Airflow/Spark/Actions, READY Manifest identity and Claim/Ledger/Fence; record evidence and select only genuinely unclaimed input.
- [ ] 5.2 Independently record protected PG17 OMOP state before running; verify source digest, no Writer COMMIT flag, exact manual DAG route and original pause state.
- [ ] 5.3 Run exactly one uniquely identified real Patient + Encounter + Reconcile Spark-only flow under shared concurrency gate, without OMOP Writer or old Batch replay.
- [ ] 5.4 Independently GET Marquez action-level Job/Run/Input+Output DatasetVersions, Reconcile's two exact inputs, column facets where real, and public read-only graph. Preserve START-only / missing facets.
- [ ] 5.5 Independently read back PG17 and prove protected state unchanged; attach exact source SHA, workflow Run, actual Spark IDs, Airflow tasks, Marquez details and failures to evidence.
- [ ] 5.6 Run required CI, review and merge scope-limited PRs only after required gates pass; mark unexecuted/blocked tasks honestly.

**Status 2026-11-04:** this plan is not proof of business Spark execution or graph restoration. The verified 3-row portal P2 fixture remains separate from real Patient/Encounter.

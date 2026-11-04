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

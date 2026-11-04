# Tasks — Rebuild Marquez lineage from evidence

## 1. Recovery inventory and provenance
- [x] 1.1 Reconfirm Marquez retention disabled, original PG14 volume still bound, historical metadata rows zero.
- [x] 1.2 Examine K8s backup/snapshot resource inventory, archived GitHub P5 evidence, SeaweedFS Filer named archive buckets and raw lineage prefixes.
- [x] 1.3 Record strict distinction between exact restored history and newly executed genuine events.

## 2. Bounded actual OpenLineage run
- [ ] 2.1 Preflight existing Airflow `platform_portal_openlineage_probe` DAG and no-retention live config.
- [ ] 2.2 Execute exactly one opt-in Airflow real two-task run with unique ID; no synthetic `/lineage` HTTP POST.
- [ ] 2.3 Independently verify Marquez Job/Event counts and linked task records; report success or failure without rewriting historical proof.

## 3. Future recovery
- [ ] 3.1 If original committed raw events / verified PG14 dump found, replay/restore in provenance-controlled fashion with independent readback.
- [ ] 3.2 Rebuild Patient/Encounter graph only from actual new Spark execution or byte-exact old OpenLineage, under a separate stage gate; never re-run committed Writer.

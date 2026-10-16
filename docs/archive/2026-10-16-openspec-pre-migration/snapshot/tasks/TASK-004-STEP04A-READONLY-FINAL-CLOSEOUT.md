# TASK004 STEP04A — Read-only PostgreSQL + Source Preflight Closeout

**Status: INVESTIGATION COMPLETE / READ-ONLY EXECUTION PASS / WRITE READINESS BLOCKED.**
Evidence captured 2026-10-13 UTC. The STEP04A investigation is closed; its `BATCH_ISOLATION_GATE=BLOCKED` is an explicit STEP04B design requirement, not a license to proceed to direct writes.

## Fixed accepted source
- `task004-airflow-task004-step03e-38324111846`
- Manifest SHA256 `ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1`, verified against the **actual immutable S3 manifest object**.
- Fixed Processing XCom URIs documented in `TASK-004-STEP04A-XCOM-PROCESSING-URI-READONLY-EVIDENCE.md`.
- Real ARC run [38342434613](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38342434613): **SUCCESS**, exact Healthcare SHA `56fdb3b04fffefb18a590ff25e51493506c8db40` read-only Parquet/S3 and SQL mapping check.
- Prior database catalog read-only [38337396849](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38337396849); map integrity [38337666759](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38337666759); real Airflow XCom URI [38340130123](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38340130123).

## Actual readback

| Gate | Result |
|---|---|
| Manifest actual content SHA | PASS |
| Person Parquet files / source rows | 1 / 23 |
| Visit Parquet files / source rows | 1 / 3592 |
| Person canonical schema readback | PASS, 18 columns |
| Visit canonical schema readback | PASS, 27 columns |
| Both source business keys nonblank and unique | PASS |
| All Visit source_person_id in same batch Person set | PASS |
| Person keys already in etl.person_id_map | **0** |
| Person keys requiring allocation | **23** |
| Visit keys already in etl.visit_occurrence_id_map | **0** |
| Visit keys requiring allocation | **3592** |
| Existing content conflict for this batch | **No existing mapping keys overlap; field-level comparisons NOT PERFORMED** |
| Existing shared Stage batch_id / manifest_sha | **Absent (BLOCKED for direct load)** |
| PostgreSQL mutation | NO |
| Landing / Processing mutation | NO |
| Airflow trigger | NO |

All 23+3592 keys are new to current **synthea-keyed mapping tables**. This is **not** proof of already valid CDM concepts, stage contract, or insertability. Concept IDs, required CDM fields, operational race windows, target natural-key collision with unmapped legacy rows, and row-level source fingerprints must be addressed before commit.

Existing historic OMOP: `cdm.person=113`, `cdm.visit_occurrence=5799`, existing maps 113/5799; zero duplicate business keys, zero orphan visits and zero target/map gaps at observation time. Full catalog, indexes and privilege evidence remains archived in catalog Runner. Prior `etl.person_stage=113` is shared and is **not batch-isolated**.

## Canonical STEP04B design inputs / must-fix items

1. Preserve OMOP CDM core schema; implement **separate batch ledger** keyed by `(batch_id, manifest_sha256)` with immutable source identity and mismatch fail-closed.
2. Batch-scoped Person/Visit candidate staging, with enforceable per-batch constraints and replay-safe persistent mapping assignment. **Never point new loaders at shared `etl.person_stage` with full-table upsert**.
3. Map source `source_record_id` to `etl.person_id_map.source_person_id`, and `source_encounter_id` to `etl.visit_occurrence_id_map.source_encounter_id`; apply stable `source_system=synthea`.
4. Map 18-column patient and 27-column encounter canonical inputs to actual 18-column OMOP Person / 17-column Visit; establish vocab and required concept ID mapping; protect historical data and FK order (Person before Visit).
5. Explicit identical-key / identical-content NO-OP; mismatched-key-content FAIL CLOSED unless approved field update rules; concurrency locks and uncertain-commit readback. Same batch reuse must NOT create new Synthea or new Processing side effects.
6. Independent DB readback for each batch with person/visit source-row fingerprints, map/target link and all FK, with old-historical counts/fingerprints protected.
7. Before any database mutation obtain explicit approval of expected inserted ranges (current planning inputs: **23 Person, 3592 Visit; actual commit counts must be preflight recalculated**).

**STEP04A closed as investigation (PASS) with explicit blocking design issues for STEP04B.** TASK004 remains IN PROGRESS; TASK005 ON HOLD.

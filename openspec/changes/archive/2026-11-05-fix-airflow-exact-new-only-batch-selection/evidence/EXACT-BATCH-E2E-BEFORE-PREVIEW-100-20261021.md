# Exact Batch Airflow selection — real E2E PASS with XCom preview still 25 (2026-10-21)

## Fix and publish

- [Healthcare PR #369](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/369) merged Main `67776c1dfdc2fc7a23919c36fcdc0437f021bdfb` after passing source/contract, Discovery clean build, Airflow DagBag, Writer regression and eight-image PR CI.
- [Main eight-image build/publish #39636935979](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39636935979): **SUCCESS**, immutable `git-67776c1...` tags and latest promotion. Writer GHCR digest: `sha256:13224e3c2dc359f976f579b0e089694d728b643ecb1964b94402068f67286fad`.
- **Display preview remained 25 during this test.** The Discovery Pod verified the exact requested Batch from its entire S3-validated READY inventory, returned one `verified_selected_batch` besides the bounded preview, and Airflow used that attestation, not preview membership.

## Exact real immutable Batch and E2E

- Existing previously generated and S3-verified READY Batch from [three-Batch source run #39630497311](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39630497311): `synthea-new-only-gh-39630497311-01`, **100 Person**, **15,188 Encounter**; Manifest SHA256 `94710cb037c40520b69b67bbd0bfd1b4dcbf6b6dba9d84af2b203632d216db04`. No new generation, no database reset.
- Temporary Self-Runner [PR #200](https://github.com/JohnZhang-DataForge/Self-Runner/pull/200), actual [Run #39637787637](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39637787637): **SUCCESS**. Exact Main SHA and both Airflow GitSync roles match, DAG parse/Writer secret passes. Discovery, exact Batch selection, readonly Claim, Spark Person, Spark Encounter, Reconciliation, handoff, Writer authorizer, atomic Writer and final success tasks all **SUCCESS**. Observed Writer Pod imageID checked against published digest.
- Independent PostgreSQL readback in a read-only transaction:

| Verification | Before | After first COMMIT | Same Batch rerun |
| --- | ---: | ---: | --- |
| `cdm.person` | 394 | 494 | Unchanged |
| `cdm.visit_occurrence` | 52,308 | 67,496 | Unchanged |
| Batch Claim | 0 | 1 | Unchanged |
| Batch COMPLETED | 0 | 1 | Unchanged |
| Batch Ledger | 0 | 1 | Unchanged |
| Batch Person stage & mapped | 0 | 100 | Unchanged |
| Batch Visit stage & mapped | 0 | 15,188 | Unchanged |
| Batch VERIFIED checkpoints | 0 | 2 | Unchanged |

- First Airflow run `local-dp-fresh-newonly-39637787637`: `STATE=success`, `FRESH_NEW_ONLY_INDEPENDENT_OMOP_PG_READBACK=PASS`.
- Second Airflow run `local-dp-fresh-skip-39637787637`: `STATE=success`, Spark/Writer skipped; `NEW_ONLY_SAME_BATCH_REPEAT_SKIP=PASS` and **`NEW_ONLY_REPEAT_ZERO_PG_CHANGE=PASS`**.
- Original DAG pause state restored: `DAG_PAUSE_RESTORED=PASS`.
- Separate live Airflow metadata probe [Run #39638642734](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39638642734) confirms `scan_ready_manifests`, `select_verified_new_only_batch`, Spark Person/Encounter, reconcile and handoff success with preview still 25.

## Display-only follow-up

The first phase's real E2E and idempotency guarantees are **PASS**. The next independently tested change may increase `MAX_XCOM_PREVIEW` 25→100. This must not modify exact selection, Manifest validation, Claim/Spark/Writer fencing or database semantics. The preview should still truncate at 101 with `preview_truncated=True`, but business processing must continue to work.

Other Synthea READY Batches `synthea-new-only-gh-39630497311-02` (100 Person / 15,400 Encounter) and `-03` (100 / 13,237) remain available for optional later full E2E.

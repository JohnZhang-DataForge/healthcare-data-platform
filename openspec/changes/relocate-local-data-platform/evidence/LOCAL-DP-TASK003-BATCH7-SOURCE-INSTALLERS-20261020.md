# TASK003 Batch 7 — One-time Processed / Writer installers, with explicit Manifest HOLD (2026-10-20)

> OpenSpec Change: `relocate-local-data-platform` · Task 4.9 PARTIAL, 4.1 and 4.8 partial. Delete historical source installers only, not formal runtime/contract/tests.

## Starting source and full recovery

- Frozen Healthcare Main `61d393b31bd68b92af98908e2934762131842242`; Self-Runner Main `fb1be4292e295fd0824b1af255171a846f541fb2`. Both repos had 0 open PR at start. Current HEAD and source file blob SHA below were individually checked from GitHub; all six are present in the frozen historical TASK003 source inventory and can be restored from immutable Git commit. No overwrite of parallel Fabric work.
- The Healthcare-Specs 393-file historical independent backup and previously confirmed incremental overlay give independent old-source recovery; this batch uses immutable current-main Git URLs rather than assuming the current HEAD will retain deleted files.

| Deleted one-shot source/installation script under `local-data-platform/scripts/task003/` | Git Blob SHA | Immutable recovery URL | Exact formal outputs |
| --- | --- | --- | ---: |
| `05g2c2c2b2-prepare-runtime-bundle-source.sh` | `6e7d868c8ce083d2007514e1957af62ff2406ab9` | [fixed source](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g2c2c2b2-prepare-runtime-bundle-source.sh) | 4/4 MATCH |
| `05g2c2c3a-prepare-writer-reservation-acquire.sh` | `f8d4cbac08b075ab31e21ff9240b0ea6af81597d` | [fixed source](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g2c2c3a-prepare-writer-reservation-acquire.sh) | 1/1 MATCH |
| `05g2c2c3b-prepare-postlock-preflight.sh` | `9b45b90c8ead81025cc39596dd9c70532044028f` | [fixed source](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g2c2c3b-prepare-postlock-preflight.sh) | 1/1 MATCH |
| `05g2c2c3c1-prepare-write-permit-source.sh` | `9ce2f558f80b5bd619bdb573ccb735f3c3f562f5` | [fixed source](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g2c2c3c1-prepare-write-permit-source.sh) | 3/3 MATCH |
| `05g3b1-prepare-processed-dq-publisher-source.sh` | `d3c3a0a7cb4d49f932c9dfb80ce0a3383f720747` | [fixed source](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g3b1-prepare-processed-dq-publisher-source.sh) | 2/2 MATCH |
| `05g5a-prepare-processed-publication-reservation-release.sh` | `5107eafd2af78a638fc692d903720f93d86e0528` | [fixed source](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/61d393b31bd68b92af98908e2934762131842242/local-data-platform/scripts/task003/05g5a-prepare-processed-publication-reservation-release.sh) | 1/1 MATCH |

## Full generated file byte comparison: 12/12

Each Bash generator was actually read from frozen Main. Extracted all literal `cat > "$STAGE/<path>" <<'<TAG>'` heredocs and independently fetched the corresponding current formal Git source. Compared full strings including final newline, not paths or snippets. All 12 out of 12 matched identically; every product is untouched/KEEP:

### `05g2c2c2b2-prepare-runtime-bundle-source.sh`
- `local-data-platform/spark/manifests/task003/visit-processed-writer.yaml.tpl` — EXACT MATCH / KEEP
- `local-data-platform/apps/task003/build_visit_processed_runtime_bundle.py` — EXACT MATCH / KEEP
- `local-data-platform/tests/task003/test_visit_processed_runtime_bundle.py` — EXACT MATCH / KEEP
- `local-data-platform/scripts/task003/05g2c2c2b2-prepare-runtime-bundle.sh` — EXACT MATCH / KEEP

### `05g2c2c3a-prepare-writer-reservation-acquire.sh`
- `local-data-platform/scripts/task003/05g2c2c3a-acquire-writer-reservation.sh` — EXACT MATCH / KEEP

### `05g2c2c3b-prepare-postlock-preflight.sh`
- `local-data-platform/scripts/task003/05g2c2c3b-capture-postlock-preflight.sh` — EXACT MATCH / KEEP

### `05g2c2c3c1-prepare-write-permit-source.sh`
- `local-data-platform/apps/task003/issue_visit_processed_write_permit.py` — EXACT MATCH / KEEP
- `local-data-platform/tests/task003/test_visit_processed_write_permit.py` — EXACT MATCH / KEEP
- `local-data-platform/scripts/task003/05g2c2c3c-issue-write-permit.sh` — EXACT MATCH / KEEP

### `05g3b1-prepare-processed-dq-publisher-source.sh`
- `local-data-platform/spark/apps/visit/publish_processed_dq.py` — EXACT MATCH / KEEP
- `local-data-platform/tests/task003/test_processed_dq_publisher.py` — EXACT MATCH / KEEP

### `05g5a-prepare-processed-publication-reservation-release.sh`
- `local-data-platform/scripts/task003/05g5a-release-processed-publication-reservation.sh` — EXACT MATCH / KEEP

## Bounded live-consumer/static call scan

- Healthcare frozen, untruncated Git tree: 64/64 high-priority sources inspected (27 GitHub workflows, 15 Airflow DAGs, 8 Dockerfiles, 14 Task004 Shells) with **zero** exact-basename reference to the six retired installers.
- TASK003 75/75 Shells inspected with **zero external** exact-basename call for the six retired files (self-source mentions only). Formal runtime scripts remained unmodified.
- Self-Runner latest Main: 16/16 relevant workflows checked; no exact-basename reference. Other workflows and dynamic variables/external references not exhaustively excluded; these are explicitly bounded negative checks, not proof of every indirect consumer.
- The new-root, fresh-batch NEW_ONLY E2E and repeated no-PG-change SKIP were previously proven in [Self-Runner #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433); no frozen historical TASK003 batch was replayed.
- Retain original Writer Fencing, permit logic, K8s reservation acquisition/release, all PG recovery utilities, processed DQ/Manifest publishers and tests. Deleted files only install already-tracked exact content; no Kubernetes/SeaweedFS/Postgres/Helm/GHCR write in this change.

## Explicit new E/HOLD — Manifest Publisher installer

- `05g4c1-prepare-processed-manifest-publisher-source.sh` **is NOT deleted**, despite its two generated outputs matching tracked files (2/2 MATCH). Two still-existing formal run scripts contain direct literal references:
  - `local-data-platform/scripts/task003/05g4c2-prepare-processed-manifest-publication.sh`, approx line 167
  - `local-data-platform/scripts/task003/05g4c2-publish-processed-manifest.sh`, approx line 125
- Both scripts use `git diff --quiet -- spark/apps/visit/publish_processed_manifest.py tests/task003/test_processed_manifest_publisher.py scripts/task003/05g4c1-prepare-processed-manifest-publisher-source.sh` as an immutable checkpoint / source drift guard. Changing or deleting the third path without re-evaluating and testing this gate could weaken or break historic publication safety; separate change required before reassessment.
- `06c4e-prepare-committed-cdm-visit-materialization.sh` remains independent **E/HOLD** due to dynamic Contract-generation completeness not demonstrated.

## Navigation / merging conditions

- `documents/systems/data-platform/landing/CODE.md` TASK003 active list **39→33**, and explicitly annotates the Manifest installer E/HOLD. Total TASK003 Shells **75→69**; all twelve formal outputs unchanged.
- PR must run all applicable real CI (OpenSpec Change Gate + static validation, Code Naming, Docs Links, Local DP DAG/Source/Provenance/Isolated Build, NEW_ONLY writer and CDM Reader regression). Merge via squash only after **final PR HEAD 10/10 checks PASS**, not based on previous PR runs. Failed checks require diagnosis/retest before merge.
- This batch does not close 4.1, 4.8, 4.9, 4.10 or 5. After remaining targeted audit/cleanup, repeat appropriate actual runtime checks and archive only after final verification.

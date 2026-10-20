# Local DP TASK003 Batch 6 — Processed Publication / Writer frozen installers (2026-10-20)

OpenSpec change: `relocate-local-data-platform`, Task 4.9 PARTIAL. This batch retires only five one-time source generator/install Shell scripts; all formal code, runners, business contracts and valuable tests stay in the active repository.

## Frozen baselines and immutable restoration

Healthcare Main before this batch: `e3ce9f2e5adbfd22f25e3bfca1b2ae892f4f086a`; Self-Runner Main: `c9bb734517a0e809b2d6451eb84fa024ff88e917`. Both repos had no open PR at start. This Healthcare head includes one preceding Fabric-only commit beyond the handoff baseline. All source Blob SHAs below match the recorded 2026-10-19 94/94 task003 historical inventory. Frozen links are recovery-only; the previously verified Healthcare-Specs source snapshot is independent.

| Removed one-time installer (under `local-data-platform/scripts/task003/`) | Frozen Git Blob | Immutable source | Retained formal products |
| --- | --- | --- | ---: |
| `05g2a-prepare-visit-processed-prefix-guard.sh` | `35317797b8d63dd14b928cad698eefa9eeed707b` | [frozen Git](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/e3ce9f2e5adbfd22f25e3bfca1b2ae892f4f086a/local-data-platform/scripts/task003/05g2a-prepare-visit-processed-prefix-guard.sh) | 3/3 |
| `05g2b-prepare-visit-processed-remote.sh` | `b576500564d168d90d308472baa2103a0375b466` | [frozen Git](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/e3ce9f2e5adbfd22f25e3bfca1b2ae892f4f086a/local-data-platform/scripts/task003/05g2b-prepare-visit-processed-remote.sh) | 1/1 |
| `05g2c1-prepare-visit-processed-write-intent.sh` | `aa3b0f4fab9866de8c41bf6b70ca2c1e0eb11169` | [frozen Git](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/e3ce9f2e5adbfd22f25e3bfca1b2ae892f4f086a/local-data-platform/scripts/task003/05g2c1-prepare-visit-processed-write-intent.sh) | 4/4 |
| `05g2c2b-prepare-visit-processed-writer-core.sh` | `d7f8b4d77591cbacb6e807fe8ce1b017666a2103` | [frozen Git](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/e3ce9f2e5adbfd22f25e3bfca1b2ae892f4f086a/local-data-platform/scripts/task003/05g2c2b-prepare-visit-processed-writer-core.sh) | 2/2 |
| `05g2c2c1-prepare-visit-processed-spark-driver.sh` | `c2b710969077b7f76209a6d20ce3bab48ea825bb` | [frozen Git](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/e3ce9f2e5adbfd22f25e3bfca1b2ae892f4f086a/local-data-platform/scripts/task003/05g2c2c1-prepare-visit-processed-spark-driver.sh) | 2/2 |

## Literal heredoc output comparison — 12/12 EXACT MATCH / KEEP

Read each original Shell from the frozen Main, parse literal `cat > "$STAGE/<path>" <<'<DELIMITER>'` heredocs, and independently fetch its generated formal file at that same Main. All 12 generated UTF-8 contents matched the whole current file byte-for-byte, including terminator newline. No installer was executed or allowed to rewrite the tracked sources.

**`05g2a-prepare-visit-processed-prefix-guard.sh`**
- `local-data-platform/apps/task003/inspect_visit_processed_prefix.py` — MATCH / KEEP
- `local-data-platform/tests/task003/test_visit_processed_prefix_guard.py` — MATCH / KEEP
- `local-data-platform/scripts/task003/05g2a-inspect-visit-processed-prefix.sh` — MATCH / KEEP

**`05g2b-prepare-visit-processed-remote.sh`**
- `local-data-platform/scripts/task003/05g2b-inspect-visit-processed-remote.sh` — MATCH / KEEP

**`05g2c1-prepare-visit-processed-write-intent.sh`**
- `local-data-platform/spark/contracts/processed/visit-writer-safety-v1.json` — MATCH / KEEP
- `local-data-platform/apps/task003/prepare_visit_processed_write_intent.py` — MATCH / KEEP
- `local-data-platform/tests/task003/test_visit_processed_write_intent.py` — MATCH / KEEP
- `local-data-platform/scripts/task003/05g2c1-verify-visit-processed-write-intent.sh` — MATCH / KEEP

**`05g2c2b-prepare-visit-processed-writer-core.sh`**
- `local-data-platform/spark/apps/visit/processed_visit_writer_core.py` — MATCH / KEEP
- `local-data-platform/tests/task003/test_processed_visit_writer_core.py` — MATCH / KEEP

**`05g2c2c1-prepare-visit-processed-spark-driver.sh`**
- `local-data-platform/spark/apps/visit/run_visit_processed_writer.py` — MATCH / KEEP
- `local-data-platform/tests/task003/test_visit_processed_driver.py` — MATCH / KEEP

## Current consumer closure checked (bounded, not global proof)

- Healthcare 64/64 high-priority source consumers checked at frozen Main: 27 GitHub Actions workflow YAML, 15 Airflow DAGs, 8 Dockerfiles and 14 TASK004 Shell scripts. Exact basename external references to retired installers: 0.
- `local-data-platform/scripts/task003/` current 80/80 Shell files checked. Exactly the five installers mentioned themselves; none of the other 75 TASK003 Shells contained their exact names.
- Self-Runner 16/16 related Workflow YAML files checked against Main `c9bb734517a0e809b2d6451eb84fa024ff88e917`; exact basename references: 0. This does NOT prove absence of computed/dynamic paths, unscanned modules or third-party external consumers.
- The previous real NEW_ONLY batch success [Self-Runner #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433) remains regression evidence for the NEW_ONLY pathway, not an assertion that historical fixed-Batch installers were replayed.
- Retain every formal processed prefix guard, remote inspector, Write Intent guard, writer core/driver, unit test, all existing Docker COPY sources, Writer Fencing and PostgreSQL recovery. `06c4e-prepare-committed-cdm-visit-materialization.sh` stays HOLD because dynamic contract completeness was not demonstrated.
- CODE maps updated: Landing TASK003 42 -> 39; Spark TASK003 11 -> 9. Entire TASK003 Shell count: 80 -> 75. Preserve all five immutable restoration links in CODE Maps and here.

## Merge gate / known limits

Only merge after all applicable actual GitHub Actions checks on the **final PR head** are successful (Docs Links, Component Naming, OpenSpec, provenance/source tests, DagBag, isolated image builds and NEW_ONLY/CDM Writer tests as triggered). Do not substitute old CI from PR #319. No changes or commands on Kubernetes, PG, S3, Airflow deployment, Fabric, GHCR; no historic batch replay. Tasks 4.1, 4.8, 4.9, 4.10 and closure Section 5 stay OPEN.

# Local DP TASK003 one-pass consolidated retirement evidence — 2026-10-20

> Change `relocate-local-data-platform`, Task 4.9 PARTIAL. **Implementation branch only / candidate runtime acceptance still pending**. This file logs the actual 26-way Runner classification; it is NOT a declaration that post-delete E2E has passed.

## Source and coverage

- Frozen Healthcare Main: `db4242dcbc752a021456240e98210ba595161510`; starting Self-Runner Main: `b5f46802ec63c8da6d047d7420dbbd7f5a292ace`. Exact PR audit run [#39479335467](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39479335467) SUCCESS on the Self-Runner pull request #166's ephemeral merge commit `a033af0f2008b654829c22c0ba5a233fc16ad340`; the run checked the exact Healthcare frozen SHA.
- Audit source: [Self-Runner PR #166](https://github.com/JohnZhang-DataForge/Self-Runner/pull/166), `scripts/ci/local_dp_consolidated_audit.py`. Its 14-day `local-dp-consolidated-audit` Artifact contains `matrix.json`, `matrix.tsv`, `summary.md`: each candidate's original Git Blob SHA, precise formal generated outputs, all exact source/config basename consumers, status and immutable Git recovery links.
- Actual scanned tracked source/config files: **818** across Healthcare and Self-Runner. Original frozen TASK003 candidate set 51, previously deleted 25, still present 26. Classified **9 DELETE_CANDIDATE + 17 HOLD**, with **19/19 official generated outputs byte-identical** for the 9 proposed retirements. These are high-confidence one-time installation/generation shells, not the generated runners. External manual operators and truly dynamic imports cannot be proven absent solely by source scanning.
- Historical TASK003 Shells on Main before this candidate batch: **69**. Candidate branch after the 9-file retirement: **60**. All scripts that perform Writer reservation/launch/observation, DQ/Manifest publish, live verification, rollback, PG recovery and other standalone operations are preserved. `local-data-platform/` remains the unique business source root.

## Exact immutable source recovery / retained products

| Proposed retired one-time installer | Frozen Git blob SHA | Byte-for-byte retained outputs | Read-only recovery |
| --- | --- | --- | --- |
| `05f-prepare-visit-candidate-mapping.sh` | `59ae696371b076a4be7b699f8798cdf3d5c64615` | 4/4 EXACT | [05f-prepare-visit-candidate-mapping.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05f-prepare-visit-candidate-mapping.sh) |
| `05f2a-prepare-visit-candidate-driver.sh` | `96484934837c94d433c92a1e1bb5d3a8cce4ebd5` | 2/2 EXACT | [05f2a-prepare-visit-candidate-driver.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05f2a-prepare-visit-candidate-driver.sh) |
| `05g1-prepare-visit-processed-plan.sh` | `bf89106c3280548237ee77fe384927adad895a71` | 4/4 EXACT | [05g1-prepare-visit-processed-plan.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05g1-prepare-visit-processed-plan.sh) |
| `05g2c2a-prepare-writer-reservation-source.sh` | `32437fd62a9dd2aa14def3c1d80d4bd586828a17` | 3/3 EXACT | [05g2c2a-prepare-writer-reservation-source.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05g2c2a-prepare-writer-reservation-source.sh) |
| `05g2c2c3c2-prepare-atomic-writer-launcher.sh` | `223261d65813b38d60d36c9d844765e66a1bd6f2` | 1/1 EXACT | [05g2c2c3c2-prepare-atomic-writer-launcher.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05g2c2c3c2-prepare-atomic-writer-launcher.sh) |
| `05g2c2c3d2b1-prepare-persisted-validator-source.sh` | `75226f50164852399539a5bb21fef6b600235b74` | 2/2 EXACT | [05g2c2c3d2b1-prepare-persisted-validator-source.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05g2c2c3d2b1-prepare-persisted-validator-source.sh) |
| `05g2c2c3d2b2-prepare-independent-readback.sh` | `a9a4c3b39e7328f303e6a487f3dc8f5c3314f881` | 1/1 EXACT | [05g2c2c3d2b2-prepare-independent-readback.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05g2c2c3d2b2-prepare-independent-readback.sh) |
| `05g3b2-prepare-processed-dq-publication.sh` | `07391c5e4d783bb1d2571748c7f8ec35d3bfc803` | 1/1 EXACT | [05g3b2-prepare-processed-dq-publication.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05g3b2-prepare-processed-dq-publication.sh) |
| `05g4c2-prepare-processed-manifest-publication.sh` | `759059c07ab8b769c518ed0a95da2e3e8f3c6d17` | 1/1 EXACT | [05g4c2-prepare-processed-manifest-publication.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05g4c2-prepare-processed-manifest-publication.sh) |

All 19 formal output paths are unchanged in the candidate branch:
**05f-prepare-visit-candidate-mapping.sh**
- KEEP `local-data-platform/spark/contracts/omop/visit-candidate-v1.json`
- KEEP `local-data-platform/apps/task003/visit_candidate_rules.py`
- KEEP `local-data-platform/spark/apps/visit/map_encounter_to_visit_candidate.py`
- KEEP `local-data-platform/tests/task003/test_visit_candidate_rules.py`
**05f2a-prepare-visit-candidate-driver.sh**
- KEEP `local-data-platform/spark/apps/visit/validate_visit_candidate_preflight.py`
- KEEP `local-data-platform/tests/task003/test_visit_candidate_preflight_static.py`
**05g1-prepare-visit-processed-plan.sh**
- KEEP `local-data-platform/spark/contracts/processed/visit-candidate-publication-v1.json`
- KEEP `local-data-platform/apps/task003/plan_visit_processed.py`
- KEEP `local-data-platform/tests/task003/test_visit_processed_plan.py`
- KEEP `local-data-platform/scripts/task003/05g1-plan-visit-processed.sh`
**05g2c2a-prepare-writer-reservation-source.sh**
- KEEP `local-data-platform/apps/task003/build_visit_writer_reservation.py`
- KEEP `local-data-platform/tests/task003/test_visit_writer_reservation.py`
- KEEP `local-data-platform/scripts/task003/05g2c2a-prepare-writer-reservation.sh`
**05g2c2c3c2-prepare-atomic-writer-launcher.sh**
- KEEP `local-data-platform/scripts/task003/05g2c2c3c2-launch-visit-processed-writer.sh`
**05g2c2c3d2b1-prepare-persisted-validator-source.sh**
- KEEP `local-data-platform/spark/apps/visit/validate_persisted_visit_candidate.py`
- KEEP `local-data-platform/tests/task003/test_persisted_visit_candidate_validator.py`
**05g2c2c3d2b2-prepare-independent-readback.sh**
- KEEP `local-data-platform/scripts/task003/05g2c2c3d2b2-run-independent-readback.sh`
**05g3b2-prepare-processed-dq-publication.sh**
- KEEP `local-data-platform/scripts/task003/05g3b2-publish-processed-dq.sh`
**05g4c2-prepare-processed-manifest-publication.sh**
- KEEP `local-data-platform/scripts/task003/05g4c2-publish-processed-manifest.sh`

## 17 explicit HOLD (do not delete)

- **HOLD** `local-data-platform/scripts/task003/04-prepare-canonical-encounter-publish.sh`
- **HOLD** `local-data-platform/scripts/task003/05-prepare-visit-omop.sh`
- **HOLD** `local-data-platform/scripts/task003/05b-prepare-visit-db-baseline.sh`
- **HOLD** `local-data-platform/scripts/task003/05c-prepare-visit-id-map.sh`
- **HOLD** `local-data-platform/scripts/task003/05d-prepare-visit-remote-metadata.sh`
- **HOLD** `local-data-platform/scripts/task003/05e-prepare-visit-raw.sh`
- **HOLD** `local-data-platform/scripts/task003/05f2b-prepare-visit-candidate-runtime.sh`
- **HOLD** `local-data-platform/scripts/task003/05g2c2c2a-prepare-runtime-readonly.sh`
- **HOLD** `local-data-platform/scripts/task003/05g2c2c3a-acquire-writer-reservation.sh`
- **HOLD** `local-data-platform/scripts/task003/05g2c2c3c2-launch-visit-processed-writer.sh`
- **HOLD** `local-data-platform/scripts/task003/05g2c2c3d1-observe-visit-processed-writer.sh`
- **HOLD** `local-data-platform/scripts/task003/05g3a-build-processed-dq.sh`
- **HOLD** `local-data-platform/scripts/task003/05g4a-build-processed-manifest.sh`
- **HOLD** `local-data-platform/scripts/task003/05g4c1-prepare-processed-manifest-publisher-source.sh`
- **HOLD** `local-data-platform/scripts/task003/06b1-build-visit-id-mutation-contract.sh`
- **HOLD** `local-data-platform/scripts/task003/06b4a-prepare-visit-id-allocation-rehearsal.sh`
- **HOLD** `local-data-platform/scripts/task003/06c4e-prepare-committed-cdm-visit-materialization.sh`

Notable reasons: `05f2b` contains a helper `PY_TEMPLATE` that dynamically writes a staged YAML/contract derivative; `06b4a` produced 4/5 exact frozen outputs (the fifth is not byte-identical); `05g4c1` is still directly named inside two active Manifest publication `git diff --quiet` guards; `06c4e` still has dynamic CDM Contract generation and a caller; `05g2c2c3a`/`05g2c2c3c2` are actual reservation/launch operations rather than throwaway installers. Other HOLD candidates have unproven standalone behavior, historical operator value, or incomplete static generation proof. No 'no-grep-hit implies safe to delete' inference is made.

## Scope and minimum merge gates

- Remove only the nine frozen historical generator installers, from an explicit Git allowlist; update Landing CODE Map **33→27** and Spark CODE Map **9→6** with immutable Git links. Do NOT delete 19 retained outputs, Contracts, DAGs, tests, actual Writer launch/rollback scripts, images, Dockerfiles, Spark Applications, active manifests, or unrelated Fabric/Portal code.
- GitHub final-PR-HEAD CI: OpenSpec Change Gate, Static Validation, Documentation Links, Naming, Airflow DagBag + Source/Provenance Gates, isolated Docker builds, NEW_ONLY Writer and CDM Reader smoke; require all applicable PASS.
- [Prior postmove real E2E #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433) proved the old frozen SHA only. The new Main-before-deletion fresh-batch E2E and the candidate-ref SHA-isolated E2E are independent, still to be recorded.
- **Fail closed on provenance**: current shared Airflow GitSync tracking Main cannot serve as proof of an unmerged PR branch. Verify a candidate-specific isolated DAG/source checkout, exact Spark driver module source and image digest (not inherited old Main tags), independent PG/S3 readback, and same-Batch idempotency SKIP. If this cannot be arranged, hold the PR without merging or falsely claiming E2E.
- No historical committed Batch replay, no Azure/Fabric chargeable Apply, no removal of valid unit/Contract tests. Any issues require bounded fixes and re-run the final HEAD; HOLD is a valid safe outcome. Keep Tasks 4.1 / 4.7 / 4.8 / 4.9 / 4.10 / 5 OPEN until proven.

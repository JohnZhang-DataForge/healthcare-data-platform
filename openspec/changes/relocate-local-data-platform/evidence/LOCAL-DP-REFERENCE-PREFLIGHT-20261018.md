# Local DP — reference preflight and cleanup blockers (PARTIAL audit)

> **2026-10-18 · PINNED STATIC CHECK, NOT RUNTIME EVIDENCE.** Task 4.1 is **not completed**. This is the first read-only pass, not permission to prune 118 Shells, remove tests, dispatch Self-Runner or touch the shared K8s/PG/S3/Airflow resources.

## Baselines and coverage

- Healthcare Main: `52237e773941def7625de72c6cecb2533f11e5d8`, Git Tree enumeration non-truncated: **393** tracked local files; the companion [393-row file matrix](LOCAL-DP-FILE-INVENTORY-20261018.md) lists exact paths and Blob SHA, with deletion HOLD on **every** row.
- Fixed physical move: [PR #225](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/225), Main `377df7c9fae770cde985f6e7bcbc47d40ecfa355`. GitHub compare `377df7c9..52237e773`: 13 commits, 60 changed paths, **0 local-data-platform paths changed**. Historical independent [Healthcare-Specs 393-file backup](https://github.com/JohnZhang-DataForge/Healthcare-Specs/pull/2) is therefore still the matching pre-move content baseline as far as these Git diffs establish; a deletion PR must still pin its **own current SHA** and restore verification, especially if subsequent changes occur.
- Inspected all **8** tracked `local-data-platform/images/*/Dockerfile` files for directly named COPY sources (52 distinct tracked file inputs); review is not a successful Docker build and does not expose all source imports.
- Inspected the **5** core `build-*.yml` GitHub workflows, 10 historical `task004-*.yml` workflow source/check rules, and **8 sampled** Self-Runner workflows at pinned `ffd0eccecbf0148183b956e6e4416d4b8d99002b`. The other workflows and dynamic inputs remain to be audited before completing 4.1.
- `CODE.md` cross-reference coverage across the 5 local component maps + Developer map: 298 files mentioned in exactly one map, 5 mentioned by more than one, 90 not individually mentioned. Almost all unmapped entries are tests; **lack of an individual CODE.md link is not proof of dead code**.

## Confirmed source-path incompatibilities (present at pinned Main)

All five current `build-*.yml` files use `context: .`, but their `file:` references and test paths expect vanished root-level `images/`, `apps/`, or `tests/` rather than `local-data-platform/`. The tree contains the new prefix and has no old root-level business sources. These are **static path mismatches**, not evidence that these specific workflows were recently executed and failed.

| Workflow | Confirmed stale path examples | Why it matters / status |
| --- | --- | --- |
| [.github/workflows/build-landing-claim-image.yml](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/52237e773941def7625de72c6cecb2533f11e5d8/.github/workflows/build-landing-claim-image.yml) | `tests/landing_claim`, `apps/landing_claim`, `file: images/landing-claim-runtime/Dockerfile`; `context: .` | Source tests and Dockerfile path incorrect on current HEAD; `push.paths` still monitors old prefixes |
| [.github/workflows/build-landing-discovery-image.yml](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/52237e773941def7625de72c6cecb2533f11e5d8/.github/workflows/build-landing-discovery-image.yml) | `tests/landing_discovery`, `apps/landing_discovery`, `file: images/landing-discovery-runtime/Dockerfile` | Old files are absent from root; `push.paths` not aligned |
| [.github/workflows/build-new-only-omop-writer.yml](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/52237e773941def7625de72c6cecb2533f11e5d8/.github/workflows/build-new-only-omop-writer.yml) | `apps/omop_writer/new_only_airflow_writer.py`, `tests/omop_writer`, `file: images/new-only-omop-writer/Dockerfile` | Old branch-specific trigger: **not** automatically presumed to be a maintained Main auto-build; review activation separately |
| [.github/workflows/build-synthea-image.yml](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/52237e773941def7625de72c6cecb2533f11e5d8/.github/workflows/build-synthea-image.yml) | `file: ./images/synthea/Dockerfile`, `context: .`; historical `images/synthea/**` trigger | Build context/file combination must be corrected; no GHCR publish was attempted |
| [.github/workflows/build-task004-runtime-image.yml](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/52237e773941def7625de72c6cecb2533f11e5d8/.github/workflows/build-task004-runtime-image.yml) | `scripts/task004/06a-prepare-unified-runtime-image.sh`, `spark/apps/task004/`, `tests/task004`, `file: ./images/task004-runtime/Dockerfile` | This workflow **regenerates** Dockerfile/entrypoint/workflow/tests into a temporary root and `cmp`s them; changing only the Dockerfile would fail or be overwritten upon regeneration. Fix source generator + generated output + tests together |

**Direction for Task 4.3**: after evaluating each image's external inputs, prefer `local-data-platform/` as Docker **build context**, with the build action's `file:` set to the appropriate new path; test correct path semantics. Keep container `RUNTIME_ROOT` unchanged unless a separate verified need arises. Preserve stable GHCR digest, DAG ID, Batch/Manifest/Claim/Writer identities. No whole-repo string replacement.

## Historical GitHub Workflow paths need classification, not blind repair

The reviewed `task004-airflow-step02-source.yml`, `task004-airflow-step03b-source.yml`, `task004-airflow-step03c-source.yml`, `task004-airflow-step03e-date-source.yml`, `task004-airflow-step03e-main-runtime-pin.yml`, `task004-airflow-step03e-runtime-report.yml`, `task004-cdm-pg-read-publish.yml`, `task004-cdm-rollback-image.yml`, `task004-s3-writer-rollback-image.yml` and `task004-step04f-cdm-ghcr-publish.yml` contain root-relative `airflow/`, `scripts/`, `tests/`, `images/` or `apps/` paths on the pinned Main.

Their `on.branches` are often **frozen feature/* names**; some also perform publishing rather than read-only checks. **Do not** retarget or re-enable all of them automatically. For each workflow, record whether it is a live maintained entrypoint, a historical frozen-ref rehearsal, or a candidate for retirement. Re-enable/publish on Main only through reviewed scope and applicable permissions.

## External Self-Runner findings (sample, not exhaustive)

Self-Runner tree SHA `ffd0eccecbf0148183b956e6e4416d4b8d99002b`. Each example below is an actual filename from the connected private repository, but whether it is an ongoing supported entrypoint depends on its `checkout.ref` / request schema, not merely the name.

| Workflow | Example observed source path | Triage |
| --- | --- | --- |
| [.github/workflows/new-only-v2-airflow-spark-live.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/new-only-v2-airflow-spark-live.yml) | `healthcare/airflow/dags/$FILE` | Check selected Healthcare ref first: old pinned SHA may legitimately contain old tree |
| [.github/workflows/task004-newonly-airflow-spark-handoff.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/task004-newonly-airflow-spark-handoff.yml) | `healthcare/airflow/dags/$FILE` | Same distinction; cannot silently follow latest Main |
| [.github/workflows/landing-batch-discovery-readonly.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/landing-batch-discovery-readonly.yml) | `healthcare/apps/landing_discovery/scan_ready_batches.py`, `healthcare/apps/task004/resolve_verified_landing_file.py` | Potential mismatch when operating against new Main; read-only **label** does not prove no K8s writes |
| [.github/workflows/task004-airflow-step03e-live.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/task004-airflow-step03e-live.yml) | `healthcare/airflow/dags/task004_processing_pipeline.py`, `PROJECT_ROOT=.../healthcare` | Has runtime path and target SHA checks; classify old fixed run vs maintained path before changing |
| [.github/workflows/task004-first-new-only-business-commit.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/task004-first-new-only-business-commit.yml) | `healthcare/apps/omop_writer`, `healthcare/airflow/dags` | **Actual business writer workflow**; never dispatch/replay merely to probe paths |
| [.github/workflows/omop-writer-precommit-readonly.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/omop-writer-precommit-readonly.yml) | `healthcare/apps/omop_writer/precommit_gate.py` | Check pinned source and ConfigMap/Pod side effects separately |
| [.github/workflows/synthea-new-only-run-new-request.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/synthea-new-only-run-new-request.yml) | Fixed-checkout controlled Synthea path; creates in-cluster Secret/Job on execution | Do not treat presence as proof of current-main acceptance |
| [.github/workflows/healthcare-openspec-pr-handoff.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/healthcare-openspec-pr-handoff.yml) | Uses exact `target_sha` and only static checkout/validation | Governance workflow appears intentionally SHA-bound; not a business runtime validation |

## Cleanup review priority and safety

- **Priority 1 — BLOCK DELETE**: eight Dockerfiles and 52 directly referenced tracked source inputs; active DAG and Writer/Claim/Fencing source; effective Contract, SQL, CI and safety tests. At least five `scripts/task004/` files are Docker COPY inputs, so 'task script' does not imply 'historical-only'.
- **Priority 2 — REVIEW CANDIDATES**: other task-numbered Shells and one-time generators; there are 123 files under `scripts/`, **118** of them not found as direct inputs of the eight tracked Dockerfile source `COPY`s. **118 is not an approved deletion count**, because Workflow, Shell-to-Shell, generated-image and dynamic references remain unverified.
- **Priority 3 — TEST VALUE REVIEW**: 105 test files, of which 71 live under `tests/task001–task004/` by pathname. Preserve meaningful regression/negative/fencing tests even if filenames are historical; selectively migrate assertions before removing duplicate tests.
- **Priority 4 — UNKNOWN / HOLD**: all files without enough direct/indirect-call and deployment evidence. Do not use absence of a CODE.md entry or absent `git grep` as a deletion proof.
- For each removal obtain the exact current blob and matching immutable restore commit; check CODE ownership, link updates, build/CI impact, and any generator that can recreate old paths. The 393-file original backup is a historical **Git** backup, not a database/object-store/cluster backup.

## Exact next read-only substep

**Continue Task 4.1 (still unchecked):** perform complete Healthcare **and** Self-Runner consumer inventory (including dynamic imports, historical pins vs maintained workflows, Airflow GitSync, SparkApplication paths, generator outputs, Python tests), and convert the preliminary 393-row HOLD matrix to evidence-backed A/B/C/D/E dispositions. Then do Task 4.8 independent recovery/backup review. Do not start 4.9 deletion, 4.2 fixes, or shared Runtime solely because this first-pass report exists.

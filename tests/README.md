# Tests — contracts, transformations and runtime regression

[← Repository overview](../README.md) · [CI workflows](../.github/README.md) · [Current task status](../docs/tasks/TASK-STATUS.md)

This directory contains Python unit tests, static source-contract checks and regression assertions grouped by **business capability** and historical implementation milestones.

## Test areas

| Directory | Focus |
| --- | --- |
| [`landing_claim/`](landing_claim/) | Claim ledger, identity and lease/fencing behavior |
| [`landing_discovery/`](landing_discovery/) | Immutable READY discovery, Airflow routing and Spark/Writer DAG gates |
| [`omop_writer/`](omop_writer/) | Atomic NEW_ONLY Writer contract, Plan, source adapter, fencing and idempotency safeguards |
| [`synthea_new_only/`](synthea_new_only/) | Producer identity, source contract, publication and replay policy |
| [`task001/`](task001/) | Whole-batch intake and manifest gates |
| [`task002/`](task002/) | Canonical Patient/Person mapping checks |
| [`task003/`](task003/) | Encounter/Visit adapter, publication, mapping and materialization checks |
| [`task004/`](task004/) | Earlier Airflow/Spark/source/PG runtime and integration contract regressions |

## Local offline test examples

From repository root, with the required Python dependencies installed:

```bash
python3 -m unittest discover -s tests/omop_writer -p 'test_*.py' -v
python3 -m unittest discover -s tests/landing_discovery -p 'test_*.py' -v
python3 -m unittest discover -s tests/synthea_new_only -p 'test_*.py' -v
```

These are examples, **not proof** that all tests will pass without the appropriate image-specific dependencies. Some tests check static source or require a prepared environment; do not run Kubernetes/PG integration scripts under the assumption that they are offline.

## Acceptance is more than unit-test green

1. Verify static contracts and image packaging.
2. Build/pin immutable container digests.
3. Validate real Airflow and Kubernetes runs with their exact batch identity.
4. Confirm durable PostgreSQL Claim/Stage/Checkpoint and OMOP row state independently.
5. For a committed batch, prove re-consumption takes the SKIP path with no Spark/Writer and unchanged durable counts.

The actual third-batch end-to-end and replay evidence is linked from [TASK004 Final Acceptance](../docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md). Tests in this directory protect a bounded contract and cannot substitute for live execution.

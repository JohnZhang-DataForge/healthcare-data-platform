# Shared Data Engine — scoped Agent instructions

These instructions apply only within `shared-data-engine/`. Read [root AGENTS](../AGENTS.md), the relevant [Active OpenSpec](../openspec/changes/), and the [Shared Engine ownership rules](../documents/engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) before editing. This file defines stable boundaries, **not package versions or current progress**.

## Component boundaries

- **Single package:** `src/healthcare_data_engine/` is the sole platform-neutral, installable Python namespace. Do not create a second Fabric I/O Wheel or copy shared algorithms into platform code.
- **Allowed:** deterministic Python/PySpark FHIR/source adapters, Canonical validation, typed Quality, reconciliation, OMOP Candidate Mapping, and pure identity/planning decisions. Explicit caller-provided input and output, no import-time side effects.
- **Forbidden:** Azure Blob/OneLake/S3/Delta/PostgreSQL/Warehouse physical I/O, network or cloud SDK, Airflow DAG, Fabric Notebook/Pipeline, K8s/Terraform, SparkSession construction in library code, credentials, clinical data, actual writes or deployment/monitoring side effects. Platforms own runtime operations.
- **Dependencies:** shared modules must not import Local DP runtime or Fabric Native Item modules, provider Writers, or form circular dependencies. Do not embed source-specific parsing into OMOP mappers.
- **Contracts:** Local `local-data-platform/spark/contracts/` is authoritative until a separately approved migration; pin original bytes/hashes, do not copy a competing schema or fabricate missing clinical values.
- **Changes:** before coding, identify owner module, API/Contract, allowed imports, relevant tests and OpenSpec task. Keep historical Local IDs/behavior unless an explicit, independently verified migration authorizes a change.

## Mandatory routing

- **Architecture and source owner:** [shared-engine README](../documents/systems/data-platform/shared-engine/README.md) and [CODE map](../documents/systems/data-platform/shared-engine/CODE.md). Update CODE.md in the same PR whenever source ownership or paths change.
- **Build/test procedures:** [BUILD-AND-TEST](../documents/systems/data-platform/shared-engine/BUILD-AND-TEST.md). Existing `tests/` remain frozen legacy paths; **new tests** go to `.github/quality/tests/shared-data-engine/<component>/` and fixtures to `.github/quality/fixtures/`.
- **Progress and acceptance:** Active OpenSpec `tasks.md`, versioned source/CI evidence, and the actual Fabric Environment readback. No duplicate CURRENT/NEXT, releases, completed-claims or status diary here.
- **Safety:** root [Safe Operations](../documents/engineering/operations/SAFE-OPERATIONS.md) applies; no live Fabric, PG, Blob, K8s or paid-resource action without separate authorization.

# Scoped Agent rules — shared-data-engine/

**MANDATORY for any Agent editing files below this directory.** Read the repository root [AGENTS.md](../AGENTS.md) and the authoritative [Shared Engine structure and ownership rules](../documents/engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) first. This directory is a **versioned, platform-neutral business transformation package**, not another Airflow/Fabric runtime.

## Absolute boundaries

- **Owned here:** source and entity adapters (CSV, FHIR R4, HL7 v2), common Canonical Patient/Encounter contracts and normalization, pure PySpark DataFrame OMOP candidate mappers, versioned identity planning, quality and reconciliation, frozen synthetic tests.
- **Forbidden here:** Fabric/OneLake/Azure Blob I/O and SDKs, SeaweedFS/S3 I/O, network access and authentication, Airflow DAG or Fabric Notebook/Pipeline, PostgreSQL/Warehouse/Delta *physical* writer and commits, K8s/Terraform, Secrets, real patient data, deployment-specific monitoring/exporter side effects.
- **Allowed compute:** deterministic Python/PySpark transformations; DataFrame arguments in, DataFrame + typed plan/quality results out. **No** Spark Session creation, environment reads, network calls or file access at import time. Caller/platform owns I/O and side effects.
- **Dependency direction:** source adapters → canonical/models/quality; OMOP mappers → canonical/identity/quality; platform runtimes → shared public API. **Never** import `healthcare_fabric`, local runtime modules or cloud/provider Writers in shared. No circular imports and no source-specific parse dependency in OMOP mappers.
- **Contracts:** Local `local-data-platform/spark/contracts/` remains the authoritative existing source until an approved standalone Contract-migration PR. Pin exact versions/hashes; no manually copied divergent schemas. Fail/quarantine optional or invalid clinical fields; do not fabricate medical defaults.
- **Naming:** `shared-data-engine/src/healthcare_data_engine/` is the sole Python namespace; name modules by domain/function, not task/step/hospital/sprint. Do not create redundant bronze/silver/gold business-source trees or entire ETL copies per hospital.
- **Migration:** leave established Local runtime/imports/IDs untouched until one module passes offline contract, negative, idempotence and Spark cross-runtime tests; release each platform's wheel dependency independently.
- **Review gate:** Before edits, identify owning module, input/output Contract, allowed imports, test cases and OpenSpec task. Same PR must maintain `documents/systems/data-platform/shared-engine/CODE.md` after any new source files. New source requires a static import/ownership guard in CI; do not assume existing CODE-map covers this new root.
- **Safety:** No runtime deployments, actual clinical data, Azure/K8s/PG/Blob writes or paid resources without separate explicit authorization. Docs ≠ implementation.

Current state: **only scoped directory policy is created**, no Python implementation or duplicate Contract files exist here.

# Clean Slate Component-first Local Data Platform Migration

## ADDED Requirements

### Requirement: Maintained implementation identifiers follow component responsibilities

After migration, active Local DP application modules, tests, Shell entry points, Docker image sources/packages, Kubernetes workload identities, Airflow DAG IDs, SQL business object names and automation consumers SHALL use functional component naming rather than implementation-phase identifiers `task001`–`task004` or `stepNNN`. Every active consumer in Healthcare and Self-Runner MUST reference the corresponding new identifier. Existing framework keys such as Airflow `task_id`, historic Git evidence and archived run logs SHALL remain valid and SHALL NOT be treated as forbidden legacy identifiers.

#### Scenario: New image and DAG import only renamed modules

- **GIVEN** the approved old→new inventory is complete
- **WHEN** all eight current business images build from clean sources and DAGs parse
- **THEN** module imports, ENTRYPOINT, COPY, DAG references and both repositories' active workflows resolve new identifiers without falling back to old Task/Step runtime paths

#### Scenario: Legacy API field is not erased

- **GIVEN** Airflow operators still require `task_id`
- **WHEN** the rename checker inspects active DAG definitions
- **THEN** it accepts valid `task_id` keys and rejects legacy numeric project-stage names used as new DAG or module identities

### Requirement: Fresh business state is reproducibly bootstrapped

The migrated platform SHALL initialize its new OMOP/ETL business schema, ledger/claim/checkpoint/id-map objects, sequences, required database roles and grants from canonical source without importing old synthetic business rows or depending on old `etl.task004_*` interfaces. Initialization MUST produce correct table/function relationships before Writer activation. Infrastructure services and non-business system metadata SHALL remain in place.

#### Scenario: Empty business database is initialized

- **GIVEN** an approved isolated blank development business database with working infrastructure
- **WHEN** reviewed bootstrap DDL/configuration is applied
- **THEN** new business schemas and access permissions exist, legacy synthetic rows are absent, and the Writer can perform its authorization checks against the new ledger without a compatibility view

#### Scenario: Bootstrap is incomplete

- **GIVEN** a missing grant, sequence, table or Fencing function in the new business state
- **WHEN** the Writer attempts admission
- **THEN** it fails closed without a partial OMOP COMMIT

### Requirement: Old and new pipelines cannot both own the same batch or unisolated tables

The system MUST ensure the old DAG/Writer and renamed DAG/Writer do not simultaneously process the same Batch or write to unisolated OMOP/ETL business tables. New scheduled processing SHALL remain disabled until old scheduled consumers are stopped or full isolation is proven. DAG history identity migration is not required.

#### Scenario: Old Writer remains active

- **GIVEN** an old DagRun or Writer may still be committing in a shared target database
- **WHEN** activation of the new writer or old-state reset is requested
- **THEN** cutover is held until that work is resolved and exclusive ownership is independently verified

#### Scenario: Distinct DAG registration

- **GIVEN** a deployed new DAG uses a new functional DAG ID
- **WHEN** Airflow parses the updated GitSync source
- **THEN** it registers the new DAG independently without requiring a rename or import of the old DagRun history

### Requirement: New E2E preserves current business and transaction semantics

A newly generated unique Synthea Batch SHALL produce valid Landing Manifest and verified S3 payload, pass current exact-batch Airflow selection, Spark Person/Visit/reconciliation and atomic OMOP Writer, and be independently read back from the new business state. Repeating that same completed Batch MUST skip the Writer and cause zero database business-row changes. Existing immutable identity, Manifest SHA, failure guards, Native Race, Multi-Parquet, Claim and Fencing behavior MUST remain testable and must not be weakened by naming changes.

#### Scenario: Fresh batch commits and safely replays

- **GIVEN** a blank approved new business state and a fresh unique Synthea Batch
- **WHEN** the full new DAG, Spark and Writer pipeline runs and its batch is retriggered unchanged
- **THEN** the first run has a verified atomic COMMIT, independent CDM/ledger/FK/Manifest readback and the second run produces SKIP with zero PG delta

#### Scenario: Manifest identity mismatch

- **GIVEN** a Batch ID and a mismatching Manifest URI or SHA256
- **WHEN** a renamed Airflow consumer attempts processing
- **THEN** admission fails closed before any unauthorized Writer COMMIT

### Requirement: Legacy business state retirement is scoped and conditional

Legacy synthetic PostgreSQL business objects, old DAG metadata, S3 test objects, GitHub workflows, Kubernetes workload resources and GHCR packages MAY be removed only after new-state E2E acceptance, a fresh ownership/consumer audit and an exact deletion allowlist. The cleanup MUST NOT delete new business data, PostgreSQL instances, Airflow metadata database wholesale, SeaweedFS PVC/services, unrelated workloads, secrets, PG14/Marquez or Azure/Fabric/Portal resources. Historical Git/PR/Run evidence MUST remain retrievable.

#### Scenario: New system accepted and old state unused

- **GIVEN** the new two-batch E2E/Replay acceptance succeeded and all old resources are independently confirmed unreferenced
- **WHEN** the approved allowlist is executed
- **THEN** only enumerated old resources are removed and new-state readback, scheduling and idempotency remain valid

#### Scenario: Unknown ownership or active external consumer

- **GIVEN** an old image digest, S3 prefix, DAG or PostgreSQL object has an unresolved active consumer or ownership
- **WHEN** deletion is considered
- **THEN** that specific resource remains HOLD without obstructing unrelated proven-safe code renaming

### Requirement: Evidence distinguishes planned, built, deployed and live-verified states

The migration SHALL record immutable Healthcare/Self-Runner commit SHAs, exact PR CI results, renamed image Digest and parent-child lineage, GitSync/DAG ID, new Batch ID/Manifest SHA, independent S3/PG readback and post-cleanup verification before it is considered complete. A planning PR or static OpenSpec validation MUST NOT be reported as actual deployment or business E2E.

#### Scenario: Spec is approved but no runtime work is executed

- **GIVEN** this proposal/design/tasks/spec PR passes governance validation
- **WHEN** its implementation status is reported
- **THEN** the status remains PLANNED, and PostgreSQL/S3 writes, Airflow deployment and old-resource deletion are explicitly marked NOT EXECUTED

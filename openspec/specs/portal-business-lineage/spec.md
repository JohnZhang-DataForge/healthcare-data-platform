# Portal Business Lineage MVP

## Purpose

Define the accepted, LAN-only Healthcare Platform Portal business lineage MVP boundary: additive Airflow NEW_ONLY and Spark OpenLineage instrumentation, correct real Job/Run/Parent and S3 DatasetVersion identities, honest PG17 Writer commit evidence, and safe native Marquez Web readback. This specification does not implement public anonymous access or Azure/Fabric cross-platform presentation. Historical A4 unknown-job unique root cause is independently deferred; physical RDD Action START-only remains a disclosed Design A observability limitation rather than a repaired event lifecycle.

## Requirements

### Requirement: Observability remains additive to existing business contracts

The Portal integration SHALL preserve the active `new_only_omop_consumer` DAG ID, current Task/XCom contracts, legacy `task004` names, immutable Manifest checks, Claim/Fencing and Writer COMMIT authorization semantics. It MUST NOT require Local DP naming/structure migration to function.

#### Scenario: Portal is enabled for an existing new-only batch

- **GIVEN** the existing validated Person/Visit pipeline and valid immutable READY batch
- **WHEN** Portal instrumentation is activated
- **THEN** Airflow/Spark observability is added without changing business selection, computation, database writes or the Writer permission gate

#### Scenario: Instrumentation or metadata service fails

- **GIVEN** Marquez or its network endpoint is unreachable
- **WHEN** a real instrumented run executes
- **THEN** its error and any impact are observable; no Writer authorization, Manifest validation or Fencing check MAY be bypassed to claim a successful run

### Requirement: Portal health status comes from current read-only evidence

An online or deployed-health claim MUST be supported by an execution-scoped read-only Marquez API/Web, Kubernetes Endpoint/Service and PG14 metadata check. Historical screenshots, YAML and 2026-10-13/14 successful runs SHALL NOT be treated as proof of present availability.

#### Scenario: Historical deployment exists without a current query

- **GIVEN** old Marquez/PG14 validation records
- **WHEN** no current live inventory is available
- **THEN** the Portal status is reported as `LIVE_STATUS=UNKNOWN`, not HEALTHY

### Requirement: Real Airflow and Spark job/run lineage can be independently queried

Enabled business Airflow tasks and real SparkApplications SHALL emit verifiable OpenLineage Run events with stable Job/Run identities through the configured Provider/Listener. The integration MUST use emitted events, not synthetic successful JSON posts, to justify acceptance.

#### Scenario: Spark job finishes and lineage is received

- **GIVEN** one controlled SparkApplication with a known app name and run identity
- **WHEN** it reads real input and completes successfully
- **THEN** Marquez API records its successful Run under the correct Job instead of an unrelated `unknown` Job

#### Scenario: Airflow selective enable does not leak scope

- **GIVEN** business DAG opted into OpenLineage
- **WHEN** the corresponding Airflow run emits its events
- **THEN** expected DAG/Task Jobs and Runs can be read back, and unrelated DAG behavior remains unchanged

### Requirement: Dataset lineage represents actual S3 input and output

The Portal SHALL expose dataset-level lineage for the actual files/Parquet paths consumed and persisted by Spark Person/Visit processing. It MUST NOT equate a ConfigMap CSV read or an in-memory dataframe with successful production input/output lineage.

#### Scenario: Isolated Spark writes real output

- **GIVEN** a scoped isolated input and distinct persistent output
- **WHEN** an authorized Spark Smoke emits OpenLineage
- **THEN** Marquez shows a corresponding real input Dataset and output Dataset attached to the correct Job/Run

#### Scenario: Spark performs only in-memory work

- **GIVEN** a job only reads a fixture and computes in memory
- **WHEN** that job completes
- **THEN** Portal MUST NOT claim a persisted output Dataset or a complete business I/O lineage

### Requirement: Batch-level linkage distinguishes Spark completion from OMOP commit

The integration SHALL preserve a traceable linkage between immutable `source_system/batch_id/manifest_sha256`, Airflow DagRun, real Spark Jobs/Runs and corresponding Dataset paths. A `WRITER_COMMITTED` or `PG_READBACK_VERIFIED` status MUST come from the real Writer contract and/or independent read-only PG17 evidence, not mere Spark completion.

#### Scenario: Same batch succeeds then safely skips

- **GIVEN** a unique synthetic batch has completed a real Writer COMMIT
- **WHEN** an authorized same-batch replay safely SKIPs
- **THEN** the evidence shows the original verified COMMIT, replay SKIP, zero PG business delta and the correct associated lineage; no fabricated second COMMIT is reported

#### Scenario: Spark completes but writer is held

- **GIVEN** a valid Spark output but absent Writer authorization
- **WHEN** the Airflow writer gate remains closed
- **THEN** Portal MAY show Spark completion but MUST NOT assert OMOP COMMIT

### Requirement: Verification and public exposure remain bounded

The MVP SHALL use existing Marquez official Web and isolated PG14 metadata. It SHALL NOT expose an unauthenticated writable Marquez API via NodePort 30999, modify or reset existing PG14/PG17 business storage as part of health checks, or silently execute live Spark/Writer work from static validation.

#### Scenario: Only the proposal and tests are reviewed

- **GIVEN** static CI passes
- **WHEN** the Change is reported
- **THEN** state remains STATIC/PLANNED until separately authorized live checks and fresh-batch E2E independently pass

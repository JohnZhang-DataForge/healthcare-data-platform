## ADDED Requirements

### Requirement: Warehouse creation ownership

The system SHALL reuse the existing user-created `healthcare-omop` Warehouse `dw-omop-5.4`, without creating a second Warehouse or declaring an unmanaged resource as Terraform-managed.

#### Scenario: Warehouse is not visible

- **GIVEN** the configured Warehouse is not visible to the Self-Runner service principal
- **WHEN** the F0 probe runs
- **THEN** it MUST fail closed without Terraform apply, Warehouse creation or Capacity resume.

### Requirement: Read-only F0 SQL probe

The system SHALL authenticate with federated GitHub OIDC and use the Warehouse-specific SQL TDS token to execute only a fixed SELECT scoped to `dw-omop-5.4`.

#### Scenario: Valid connection

- **GIVEN** the existing Warehouse is running and the service principal is authorized
- **WHEN** the F0 probe connects
- **THEN** the observed DB_NAME MUST equal `dw-omop-5.4` and the run MUST record a SQL_SELECT_PASS without emitting tokens.

#### Scenario: Missing SQL permission or driver

- **GIVEN** Fabric REST metadata is accessible but SQL TDS permissions or local ODBC driver are missing
- **WHEN** the F0 probe executes
- **THEN** it MUST report a bounded HOLD reason and perform no DDL or DML.

### Requirement: CDM Gold ownership

The system SHALL maintain a formally versioned OHDSI CDM 5.4 schema inside the Fabric Warehouse, with stable Fabric-managed IDs and Vocabulary independent of Local PostgreSQL runtime.

#### Scenario: Candidate before Gold

- **GIVEN** Silver Delta is approved and Spark OMOP Candidate exists
- **WHEN** Warehouse schema, identity or vocabulary validation is incomplete
- **THEN** Candidate SHALL NOT be represented as committed Gold.

### Requirement: Replay-safe transaction

The system SHALL use a batch-fenced Warehouse transaction for ID-map, Person, Visit and ledger writes with independent DQ/readback.

#### Scenario: Identical approved batch replay

- **GIVEN** a prior accepted batch was durably committed
- **WHEN** the exact same batch is replayed
- **THEN** the writer SHALL leave Gold row identities unchanged and report a verified SKIP.

### Requirement: Stable Fabric-only clinical entity identities

The system SHALL allocate persisted positive INT OMOP Person and Visit Occurrence IDs from a Warehouse-wide, single-writer guarded allocator and persist the exact hospital/source business key to ID mapping. It SHALL not use row ordinal, temporary hash, name/DOB matching, external PostgreSQL runtime, or unsupported Fabric BIGINT IDENTITY as the OMOP INT ID.

#### Scenario: Same source key across batches

- **GIVEN** an already committed patient key `(hospital_id,source_system,source_record_id)`
- **WHEN** an approved replay arrives
- **THEN** the same `cdm.person.person_id` must be returned without allocating a new ID.

#### Scenario: Distinct hospitals with identical source keys

- **GIVEN** two different `hospital_id` values and identical external patient identifiers
- **WHEN** their mapping requests are validated
- **THEN** they must map to distinct Warehouse-global INT IDs, with no cross-hospital collision.

#### Scenario: Concurrent writer or INT overflow

- **GIVEN** a concurrent allocation attempt, allocator drift, or a projected value outside positive INT range
- **WHEN** a writer plans ID allocation
- **THEN** the writer must HOLD without partial `cdm` or ledger COMMIT and without assuming Fabric SERIALIZABLE isolation.

### Requirement: Ledger-scoped replay fence

The system SHALL link source manifest SHA256, OMOP mapping profile SHA256, batch ID and committed Person/Visit counts atomically with mapping and clinical writes.

#### Scenario: Identical versus conflicting replay

- **GIVEN** a recorded completed batch
- **WHEN** the same batch with unchanged hashes is requested
- **THEN** an independently verified replay must SKIP; a changed hash must fail without mutating Gold.

### Requirement: F2 ID preview cannot grant commit permission

The system SHALL treat deterministic Source-to-INT-ID planning as an uncommitted proposal. Only a target-verified single-writer Warehouse transaction with full Snapshot/Map/Gold revalidation MAY persist the ID Map, Person/Visit and COMMITTED Batch Ledger.

#### Scenario: Preview changes before Warehouse commit

- **GIVEN** the persisted Map, Gold row inventory or allocator differs from the verified preview
- **WHEN** the F2 Writer begins its transaction
- **THEN** it MUST reject the batch without exposing a GOLD_COMMITTED receipt or silently replacing any stable ID.

#### Scenario: Case-insensitive source identity collision

- **GIVEN** differently cased external source keys that may collide under Warehouse collation
- **WHEN** a preview is generated
- **THEN** the planner MUST HOLD before DML, rather than allocate two surrogate IDs to one effective source key.

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

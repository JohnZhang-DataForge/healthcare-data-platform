# NEW_ONLY Exact S3 Batch Selection

## ADDED Requirements

### Requirement: Manual Airflow selection is independent of display preview truncation

When a valid manual NEW_ONLY DagRun supplies exact Batch ID, immutable Manifest URI and SHA256, the existing S3-credentialed Discovery Pod SHALL validate that exact Batch against the complete vetted S3 inventory. Its return SHALL include one attested `verified_selected_batch` object in addition to the bounded `ready_batches_preview`. Airflow SHALL NOT require `preview_truncated=False` or equality of total READY count and preview length to process the correctly verified Batch.

#### Scenario: 26 ready batches, target outside first 25

- **GIVEN** 26 verified READY Batches and a 25-item preview omitting the requested Batch
- **WHEN** the Discovery Pod attests the exact requested Batch and Airflow validates its identity
- **THEN** manual selection succeeds without increasing the display preview or authorizing DB mutation

#### Scenario: Preview grows from 25 to 100

- **GIVEN** a later UI-only preview capacity of 100 and more than 100 READY Batches
- **WHEN** a verified requested Batch is outside the first 100
- **THEN** the selector still processes the attested Batch without dependence on preview membership

### Requirement: Preserve immutable and fail-closed identity contracts

The Discovery Pod MUST reject missing Batch identity fields, absent/quarantined target Batches and any disagreement between the requested and verified Manifest URI/SHA256 or source identity. Airflow MUST reject missing or mismatched attestations. It MUST preserve manual-only flags, read-only Discovery invariants and existing Claim/Spark/Writer authorization gates.

#### Scenario: Selected Batch Manifest drift

- **GIVEN** supplied Manifest URI/SHA256 does not match the actual validated S3 manifest
- **WHEN** exact selection is attempted
- **THEN** the run fails closed before Spark or any database COMMIT

### Requirement: Bounded preview remains non-authoritative

The Discovery XCom preview SHALL remain bounded for display and SHALL expose `ready_count` and `preview_truncated` accurately. An increase to 100 shall happen only after successful real Airflow E2E and shall not change the exact Batch validation mechanism.

#### Scenario: 101 ready batches after preview update

- **GIVEN** 101 READY Batches
- **WHEN** the display-only XCom is constructed
- **THEN** it includes at most 100 preview rows, correctly marks truncation, and does not reject a separately verified requested Batch

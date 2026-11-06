# Local DP Writer Parquet Dataset Reader

## ADDED Requirements

### Requirement: A Processing URI denotes a complete immutable Parquet dataset

The NEW_ONLY OMOP Writer SHALL accept one or more Spark Parquet data objects under the Processing URI prefix bound to the validated immutable Batch plan. A valid dataset MUST NOT be rejected solely because Spark produces multiple `part-*.parquet` files. The Writer MUST NOT change the Spark partitioning behavior to bypass this requirement.

#### Scenario: One-part legacy compatibility

- **GIVEN** a verified Processing prefix containing exactly one valid Parquet part
- **WHEN** the Writer reads the dataset
- **THEN** it maps the same logical Person or Visit rows and preserves downstream behavior

#### Scenario: Multi-part Spark output

- **GIVEN** a verified Visit Processing prefix with two or more Parquet part objects for one Batch
- **WHEN** the Writer reads all parts
- **THEN** it validates and maps the complete logical Visit dataset exactly once, regardless of S3 listing order

### Requirement: Combined rows remain strictly validated before database writes

The source adapter SHALL preserve Manifest SHA and immutable plan identity checks, refuse empty/malformed objects and duplicate listed keys, and SHALL apply the unchanged whole-Batch expected-row-count, source-identity, uniqueness and Person/Visit relationship validations to combined records before any business COMMIT.

#### Scenario: One missing or incorrect shard

- **GIVEN** any shard is absent, has invalid data, or contains source rows from a different Batch
- **WHEN** the Writer loads and verifies the combined records
- **THEN** the complete Batch fails closed before atomic COMMIT

#### Scenario: Duplicates across shards

- **GIVEN** two distinct Parquet parts contain the same Encounter source key
- **WHEN** combined validation runs
- **THEN** the Writer rejects the Batch as a duplicate rather than treating shards as independent valid batches

### Requirement: Preserve existing Writer commit and replay guarantees

The bugfix SHALL NOT modify OMOP schema, Mapping, SQL transaction/fencing, initial Claim rules, precommit inspection or completed-Batch idempotent SKIP semantics.

#### Scenario: Fresh E2E and retry

- **GIVEN** a new Synthea Batch processed by Spark into one or more Parquet parts
- **WHEN** the Writer commits and the same Batch is triggered again
- **THEN** the first run has one independently verifiable atomic COMMIT, and the second run safely skips without changing PG records

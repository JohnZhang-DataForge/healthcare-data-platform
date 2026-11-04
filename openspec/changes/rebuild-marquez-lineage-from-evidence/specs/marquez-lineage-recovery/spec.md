## ADDED Requirements

### Requirement: Historical Marquez metadata recovery must preserve event provenance
Any recovered OpenLineage RunEvent MUST come from an independently verified original event or intact database backup. New task executions MUST be identified as newly generated lineage and MUST NOT be represented as exact restoration of earlier historical events.

#### Scenario: Original event bytes missing
- **WHEN** only validation summaries, dataset names and timestamps remain
- **THEN** the recovery tool SHALL NOT synthesize historical COMPLETE events or historical run identifiers

### Requirement: Bounded recovery smoke must not alter healthcare business data
A recovery smoke test MUST run the existing opt-in Airflow probe only after confirming Marquez retention is disabled, and SHALL NOT run Synthea, Spark, OMOP Writer, business DagRuns or modify existing batch manifests.

#### Scenario: No original event archive is available
- **WHEN** a real ingestion health check is required
- **THEN** the opt-in DAG SHALL create a uniquely identified new execution
- **AND** independent Marquez readback SHALL verify its actual Jobs/Events
- **AND** its result SHALL be reported as regenerated lineage rather than restored history

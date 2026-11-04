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


### Requirement: New business lineage regeneration must not replay an OMOP commit
A NEW Patient / Encounter / Reconcile lineage run SHALL consume an independently validated, immutable READY Synthea manifest with the exact checked SHA256 and SHALL proceed only if Claim / Writer ledgers and Replay Fence permit an uncommitted Spark-only execution. The run SHALL never execute OMOP Writer or modify previously completed business batch state.

#### Scenario: Batch previously committed or has an active/conflicting claim
- **WHEN** the selected batch has a completed Writer entry, manifest hash drift, a live lease, or another active data-platform execution
- **THEN** the runner MUST stop before Spark or Airflow trigger and MUST NOT reinterpret that block as a new recovery candidate

### Requirement: Real business graph readback must inspect action-level lineage
The acceptance SHALL query genuine newly executed Spark Job / Run and action-level child Jobs, not only top-level application Jobs; SHALL verify Patient and Encounter Landing Input and Processing Output DatasetVersions, and SHALL require Reconcile's two inputs match those exact output versions. Column-level claims MUST be backed by actual OpenLineage column lineage facets and MUST NOT infer missing RDD COMPLETE events.

### Requirement: Independent no-business-mutation evidence
A controlled business Spark-only run SHALL capture protected OMOP PostgreSQL read-only baseline and post-run state, original paused state, exact source SHA, manifests, real Job/Run IDs and actual workflow conclusions. Any mismatch, incomplete readback or unknown commit status MUST remain HOLD, and MUST NOT trigger automatic retry or synthetic /lineage events.

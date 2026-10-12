# TASK-003 STEP06A — Visit ID Read-Only Preflight

## Status

STEP06A is complete and frozen as a read-only pre-mutation phase.

No Visit ID has been allocated yet.

## Frozen Candidate

- Run: `visit-proc-20261009t192437z-2081886`
- Rows: `5799`
- Unique business keys: `5799`
- Referenced Persons: `113`
- Business key: `(source_system, source_encounter_id)`
- Business-key SHA256:
  `aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

## PostgreSQL Baseline

Before allocation:

- `etl.visit_occurrence_id_map`: `0`
- `cdm.visit_occurrence`: `0`
- `etl.person_id_map`: `113`

Sequence:

`etl.visit_occurrence_id_map_visit_occurrence_id_seq`

Observed state:

- `last_value = 1`
- `is_called = false`
- `pg_get_serial_sequence()` binding exists
- column default is `NONE`
- automatic `DEFAULT nextval(...)` is not configured
- explicit controlled allocation is required

## STEP06A2 Allocation Preview

Current snapshot predicts:

- existing mappings: `0`
- new mappings: `5799`
- predicted ID range: `1..5799`

The predicted range is **not authoritative** until mutation-time revalidation and serialization.

Allocation Plan SHA256:

`28cf06fecb744c8da477221abde37e7afd72ba7d974ef2c93f847a3d79b63c93`

## STEP06A3 Exact Business-Key Reconciliation

Real Spark/JDBC reconciliation proved:

- Candidate keys: `5799`
- existing Candidate mappings: `0`
- new Candidate mappings: `5799`
- Candidate-only keys: `5799`
- DB-only Synthea keys: `0`
- duplicate Candidate business-key groups: `0`
- duplicate DB business-key groups: `0`
- duplicate Visit ID groups: `0`

Reconciliation Result SHA256:

`fb2905064173c564a8074b7f946c976b8d2ea1e0165ce7f2f3f2b3feb258eb31`

## Safety State

At STEP06A close:

- S3 access: read only
- PostgreSQL access: read only
- `nextval()` called: NO
- `setval()` called: NO
- Visit ID map mutated: NO
- sequence advanced: NO
- `cdm.visit_occurrence` written: NO

## Next Phase

Before STEP06B performs the first database mutation:

1. Commit this STEP06A freeze source as a Git checkpoint.
2. Revalidate current map/CDM/sequence state at mutation time.
3. Acquire a PostgreSQL serialization/advisory lock.
4. Reconcile the frozen Candidate business-key fingerprint again.
5. Allocate stable IDs transactionally.
6. Verify map coverage and sequence state independently.
7. Keep `cdm.visit_occurrence` loading as a later, separate mutation.

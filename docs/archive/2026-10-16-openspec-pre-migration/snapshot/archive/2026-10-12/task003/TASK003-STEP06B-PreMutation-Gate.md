# TASK-003 STEP06B Pre-Mutation Gate

## Status

STEP06B1 and STEP06B2 are complete.

Visit ID allocation has **not** started.

## Frozen Input

Processed Candidate:

- rows: 5799
- unique business keys: 5799
- business key: `(source_system, source_encounter_id)`

Frozen business-key snapshot SHA256:

`aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

The TSV file contains:

- UTF-8
- no header
- TAB delimiter
- LF line endings
- deterministic ascending business-key order
- exactly 5799 rows
- exactly 5799 unique keys

## Mutation Contract

Mutation Contract SHA256:

`58cd44b22eaf15674a7277c51c66418c305bd3743b403c7612d458453d87f9f0`

Allocation target:

`etl.visit_occurrence_id_map`

The allocation transaction must not write:

`cdm.visit_occurrence`

## Serialization

Transaction-scoped PostgreSQL advisory lock:

`5947676943154735385`

Lock order:

1. transaction advisory lock
2. `etl.visit_occurrence_id_map`
3. `etl.person_id_map`
4. `cdm.visit_occurrence`

## Candidate Transport

The frozen TSV is transported into PostgreSQL using:

`COPY temporary table FROM STDIN`

No persistent staging table is permitted.

## Allocation Policy

New business keys are allocated in deterministic ascending business-key order.

IDs use explicit:

`nextval('etl.visit_occurrence_id_map_visit_occurrence_id_seq')`

The current predicted range is:

`1..5799`

This prediction is not authoritative before mutation-time revalidation.

Only committed `(source_system, source_encounter_id) -> visit_occurrence_id`
mapping rows are authoritative.

## Sequence Failure Policy

PostgreSQL sequence advancement is not transactional.

If `nextval()` executes and the transaction later rolls back:

- sequence gaps are acceptable
- blind retry is forbidden
- backward `setval()` is forbidden
- recovery must reconcile both map state and sequence state first

Policy:

`ACCEPT_GAPS_NEVER_REWIND`

## Current Safety State

At STEP06B3:

- advisory lock acquired: NO
- nextval called: NO
- setval called: NO
- Visit ID allocation started: NO
- Visit ID map mutated: NO
- sequence advanced: NO
- CDM Visit write: NO

## Next Boundary

After the STEP06B3 source checkpoint, the first mutation step may:

1. acquire the advisory lock
2. acquire table locks
3. revalidate all database invariants
4. load the exact frozen key TSV into a temporary table
5. verify count, uniqueness, fingerprint-equivalent content, and zero prior mappings
6. revalidate sequence state immediately before allocation
7. execute explicit nextval allocation
8. insert only `etl.visit_occurrence_id_map`
9. commit
10. perform independent post-commit verification

CDM Visit row materialization remains a later separate step.

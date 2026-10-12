# TASK-003 STEP06C4E — Committed CDM Visit Materialization

## Status

**CDM Visit materialization is committed and independently reconciled.**

The authoritative target state is now:

- Target: `cdm.visit_occurrence`
- Rows: **5799**
- Unique `visit_occurrence_id`: **5799**
- ID range: **2..5800**
- ID 1 remains the accepted historical allocation gap.
- Target column count: **17**
- CDM row-shape SHA256:
  `995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1`

## Lineage

- Candidate rows: **5799**
- Candidate business-key SHA256:
  `aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`
- Visit ID map rows: **5799**
- Authoritative Visit mapping SHA256:
  `7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f`
- Person map rows: **113**
- Person mapping SHA256:
  `f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98`

## Visit ID sequence

The materialization did not allocate or modify Visit IDs.

- Before materialization: `5800|true`
- After materialization: `5800|true`
- `nextval()`: not used
- `setval()`: not used
- Visit ID reallocation: forbidden

## Real materialization

The frozen real materialization SQL SHA256 is:

`627056f9169fe0615c1649c8785623d240c8d6a562ba0ed993da537f2bafa214`

The controlled execution performed exactly:

- one persistent INSERT into `cdm.visit_occurrence`
- explicit 17-column target list
- 5799 inserted rows
- one COMMIT
- no ON CONFLICT
- no UPDATE
- no DELETE
- no TRUNCATE
- no sequence mutation

The original PostgreSQL client returned exit code **0** and emitted the successful COMMIT marker.

## Independent reconciliation

The independently verified post-commit state is:

- `cdm.visit_occurrence`: 5799 rows
- unique IDs: 5799
- ID range: 2..5800
- target/map ID mismatch: 0
- required NULL violations: 0
- Person FK: PASS
- Concept FK: PASS
- Provider FK: PASS
- Care Site FK: PASS
- preceding Visit FK: PASS
- row-shape SHA exactly matches the frozen payload

## Recovered tooling errors

Two tooling errors occurred **after the real database state was already valid**:

1. D2 classified the committed state as ambiguous because it compared the normalized sequence string `5800|true` against `5800|t`.
2. The first recovery script used `grep -F '^COMMIT$'`; with fixed-string mode the anchors were treated literally.

Neither error caused an additional INSERT, rollback, Visit ID allocation, or retry.

The real materialization was **never rerun**.

## Terminal policy

The first-batch materialization is terminal.

- Re-running the empty-target materialization SQL is **FORBIDDEN**.
- Reallocating Visit IDs is **FORBIDDEN**.
- Rewriting the 5799 committed rows as a retry is **FORBIDDEN**.
- Future work must start from the committed state verified by STEP06C4E.

## Frozen source checkpoint

Pre-C4E Git checkpoint:

`46bf2f7348029d1a17ed3db178fc93ea3a6a97ca`

STEP06C4E itself performs only read-only database verification and canonical source generation. Git checkpointing is a separate subsequent step.

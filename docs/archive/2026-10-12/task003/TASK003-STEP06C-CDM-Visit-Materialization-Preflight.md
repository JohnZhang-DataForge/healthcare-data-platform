# TASK-003 STEP06C — CDM Visit Materialization Preflight

## Frozen upstream state

STEP06B finalized the authoritative Visit ID mapping:

- Candidate business keys: 5799
- Visit ID map rows: 5799
- Visit ID range: 2 through 5800
- Visit ID 1: intentionally consumed sequence gap
- mapping SHA256:
  `7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f`

## STEP06C1 target discovery

`cdm.visit_occurrence` contains 17 columns.

Six columns are NOT NULL with no default and therefore must be explicitly
materialized:

1. `visit_occurrence_id`
2. `person_id`
3. `visit_concept_id`
4. `visit_start_date`
5. `visit_end_date`
6. `visit_type_concept_id`

The target Visit ID column is not an identity column and has no default.

The table has:

- 10 constraints
- 3 indexes
- 0 user triggers

Before materialization:

- `cdm.visit_occurrence` rows = 0
- `etl.visit_occurrence_id_map` rows = 5799
- `etl.person_id_map` rows = 113

## STEP06C2 verified Spark preflight

The verified Spark preflight read:

- frozen Processed Visit Candidate from S3
- authoritative Visit ID map from PostgreSQL
- authoritative Person map from PostgreSQL
- referenced FK target tables from PostgreSQL

It performed no database write and no S3 write.

Candidate:

- rows: 5799
- columns: 36
- unique business keys: 5799
- business-key SHA256:
  `aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

Person map:

- rows: 113
- SHA256:
  `f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98`

## Prepared CDM row shape

The preflight successfully constructed the complete 17-column
`cdm.visit_occurrence` row shape for all 5799 Candidate rows.

Frozen payload fingerprint:

`995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1`

This SHA is calculated from rows ordered by `visit_occurrence_id` and includes
all 17 target columns.

It is the authoritative pre-mutation payload fingerprint for the first Visit
materialization.

Validation results:

- final row shape rows: 5799
- unique Visit IDs: 5799
- required target NULL violations: 0
- cast failures: 0
- varchar(50) violations: 0
- invalid date order: 0
- invalid datetime order: 0
- date/datetime consistency violations: 0

## FK feasibility

All required database references were resolvable:

- Person FK: PASS
- Concept FK: PASS
- Provider FK: PASS
- Care Site FK: PASS
- preceding Visit FK feasibility: PASS

Observed distinct references:

- Person IDs: 113
- Concept IDs: 6
- Provider IDs: 0
- Care Site IDs: 0
- preceding Visit IDs: 0

The first batch therefore has no Provider, Care Site or preceding Visit
references to materialize.

## Canonical Encounter contract

The upstream frozen schema contract is:

`spark/contracts/canonical/encounter-v1.json`

SHA256:

`473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837`

Earlier temporary C2 development called this a "Candidate contract". That name
was misleading. Canonical source now identifies it correctly as the Encounter
canonical contract.

## Mutation boundary

STEP06C1/C2/C3 do not write `cdm.visit_occurrence`.

Before the first CDM mutation, a new transaction contract must:

1. revalidate the frozen Git checkpoint
2. revalidate the authoritative Visit mapping
3. revalidate target schema and constraints
4. revalidate `cdm.visit_occurrence` is still empty
5. reproduce the exact 5799-row CDM payload
6. reproduce row-shape SHA256
   `995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1`
7. acquire the required mutation locks
8. insert the complete Visit batch atomically
9. independently verify the committed CDM state

No `ON CONFLICT` or blind retry should hide unexpected database state.

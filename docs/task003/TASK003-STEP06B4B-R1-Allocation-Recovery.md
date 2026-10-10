# TASK-003 STEP06B4B-R1 — Failed Visit ID Allocation Recovery

## Failure

The first Visit ID allocation transaction crossed the sequence boundary but
failed on the first persistent INSERT.

PostgreSQL rejected the explicit value because:

`etl.visit_occurrence_id_map.visit_occurrence_id`

is:

`GENERATED ALWAYS AS IDENTITY`

The explicit INSERT therefore requires:

`OVERRIDING SYSTEM VALUE`

## Important discovery correction

The earlier pre-mutation inspection observed:

`column_default = NONE`

That fact is not sufficient to conclude that the column has no automatic
generation semantics.

The recovery inspection proved:

- `is_identity = YES`
- `identity_generation = ALWAYS`
- identity start = 1
- identity increment = 1
- identity cycle = NO
- sequence dependency type = `i`
- identity sequence =
  `etl.visit_occurrence_id_map_visit_occurrence_id_seq`

Future database-contract discovery must inspect identity metadata in addition
to `column_default`.

## Failure result

The first sequence allocation returned ID 1.

The subsequent INSERT failed.

The transaction rolled back, therefore:

- committed Visit ID map rows = 0
- CDM Visit rows = 0
- Person map rows = 113

PostgreSQL sequence advancement is not rolled back.

Recovery baseline:

- sequence last_value = 1
- sequence is_called = true
- ID 1 is consumed
- ID 1 is an accepted sequence gap
- predicted next value = 2

The predicted next value is not authoritative until a fresh locked
revalidation immediately before corrected mutation.

## Retry policy

The original STEP06B4B command must never be rerun.

Backward `setval()` is forbidden.

The corrected allocation transaction must:

1. acquire the same advisory lock
2. acquire the same table locks
3. revalidate map/CDM/Person state
4. verify identity metadata remains GENERATED ALWAYS
5. verify sequence baseline is still `1|true`
6. COPY the same frozen 5799-key snapshot
7. revalidate the business-key fingerprint
8. perform final sequence-state verification
9. cross a new irreversible boundary
10. allocate sequence values
11. INSERT explicit identity values using
   `OVERRIDING SYSTEM VALUE`
12. verify transaction state
13. commit
14. independently read back the committed mapping

With no other sequence consumer, the predicted allocation range is `2..5800`.
That range remains non-authoritative until the corrected transaction commits.

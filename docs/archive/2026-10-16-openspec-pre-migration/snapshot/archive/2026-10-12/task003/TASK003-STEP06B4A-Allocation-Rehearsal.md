# TASK-003 STEP06B4A — Visit ID Allocation Rehearsal

STEP06B4A validated the complete PostgreSQL transaction path immediately
before the first sequence allocation.

The rehearsal used the frozen 5799-row business-key snapshot.

## Verified operations

The rehearsal successfully:

1. acquired transaction advisory lock `5947676943154735385`
2. acquired the required table locks
3. revalidated the zero-row Visit ID map baseline
4. confirmed `cdm.visit_occurrence` remained empty
5. confirmed the sequence was still `last_value=1, is_called=false`
6. created a transaction-local Candidate key table
7. copied exactly 5799 frozen business keys using COPY FROM STDIN
8. recomputed the business-key SHA256 inside PostgreSQL
9. matched the frozen fingerprint
10. confirmed zero existing Candidate mappings
11. stopped before the irreversible sequence boundary
12. rolled back the complete rehearsal transaction
13. independently verified the database remained unchanged

Frozen business-key SHA256:

`aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

Rehearsal SQL SHA256:

`21e00285ce0ebaf43c0c38b57be74bf32204236ae7af8d9c1170143b757d31e1`

Rehearsal psql-output SHA256:

`7d26cf9f34bb39b445e2ff53171f4f345eb6c2818a2a39b0692756c5fb48e92b`

## Safety result

After rehearsal:

- Visit ID map rows: 0
- CDM Visit rows: 0
- Person map rows: 113
- sequence last_value: 1
- sequence is_called: false
- advisory lock released: yes
- nextval called: no
- setval called: no
- persistent mutation: no

STEP06B4A therefore validates the transaction path but does not allocate IDs.

The next mutation step must preserve the same lock, COPY, fingerprint and
database revalidation sequence before crossing the first sequence allocation
boundary.

If an error occurs after that boundary, automatic retry is forbidden.

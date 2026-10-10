# TASK-003 STEP06B4C — Committed Visit ID Mapping

## Final allocation result

The corrected Visit ID allocation transaction completed successfully.

Frozen Candidate business keys:

- rows: 5799
- unique keys: 5799
- business-key SHA256:
  `aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

Committed Visit ID mapping:

- rows: 5799
- unique Visit IDs: 5799
- minimum Visit ID: 2
- maximum Visit ID: 5800
- IDs are contiguous from 2 through 5800
- authoritative mapping SHA256:
  `7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f`

The mapping fingerprint represents ordered rows:

`source_system<TAB>source_encounter_id<TAB>visit_occurrence_id<LF>`

ordered by:

`source_system, source_encounter_id`

## Sequence state

The first failed allocation attempt consumed sequence value 1.

That value is intentionally preserved as a legal sequence gap.

Final sequence state:

- last_value: 5800
- is_called: true
- gap policy: `ACCEPT_GAPS_NEVER_REWIND`
- backward `setval()` was never used

## Identity behavior

`etl.visit_occurrence_id_map.visit_occurrence_id`

is:

`GENERATED ALWAYS AS IDENTITY`

The corrected transaction therefore used:

`OVERRIDING SYSTEM VALUE`

for explicit IDs obtained from the owned identity sequence.

## Database scope

STEP06B4B-R2 mutated only:

`etl.visit_occurrence_id_map`

It did not write:

`cdm.visit_occurrence`

After allocation:

- Visit ID map rows: 5799
- CDM Visit rows: 0
- Person map rows: 113

## Audit lineage

Recovery checkpoint before corrected mutation:

`d2bddab5ffee00df0f42db8273379b89364be115`

Corrected allocation SQL SHA256:

`4e0f7ba8c81639d601df832781515d1b2e6084706f9e96f1829ec12a2937bf7e`

Corrected psql output SHA256:

`db7add87ae7185dc2127b21230ce7756e2ec3c11bb80676c023fed0e066c59a3`

Recovery state SHA256:

`c34f6682f5a4482f1ef33f8a085463c4714fe858cd72c14bc03d75be3608dcc2`

Recovery amendment SHA256:

`f3f81af4effadc65e73255837f5cf79fe74050f2bf3f4685385f360b20a76a03`

## Next boundary

The committed mapping is now authoritative.

No Visit IDs may be reassigned.

The next phase may use this mapping to prepare and validate
`cdm.visit_occurrence` rows, but CDM materialization must remain a separate
mutation boundary with its own preflight, reconciliation, canonical source,
and Git checkpoint.

# Development Baseline

## Protected legacy baseline

The following directory is treated as a validated historical baseline:

`/data/spark/phase3c`

Do not directly refactor or overwrite it.

Relevant historical scripts include:

- 03-upload-synthea-landing.sh
- 04-ingest-patients-raw.sh
- 05-validate-patients-raw.sh
- 07-prepare-person-etl.sh
- 10-map-person-omop.sh
- 11-validate-omop-person.sh
- 12-load-person-cdm.sh

They are references for the V2 implementation, not the new project code.

## V2 rule

New development must first be implemented and validated under:

`/data/spark/healthcare-data-platform`

Only verified functionality should be committed.

## Development loop

DESIGN
  ->
GENERATE SHELL / CODE
  ->
RUN
  ->
VALIDATE
  ->
FAIL: modify same step and rerun
  ->
PASS: freeze result
  ->
NEXT STEP

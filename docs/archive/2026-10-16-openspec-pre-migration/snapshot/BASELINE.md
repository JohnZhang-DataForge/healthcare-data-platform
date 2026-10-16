# Development Baseline

> **LEGACY / PROTECTED BASELINE — NOT THE CURRENT DEVELOPMENT WORKFLOW**
>
> This file protects the historical `/data/spark/phase3c` baseline. Current development workflow and current TASK status are defined by:
>
> ```text
> docs/README.md
> docs/tasks/TASK-STATUS.md
> docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md
> docs/skill/SKILL-cn.md
> ```
>
> Do not use the historical loop to override the current canonical-source + PR/SHA + Self-Runner workflow.

## Protected legacy baseline

The following directory is treated as a validated historical baseline:

```text
/data/spark/phase3c
```

Do not directly refactor or overwrite it.

Relevant historical scripts include:

- `03-upload-synthea-landing.sh`
- `04-ingest-patients-raw.sh`
- `05-validate-patients-raw.sh`
- `07-prepare-person-etl.sh`
- `10-map-person-omop.sh`
- `11-validate-omop-person.sh`
- `12-load-person-cdm.sh`

They are references for the V2 implementation, not the current project development workflow.

## Current project location

```text
/data/spark/healthcare-data-platform
```

## Current development loop

```text
READ CURRENT STATUS / CONTRACT / FROZEN BOUNDARY
  ->
EDIT CANONICAL SOURCE DIRECTLY
  ->
STATIC TESTS
  ->
HEALTHCARE FEATURE PR
  ->
BIND EXACT PR HEAD SHA IN SELF-RUNNER
  ->
POLICY GATE
  ->
ARC REAL RUNTIME
  ->
VALIDATE BUSINESS EVIDENCE
  ->
FAIL: MODIFY SAME STEP AND REVALIDATE
  ->
PASS
  ->
MERGE
  ->
CHECKPOINT
  ->
NEXT STEP
```

Permanent historical generators remain authoritative only for files they already own. New STEP development does **not** require generating all source through Shell.

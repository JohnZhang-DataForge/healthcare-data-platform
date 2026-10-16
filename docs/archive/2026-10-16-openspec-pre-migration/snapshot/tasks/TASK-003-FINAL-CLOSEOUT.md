# TASK-003 Final Closeout

## 1. Final Status

**TASK-003 is COMPLETE / CLOSED.**

TASK-003 delivered the first complete Visit-domain implementation for the Healthcare Data Platform:

**Synthea Encounter → Canonical Encounter Raw → Processed Visit Candidate → Visit ID allocation → OMOP `cdm.visit_occurrence`.**

Final implementation checkpoint:

`373439c323c82388f559538204b1ba6348916fa0`

Local HEAD and remote `main` were verified to match this checkpoint before closeout.

---

## 2. Final Business Result

| Item | Final result |
|---|---:|
| Canonical Encounter rows | 5799 |
| Processed Visit Candidate rows | 5799 |
| Unique Visit business keys | 5799 |
| Referenced Person rows | 113 |
| Visit ID map rows | 5799 |
| `cdm.visit_occurrence` rows | 5799 |
| Unique `visit_occurrence_id` | 5799 |
| Visit ID range | 2..5800 |
| Historical Visit ID gap | ID 1 |
| Visit sequence | `5800|true` |

Final database gates:

- Person FK: PASS
- Concept FK: PASS
- Provider FK: PASS
- Care Site FK: PASS
- preceding Visit FK: PASS
- required NULL gate: PASS
- target/map ID equality: PASS
- final row-shape verification: PASS

TASK-003 therefore satisfies the Visit-domain delivery goal.

---

## 3. Final End-to-End Pipeline

```text
Synthea Encounter CSV
        |
        v
Canonical Encounter Adapter
        |
        v
Canonical Encounter Raw
SeaweedFS / health-raw
        |
        | DQ + manifest + approved lineage
        v
Visit transformation
        |
        v
Processed Visit Candidate
SeaweedFS / health-processed
        |
        | business key:
        | source_system + source_encounter_id
        v
Visit ID Allocation
etl.visit_occurrence_id_map
        |
        | authoritative surrogate ID
        v
17-column OMOP Visit payload
        |
        | PostgreSQL staging + validation
        v
cdm.visit_occurrence
```

The pipeline deliberately separates:

1. source normalization;
2. Canonical Raw persistence;
3. Processed business transformation;
4. surrogate-ID ownership;
5. final CDM materialization.

This separation should remain a project standard.

---

## 4. Frozen Lineage and Fingerprints

### 4.1 Canonical Encounter contract

File:

`spark/contracts/canonical/encounter-v1.json`

SHA256:

`473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837`

### 4.2 Visit Candidate business keys

Business key:

`(source_system, source_encounter_id)`

SHA256:

`aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

### 4.3 Person mapping

Rows: `113`

SHA256:

`f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98`

### 4.4 Visit ID mapping

Rows: `5799`

ID range: `2..5800`

SHA256:

`7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f`

ID 1 is an intentionally preserved historical gap.

Visit sequence:

`5800|true`

### 4.5 Final CDM Visit row shape

Rows: `5799`

Columns: `17`

SHA256:

`995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1`

### 4.6 Real materialization SQL

SHA256:

`627056f9169fe0615c1649c8785623d240c8d6a562ba0ed993da537f2bafa214`

### 4.7 Final materialization result contract

SHA256:

`d1df5b407950a830e4738ea1083189d47737f62305b16e0ff6caa294f2d1e863`

---

## 5. Development Phases

### STEP03 — Canonical Encounter

Converted Synthea Encounter source data into deterministic Canonical Encounter rows.

Final:

- 5799 rows
- 5799 unique Encounter keys

The adapter boundary isolates Synthea-specific structure from downstream Visit logic.

### STEP04 — Canonical Raw publication

Published approved Canonical Encounter Raw to SeaweedFS.

Implemented:

- guarded publication;
- DQ;
- manifest;
- independent readback;
- recovery;
- same-run replay verification;
- reset tooling.

This established the durable upstream contract consumed by Visit processing.

### STEP05 — Visit Processed

Converted approved Encounter Raw into a deterministic Visit Candidate.

Implemented:

- authoritative Raw resolution;
- Person mapping;
- Visit business mapping;
- immutable Processed publication;
- writer reservation;
- write intent;
- write permit;
- persisted readback;
- DQ;
- approved manifest.

The Processed Candidate intentionally contains no final Visit surrogate ID.

### STEP06A — Visit ID read-only preflight

Calculated:

- candidate keys: 5799
- existing Visit mappings: 0
- new Visit mappings required: 5799

No mutation occurred.

### STEP06B — Visit ID allocation

Created authoritative Visit surrogate IDs.

Final:

- mappings: 5799
- IDs: 2..5800
- sequence: `5800|true`

ID allocation and CDM materialization were intentionally separated into different mutations.

### STEP06C — CDM Visit materialization

Converted the persisted Candidate plus authoritative ID maps into the exact OMOP 17-column Visit row shape.

Final:

- rows: 5799
- unique IDs: 5799
- ID range: 2..5800

The mutation was executed once, committed once, independently reconciled, canonically verified and frozen.

---

## 6. Important Problems and Engineering Lessons

### 6.1 PostgreSQL identity columns

The first Visit ID mutation attempted explicit insertion into a column defined as:

`GENERATED ALWAYS AS IDENTITY`

PostgreSQL rejected the insert. Explicit insertion required:

`OVERRIDING SYSTEM VALUE`

The transaction rolled back, but sequence value 1 had already been consumed.

**Lesson:** PostgreSQL sequence allocation is not rolled back like ordinary table data.

Therefore:

- do not rewind sequences automatically;
- accept valid gaps;
- reconcile before retry;
- never treat surrogate IDs as gapless counters.

### 6.2 ID 1 gap is valid

Final Visit IDs begin at 2.

ID 1 is a legal historical gap caused by the failed first allocation attempt.

Correct invariant:

**Every committed business key owns one unique stable surrogate ID.**

Incorrect invariant:

**Surrogate IDs must be gapless.**

### 6.3 Bash special variable `COLUMNS`

A shell variable named `COLUMNS` collided with Bash terminal state.

The value became the terminal width and caused a schema report to be written to a file named `141`.

**Lesson:** avoid ambiguous shell variables that may collide with shell internals.

Prefer explicit names such as:

- `TARGET_COLUMNS_FILE`
- `SCHEMA_REPORT`
- `COLUMN_METADATA`

### 6.4 Pipe plus `python3 -` plus heredoc

A script attempted the equivalent of:

```bash
git show ... | python3 - <<'PY'
...
PY
```

The Python program itself consumed stdin, so the piped Git data was unavailable.

**Lesson:** if Python source is passed through stdin, pass input data through a temporary file, command-line filename, environment variable or explicit file descriptor.

### 6.5 Spark driver logs are not a clean structured-data channel

The 5799-row CDM payload was initially extracted from Spark driver logs.

A Log4j line appeared between payload markers. The SparkApplication itself completed correctly, but the parser failed.

Recovery succeeded by selecting only lines carrying the exact payload prefix.

**Lesson:** for structured output:

- prefix structured records;
- filter exact prefixes;
- verify expected row count;
- verify SHA256.

Future improvement: write structured artifacts directly to controlled storage rather than reconstructing them from general application logs.

### 6.6 PostgreSQL boolean text formatting

A reconciliation returned:

`5800|true`

A shell condition expected:

`5800|t`

The database was already correctly committed, but the wrapper classified it as ambiguous.

**Lesson:** do not depend on display formatting. Normalize booleans explicitly in SQL.

```sql
CASE
  WHEN is_called THEN 'true'
  ELSE 'false'
END
```

### 6.7 `grep -F` and regex anchors

A recovery script used:

`grep -F '^COMMIT$'`

With `-F`, `^` and `$` are literal characters.

Correct alternatives:

```bash
grep -xF 'COMMIT'
```

or:

```bash
grep -E '^COMMIT$'
```

### 6.8 Client failure does not prove database failure

The D2 wrapper initially reported an ambiguous result even though:

- INSERT succeeded;
- PostgreSQL returned COMMIT;
- the final table contained all 5799 rows.

The correct recovery was an independent read-only reconciliation.

Permanent rule:

**Never infer authoritative database state only from wrapper exit status.**

If commit state is uncertain:

1. do not retry;
2. open a new read-only session;
3. inspect persistent state;
4. classify from database truth.

### 6.9 Separate mutation design from mutation execution

TASK-003 established this safe sequence:

```text
design
  ↓
static validation
  ↓
freeze payload
  ↓
rehearsal
  ↓
real mutation
  ↓
independent reconciliation
  ↓
canonical verification
  ↓
Git freeze
```

This should become the standard for high-risk mutations.

### 6.10 Runtime evidence must be preserved

During failure investigation, completed SparkApplications, driver Pods, ConfigMaps, logs and runtime reports were preserved.

That allowed recovery without rerunning the workload.

**Lesson:** a wrapper failure does not mean the workload failed. Inspect existing evidence first.

### 6.11 Runtime evidence and Git source are different things

`runtime/` contains execution evidence.

Git contains:

- canonical source;
- contracts;
- validators;
- tests;
- generators;
- documentation.

Runtime evidence should normally remain outside Git.

Simple rule:

**Git explains how the system works.**

**`runtime/` explains what happened during one execution.**

---

## 7. Repository Structure

```text
healthcare-data-platform/
│
├── apps/
│   └── task003/
│
├── spark/
│   ├── apps/
│   │   └── visit/
│   └── contracts/
│       ├── canonical/
│       ├── omop/
│       └── processed/
│
├── scripts/
│   └── task003/
│
├── tests/
│   └── task003/
│
├── docs/
│   ├── task003/
│   ├── tasks/
│   ├── runbooks/
│   └── handoffs/
│
└── runtime/
    └── reports/
        └── task003/
```

---

## 8. Main Code Areas and Their Purpose

### `apps/task003/`

Control-plane and verification logic.

- `resolve_approved_encounter_raw.py` — resolves the authoritative approved Encounter Raw input.
- `build_encounter_raw_evidence.py` — builds deterministic evidence for approved Encounter Raw.
- `visit_candidate_rules.py` — Visit transformation and mapping rules.
- `plan_visit_processed.py` — creates the Processed Visit publication plan without writing.
- `inspect_visit_processed_prefix.py` — checks the immutable Processed destination before publication.
- `prepare_visit_processed_write_intent.py` — builds the formal write intent.
- `build_visit_writer_reservation.py` — builds writer reservation state and prevents duplicate writers.
- `issue_visit_processed_write_permit.py` — issues the controlled write permit.
- `build_visit_processed_runtime_bundle.py` — builds exact runtime inputs for the Spark writer.
- `build_visit_processed_dq.py` — builds deterministic Processed Visit DQ evidence.
- `build_visit_processed_manifest.py` — builds the approved Processed Visit manifest.
- `candidate_to_cdm_preflight.py` — produces the exact 17-column OMOP Visit shape without writing the target.
- `verify_cdm_materialization_preflight.py` — validates Candidate → CDM preflight state.
- `verify_visit_id_readonly_preflight.py` — validates the read-only Visit ID baseline.
- `verify_visit_id_pre_mutation_gate.py` — validates state immediately before ID mutation.
- `verify_visit_id_allocation_rehearsal.py` — validates the ID-allocation rehearsal.
- `verify_visit_id_allocation_recovery.py` — validates recovery after the failed initial identity insertion.
- `verify_committed_visit_id_mapping.py` — canonical verifier for committed Visit ID mapping.
- `verify_committed_cdm_visit_materialization.py` — canonical final verifier for committed `cdm.visit_occurrence`.

### `spark/apps/visit/`

Actual Spark/data-plane runtime.

- `processed_visit_writer_core.py` — core deterministic Processed Visit writer.
- `run_visit_processed_writer.py` — Spark runtime entry point.
- `publish_processed_dq.py` — write-once Processed DQ publisher.
- `publish_processed_manifest.py` — write-once approved Processed Manifest publisher.

Architectural distinction:

```text
apps/task003/
    control / contracts / verification

spark/apps/visit/
    actual Spark data execution
```

### `spark/contracts/canonical/`

Canonical Raw schemas and semantics.

Important file:

`encounter-v1.json`

### `spark/contracts/omop/`

Visit-domain and OMOP mapping expectations.

Important examples:

- `visit-candidate-v1.json`
- `visit-class-v1.json`

### `spark/contracts/processed/`

Persisted state and mutation contracts.

Important examples:

- `visit-candidate-publication-v1.json`
- `visit-writer-safety-v1.json`
- `visit-business-key-snapshot-v1.json`
- `visit-id-readonly-preflight-v1.json`
- `visit-id-mutation-contract-v1.json`
- `visit-id-allocation-recovery-amendment-v1.json`
- `visit-id-allocation-result-v1.json`
- `visit-cdm-materialization-preflight-v1.json`
- `visit-cdm-materialization-result-v1.json`

Contracts turn operational assumptions into machine-verifiable frozen state.

### `scripts/task003/`

Shell orchestration and reconstruction layer.

Responsibilities include:

- discovery;
- source preparation;
- runtime bundle preparation;
- SparkApplication launch;
- PostgreSQL gates;
- mutation rehearsal;
- controlled mutation;
- recovery;
- evidence freeze;
- canonical-source generation.

A useful pattern is `prepare-*.sh`: these scripts generate or reconstruct canonical code and contracts.

### `tests/task003/`

Static and behavioral tests for:

- adapters;
- mapping rules;
- Processed planning;
- writer safety;
- DQ;
- manifests;
- Visit ID allocation;
- CDM materialization;
- final committed-state verification.

Future work should move more reusable logic into Python and cover it here.

### `docs/`

- `docs/task003/` — technical documentation for TASK-003 phases.
- `docs/tasks/` — task-level milestone and final closeout documents.
- `docs/runbooks/` — reusable operational lessons.
- `docs/handoffs/` — development handoff state.

### `runtime/`

Execution evidence only.

Example:

`runtime/reports/task003/`

Contains Spark reports, frozen payloads, database snapshots, reconciliation output and temporary evidence.

This directory is not normal Git source.

---

## 9. Should These Workloads Eventually Run as Kubernetes Pods?

**Yes.**

Part of the platform already works this way.

Spark Operator creates:

```text
SparkApplication
      |
      +--> driver Pod
      |
      +--> executor Pods
```

Airflow also runs as Kubernetes workloads.

The mature execution model should become:

```text
Git
  |
  v
CI
  |
  v
Container Image
  |
  v
Kubernetes Job / SparkApplication
  |
  v
Runtime Evidence
```

`runner01` should gradually become a control/CI runner rather than the machine where production-style application logic is manually executed.

---

## 10. Do We Need Custom Container Images?

**Yes, for the production-like version of the platform.**

Every Pod already runs an image.

During development it is acceptable to use a generic Spark image and inject application code.

The mature model should use a project image such as:

```text
healthcare-data-platform-spark:<git-sha>
```

or preferably an immutable digest:

```text
ghcr.io/.../healthcare-data-platform-spark@sha256:<digest>
```

The image should contain stable runtime dependencies such as:

```text
Spark runtime
Python dependencies
spark/apps/*
shared Python libraries
required JDBC/JAR dependencies
stable runtime utilities
```

---

## 11. What Should NOT Be Baked into an Image?

Do not embed:

- S3 credentials;
- PostgreSQL passwords;
- Kubernetes credentials;
- Azure credentials;
- GitHub tokens.

These belong in Kubernetes Secrets or an external secret system.

Also do not bake run-specific values into the image:

- `batch_id`
- `run_id`
- input URI
- output URI
- database host
- execution date

Those are runtime parameters.

---

## 12. Which Code Should Be Containerized?

Good candidates:

```text
spark/apps/*
shared Python libraries
runtime validators
database loaders
reconciliation Jobs
```

Developer tooling can remain outside the runtime image:

```text
scripts/task003/*prepare*.sh
documentation generators
Git checkpoint scripts
discovery scripts
developer recovery utilities
```

The clean distinction is:

```text
repository tooling
    builds / validates / deploys

container image
    executes the workload
```

---

## 13. Recommended Kubernetes Runtime Model

A future Airflow DAG could orchestrate:

```text
Airflow
  |
  +--> Job: input preflight
  |
  +--> SparkApplication: Raw / Processed transform
  |
  +--> Job: DQ validation
  |
  +--> Job: Manifest publication
  |
  +--> Job: surrogate-ID reconciliation/allocation
  |
  +--> Job: CDM materialization
  |
  +--> Job: independent reconciliation
```

Each workload should receive:

- immutable image;
- contract version;
- input run ID;
- output run ID;
- Secret references;
- deterministic configuration.

---

## 14. Recommended Image Build Pipeline

Future GitHub Actions flow:

```text
Git commit
    |
    v
unit tests
    |
    v
build container
    |
    v
security scan
    |
    v
push image
    |
    v
record image digest
    |
    v
deploy workload
```

Image identity should be tied to Git identity.

Example:

```text
healthcare-data-platform-spark:373439c
```

Long term, deployment should use the immutable image digest rather than a mutable tag.

---

## 15. Should Future Development Use TASK-003 as the Blueprint?

**Yes.**

TASK-003 should become the reference implementation for later OMOP entities.

But we should copy its **architecture**, not its total amount of Bash.

The reusable lifecycle is:

```text
1. Source discovery
2. Source contract
3. Canonical adapter
4. Canonical Raw
5. Raw DQ
6. Raw approved Manifest

7. Processed planning
8. Deterministic transformation
9. Processed publication
10. Processed DQ
11. Processed approved Manifest

12. Business-key freeze
13. Surrogate-ID read-only reconciliation
14. ID mutation contract
15. ID rehearsal
16. ID allocation
17. Committed-ID reconciliation

18. Candidate → CDM preflight
19. Exact typed payload freeze
20. Materialization rehearsal
21. Controlled database mutation
22. Independent reconciliation

23. Canonical final-state contract
24. Final closeout
```

This is the main engineering blueprint produced by TASK-003.

---

## 16. What Can Be Reused Directly?

### Canonical publication

Reusable for entities such as:

- Condition
- Procedure
- Drug
- Measurement
- Observation

### Processed publication

The following pattern is generic:

```text
plan
reservation
write intent
write permit
writer
readback
DQ
manifest
```

### Surrogate ID allocation

Reusable concepts:

```text
business-key snapshot
read-only reconciliation
advisory lock
mapping table
sequence ownership
rehearsal
controlled mutation
post-mutation reconciliation
```

### CDM materialization

Reusable pattern:

```text
Candidate
   +
ID maps
   +
FK maps
   |
   v
typed staging
   |
   v
validation
   |
   v
controlled materialization
   |
   v
independent verification
```

---

## 17. What Should Be Refactored Before Many More Entities?

TASK-003 contains very large Bash generators.

They were useful during design because every state transition was visible and auditable.

But we should not create five more entities by copying thousands of lines of shell each time.

The project should gradually move reusable logic into shared Python modules.

Suggested future structure:

```text
src/
└── healthcare_platform/
    ├── canonical/
    │   ├── publisher.py
    │   └── evidence.py
    │
    ├── processed/
    │   ├── planner.py
    │   ├── reservation.py
    │   ├── writer.py
    │   ├── dq.py
    │   └── manifest.py
    │
    ├── ids/
    │   ├── reconciliation.py
    │   ├── allocation.py
    │   └── contracts.py
    │
    ├── cdm/
    │   ├── staging.py
    │   ├── materialization.py
    │   └── verification.py
    │
    └── runtime/
        ├── evidence.py
        └── hashing.py
```

Then entity-specific code becomes smaller:

```text
entities/
└── visit/
    ├── contract.json
    ├── mapping.py
    └── target.py
```

Later entities would mainly define:

- source schema;
- business key;
- transformation rules;
- OMOP target columns;
- FK rules;
- DQ rules.

The platform framework would provide the mechanics.

---

## 18. Recommended Project Standards Going Forward

### Every persisted dataset

Should expose:

- deterministic business key;
- row count;
- unique-key count;
- contract version;
- source lineage;
- cryptographic fingerprint.

### Every significant mutation

Should have:

```text
read-only preflight
mutation contract
rehearsal where practical
single controlled execution
independent reconciliation
```

### Every major development phase

Should finish with:

```text
canonical source
tests
documentation
Git checkpoint
```

### Every execution

Should preserve evidence under:

`runtime/reports/`

### Every uncertain failure

Should be reconciled from authoritative persistent state before retry.

---

## 19. What TASK-003 Really Produced

TASK-003 did not only produce:

`5799 visit_occurrence rows`

It established the project's first complete reference architecture:

```text
source
  ↓
canonical
  ↓
Raw
  ↓
Processed
  ↓
surrogate IDs
  ↓
OMOP CDM
  ↓
verification
```

It also established:

- immutable publication;
- deterministic fingerprints;
- mutation boundaries;
- transaction safety;
- recovery discipline;
- evidence preservation;
- canonical verification;
- Git freeze.

That engineering pattern is more valuable than the single Visit table itself.

---

## 20. Terminal Policy

The first TASK-003 batch is historical committed state.

The following are forbidden as blind TASK-003 retries:

- rerunning the empty-target Visit materialization;
- rewinding the Visit ID sequence;
- reallocating existing Visit IDs;
- rewriting the committed 5799 rows as a retry.

Future development must treat:

```text
cdm.visit_occurrence rows = 5799
IDs = 2..5800
sequence = 5800|true
```

as the authoritative TASK-003 baseline.

---

## 21. Final Decision

```text
TASK-003
STATUS=COMPLETE
CLOSED=YES

Canonical Encounter rows=5799
Processed Visit Candidate rows=5799
Visit ID mappings=5799
CDM Visit rows=5799

Visit ID range=2..5800
Visit sequence=5800|true

Candidate Business Key SHA256=
aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e

Visit Mapping SHA256=
7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f

Person Mapping SHA256=
f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98

CDM Row Shape SHA256=
995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1

Real Materialization SQL SHA256=
627056f9169fe0615c1649c8785623d240c8d6a562ba0ed993da537f2bafa214

Materialization Result Contract SHA256=
d1df5b407950a830e4738ea1083189d47737f62305b16e0ff6caa294f2d1e863

Implementation Git Checkpoint=
373439c323c82388f559538204b1ba6348916fa0
```

**TASK-003 is formally complete.**

Recommended next direction:

1. preserve TASK-003 as the reference implementation;
2. extract its reusable mechanics into shared platform modules;
3. introduce project-owned runtime container images;
4. execute runtime work through Kubernetes Jobs / SparkApplications;
5. use the resulting framework for subsequent OMOP entities.

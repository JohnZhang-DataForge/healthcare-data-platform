# TASK-003 Development Lessons

## 1. Purpose

This document records the main engineering lessons learned during TASK-003 so they can be reused by later OMOP entity pipelines.

TASK-003 implemented:

Synthea Encounter → Canonical Raw → Processed Visit Candidate → Visit ID allocation → `cdm.visit_occurrence`.

Final implementation checkpoint:

`373439c323c82388f559538204b1ba6348916fa0`

---

## 2. PostgreSQL Sequence and Identity Lessons

### 2.1 `GENERATED ALWAYS AS IDENTITY`

Explicit insertion into a `GENERATED ALWAYS AS IDENTITY` column requires:

`OVERRIDING SYSTEM VALUE`

The first failed Visit ID allocation consumed sequence value 1 even though the transaction rolled back.

### 2.2 Sequence values are not normal transactional rows

A rolled-back transaction does not necessarily restore sequence state.

Therefore:

- never rewind a sequence automatically;
- accept legal surrogate-ID gaps;
- reconcile persistent state before retry;
- never assume IDs must be gapless.

TASK-003 final Visit IDs are:

`2..5800`

ID 1 remains a valid historical gap.

---

## 3. Shell Scripting Lessons

### 3.1 Avoid Bash special variables

`COLUMNS` is a Bash/terminal special variable.

Using it as a normal filename variable caused an unexpected file named `141`.

Prefer explicit names such as:

- `TARGET_COLUMNS_FILE`
- `SCHEMA_REPORT`
- `COLUMN_METADATA`

### 3.2 Do not combine two stdin producers

This pattern is unsafe:

```bash
git show ... | python3 - <<'PY'
...
PY
```

The heredoc supplies Python source through stdin, so the piped data cannot also be consumed as stdin.

Use a temporary file or pass a filename.

### 3.3 Fixed-string grep is not regex grep

This check was wrong:

```bash
grep -F '^COMMIT$'
```

With `-F`, `^` and `$` are literal.

Use:

```bash
grep -xF 'COMMIT'
```

or:

```bash
grep -E '^COMMIT$'
```

---

## 4. Structured Data and Logging

Spark driver logs are not a clean data transport channel.

A Log4j line appeared inside a marker-delimited payload region even though the SparkApplication itself succeeded.

For structured data:

- prefix every structured record;
- filter only exact prefixes;
- verify row count;
- verify SHA256;
- prefer direct artifact storage over log scraping.

---

## 5. Normalize Database Output

PostgreSQL boolean output appeared as:

`true`

while one shell classifier expected:

`t`

The database state was correct; the wrapper logic was wrong.

Normalize database values explicitly before comparing them.

Example:

```sql
CASE
  WHEN is_called THEN 'true'
  ELSE 'false'
END
```

---

## 6. Wrapper Failure Is Not Database Failure

A client or wrapper exit code does not by itself prove mutation success or failure.

For commit uncertainty:

1. do not retry;
2. open a new independent read-only session;
3. inspect authoritative persistent state;
4. reconcile from database truth;
5. only then decide the next action.

TASK-003 permanently adopted:

**no blind retry after uncertain mutation state.**

---

## 7. Separate Mutation Design from Execution

Recommended lifecycle:

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

This pattern should be reused for future ID allocation and CDM materialization work.

---

## 8. Preserve Runtime Evidence

Do not immediately delete failed or completed:

- SparkApplications;
- driver Pods;
- ConfigMaps;
- logs;
- runtime reports.

A failed wrapper may still have produced a valid workload result.

Preserve evidence until reconciliation is complete.

---

## 9. Keep Runtime Evidence Out of Git

Git should contain:

- canonical code;
- contracts;
- tests;
- generators;
- documentation.

`runtime/` should contain:

- run-specific reports;
- snapshots;
- payloads;
- execution logs;
- reconciliation evidence.

Simple rule:

**Git explains how the system works.**

**runtime explains what happened in a specific run.**

---

## 10. Deterministic Fingerprints Matter

TASK-003 repeatedly used SHA256 to distinguish:

- source drift;
- payload drift;
- mapping drift;
- wrapper bugs;
- persistent-state changes.

Important final fingerprints:

- Candidate business keys:
  `aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`
- Visit mapping:
  `7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f`
- Person mapping:
  `f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98`
- CDM row shape:
  `995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1`

---

## 11. Reusable Development Standard

Future persisted datasets should expose:

- business key;
- row count;
- unique-key count;
- contract version;
- source lineage;
- fingerprint.

Future mutations should include:

- read-only preflight;
- mutation contract;
- rehearsal where practical;
- one controlled execution;
- independent reconciliation.

Future major phases should finish with:

- canonical source;
- tests;
- documentation;
- Git checkpoint.

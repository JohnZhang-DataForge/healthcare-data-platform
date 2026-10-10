# TASK-003 Completion Handoff

## 1. Status

TASK-003 is complete.

Final implementation checkpoint:

`373439c323c82388f559538204b1ba6348916fa0`

Final database state:

- `cdm.person`: 113 rows
- `etl.person_id_map`: 113 rows
- `etl.visit_occurrence_id_map`: 5799 rows
- `cdm.visit_occurrence`: 5799 rows
- unique Visit IDs: 5799
- Visit ID range: 2..5800
- Visit sequence: `5800|true`

TASK-003 must not be blindly rerun.

---

## 2. Authoritative Final Artifacts

Final result contract:

`spark/contracts/processed/visit-cdm-materialization-result-v1.json`

Canonical committed-state verifier:

`apps/task003/verify_committed_cdm_visit_materialization.py`

Verifier runner:

`scripts/task003/06c4e-verify-committed-cdm-visit-materialization.sh`

Final technical materialization document:

`docs/task003/TASK003-STEP06C4E-Committed-CDM-Visit-Materialization.md`

Final task closeout:

`docs/tasks/TASK-003-FINAL-CLOSEOUT.md`

---

## 3. Important Final Fingerprints

Candidate business-key SHA256:

`aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

Visit mapping SHA256:

`7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f`

Person mapping SHA256:

`f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98`

CDM row-shape SHA256:

`995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1`

Real materialization SQL SHA256:

`627056f9169fe0615c1649c8785623d240c8d6a562ba0ed993da537f2bafa214`

Materialization result contract SHA256:

`d1df5b407950a830e4738ea1083189d47737f62305b16e0ff6caa294f2d1e863`

---

## 4. Terminal Safety Rules

Do not:

- rerun the empty-target materialization;
- rewind the Visit sequence;
- reallocate existing Visit IDs;
- rewrite the committed 5799 Visit rows as a retry;
- delete runtime evidence needed for later audit.

If state is uncertain, run the canonical read-only verifier first.

---

## 5. Where to Start Next

TASK-003 should be treated as a reference implementation.

Before creating many more OMOP entities, extract reusable mechanics into shared modules:

- canonical publication;
- processed publication;
- DQ;
- manifest;
- ID reconciliation/allocation;
- CDM staging/materialization;
- post-mutation reconciliation;
- evidence hashing.

Then build the next entity on the shared framework instead of copying the full TASK-003 shell stack.

---

## 6. Recommended Runtime Direction

The long-term runtime should move toward:

```text
Airflow
  |
  +--> Kubernetes Job: preflight
  |
  +--> SparkApplication: transformation
  |
  +--> Kubernetes Job: DQ / manifest
  |
  +--> Kubernetes Job: ID allocation
  |
  +--> Kubernetes Job: CDM materialization
  |
  +--> Kubernetes Job: reconciliation
```

Runtime workloads should use immutable container images tied to Git SHA or image digest.

Secrets remain external to images.

---

## 7. Handoff Decision

TASK-003 requires no additional Visit ingestion or first-batch materialization development.

Next work should begin from the committed TASK-003 baseline rather than recreating it.

# TASK-003 Reference Blueprint for Future OMOP Entities

## 1. Purpose

TASK-003 is the first complete reference implementation for moving a healthcare source entity through:

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

Future entities should reuse this architecture.

They should not blindly copy all TASK-003 shell code.

---

## 2. Standard Entity Lifecycle

### Phase A — Source and Canonical

1. Discover source data.
2. Define source assumptions.
3. Define Canonical contract.
4. Build source-specific adapter.
5. Produce deterministic Canonical rows.
6. Validate business key and row counts.

### Phase B — Raw Publication

7. Guard target prefix.
8. Publish immutable Canonical Raw.
9. Build Raw DQ.
10. Publish Raw manifest.
11. Perform independent readback.

### Phase C — Processed Transformation

12. Resolve authoritative approved Raw.
13. Plan Processed output.
14. Resolve required foreign-key mappings.
15. Transform to deterministic entity Candidate.
16. Guard immutable Processed prefix.
17. Acquire writer reservation.
18. Build write intent.
19. Issue write permit.
20. Execute Processed writer.
21. Perform persisted readback.
22. Build Processed DQ.
23. Publish approved Processed manifest.

### Phase D — Surrogate IDs

24. Freeze business keys.
25. Reconcile existing mappings read-only.
26. Define mutation contract.
27. Rehearse allocation.
28. Allocate IDs once.
29. Independently reconcile committed mappings.

### Phase E — CDM Materialization

30. Candidate → exact CDM preflight.
31. Freeze typed target payload.
32. Rehearse database materialization.
33. Execute one controlled mutation.
34. Independently reconcile committed state.
35. Freeze canonical final-state contract.
36. Close the task.

---

## 3. Generic Platform Components to Extract

Recommended future shared package:

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

Entity-specific code should eventually become small:

```text
entities/
└── <entity>/
    ├── contract.json
    ├── mapping.py
    ├── target.py
    └── dq.py
```

---

## 4. Generic Invariants

Every persisted dataset should provide:

- deterministic business key;
- row count;
- unique business-key count;
- contract version;
- upstream lineage;
- SHA256 fingerprint.

Every significant mutation should have:

- read-only preflight;
- explicit mutation contract;
- rehearsal where practical;
- single controlled execution;
- independent reconciliation.

---

## 5. Kubernetes and Container Model

Future workloads should run through Kubernetes rather than manual long-running shell execution.

Suggested model:

```text
Git
  ↓
CI
  ↓
Container Image
  ↓
Airflow
  ↓
Kubernetes Job / SparkApplication
  ↓
Runtime Evidence
```

Spark transformation work:

- SparkApplication
- driver Pod
- executor Pods

Control operations such as:

- preflight;
- ID allocation;
- materialization;
- reconciliation

can run as Kubernetes Jobs.

---

## 6. Container Image Strategy

Use project-owned immutable runtime images.

Example:

`healthcare-data-platform-spark:<git-sha>`

Prefer deployment by immutable image digest.

Images may contain:

- Spark runtime;
- Python dependencies;
- application code;
- shared libraries;
- stable JAR dependencies.

Images must not contain:

- passwords;
- S3 keys;
- GitHub tokens;
- Azure credentials;
- run-specific batch IDs;
- run-specific URIs.

Those remain runtime configuration and Kubernetes Secrets.

---

## 7. Recommended CI Pipeline

```text
commit
  ↓
unit tests
  ↓
contract tests
  ↓
build image
  ↓
security scan
  ↓
push image
  ↓
record digest
  ↓
deploy / execute
```

Git SHA, image digest and runtime evidence should be traceable to one another.

---

## 8. Entities That Can Reuse the Pattern

Likely future OMOP domains include:

- `condition_occurrence`
- `procedure_occurrence`
- `drug_exposure`
- `measurement`
- `observation`

Each should reuse TASK-003 mechanics while supplying its own:

- business key;
- mapping rules;
- OMOP target columns;
- foreign-key rules;
- DQ rules.

---

## 9. What Not to Copy

Do not repeat the TASK-003 pattern as thousands of lines of new Bash for every entity.

TASK-003 used explicit shell orchestration while the platform architecture was still being discovered.

Future tasks should increasingly reuse shared Python modules and generic runners.

The architecture is the blueprint.

The TASK-003 code volume is not.

---

## 10. Reference Baseline

TASK-003 final state:

- Visit Candidate rows: 5799
- Visit ID mappings: 5799
- `cdm.visit_occurrence` rows: 5799
- Visit IDs: 2..5800
- sequence: `5800|true`
- implementation checkpoint:
  `373439c323c82388f559538204b1ba6348916fa0`

This reference implementation should remain frozen while shared platform components are extracted around it.

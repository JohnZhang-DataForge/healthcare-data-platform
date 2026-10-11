# TASK-004 Phase 9 Closeout — Unified Control Runtime Image

## 1. Final Status

**TASK-004 Phase 9 is COMPLETE / CLOSED.**

Phase 9 delivered a dedicated TASK004 control-plane runtime image that executes repository runtime logic from inside Kubernetes without depending on the runner01 filesystem or `kubectl exec` back into the Airflow scheduler.

Final source commit:

```text
d31035b41141c905dd56e21d339342f8988998e3
```

Final immutable image:

```text
ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-runtime@sha256:10865e3923441b82409cab50710857fd5a11bda6b5ec1afc9cbf9a8982a91bc6
```

---

## 2. Runtime Role

The image role is:

```text
TASK004_CONTROL_PLANE_RUNTIME
```

It is not:

```text
Synthea generator
Spark driver image
Airflow base image
```

Responsibilities:

- execute TASK004 control-plane scripts;
- resolve verified Landing lineage;
- provide runtime templates and source closure;
- provide Bash, Python and kubectl;
- launch future controlled Kubernetes workloads.

Spark remains the separate data plane.

---

## 3. Immutable Image Identity

Git commit:

```text
d31035b41141c905dd56e21d339342f8988998e3
```

Root OCI digest:

```text
sha256:10865e3923441b82409cab50710857fd5a11bda6b5ec1afc9cbf9a8982a91bc6
```

Linux/amd64 manifest digest:

```text
sha256:80dccbe023c062dbd245ca3f334dca5e1dfa44e10362a2eeeb4caabf153e2fa5
```

Image config digest:

```text
sha256:11fe25ad746e9375e8b401d6831a62b2056d50840180924451cd8802a8857cc5
```

Verified metadata:

```text
platform           = linux/amd64
runtime user       = 10001:10001
kubectl            = v1.32.5
project root       = /data/spark/healthcare-data-platform
runtime context    = in-cluster
OCI revision label = d31035b41141c905dd56e21d339342f8988998e3
```

Runtime execution should use immutable digest references.

---

## 4. Runtime Source Closure

The control image contains the 14-file minimum runtime closure:

```text
apps/task004/resolve_verified_landing_file.py
apps/task004/publish_synthea_landing.py

scripts/task004/04c-run-synthea-generate-publish.sh
scripts/task004/05c-resolve-runtime-lineage.sh
scripts/task004/05d-run-person-canonical.sh
scripts/task004/05e-run-visit-canonical.sh

kubernetes/manifests/task004/synthea-generate-publish-job.yaml.tpl

spark/apps/person/synthea_patient_adapter.py
spark/common/batch_manifest.py
spark/contracts/canonical/patient-v1.json
spark/manifests/task002/person-canonical-adapter.yaml.tpl

spark/apps/visit/synthea_encounter_adapter.py
spark/contracts/canonical/encounter-v1.json
spark/manifests/task003/encounter-canonical-adapter.yaml.tpl
```

Final runtime verification:

```text
runtime file count       = 14
runtime readable count   = 14
runtime unreadable count = 0
```

---

## 5. Direct In-Cluster Resolver

The TASK004 bridge supports:

```text
manual
in-cluster
```

Manual mode remains a runner01 development fallback.

In-cluster mode is the production-style orchestration path:

```text
control Pod
  ↓
local generic resolver
  ↓
SeaweedFS S3 endpoint
  ↓
verified manifest
```

It does not execute:

```text
control Pod
  ↓
kubectl exec
  ↓
Airflow scheduler
```

Verified:

```text
KUBECTL_EXEC_TO_SCHEDULER=NO
DIRECT_IN_CLUSTER_LINEAGE_RESOLUTION=PASS
```

---

## 6. Initial Failed Image

Initial source commit:

```text
13ccbe8b34362c26b9c46ae6fcf2e5431c41666d
```

Initial failed root digest:

```text
sha256:9a94a36f5b393744e4ed2cca2f47b036c27c58797b7ca7e4b695787d74c034e6
```

This image must not be reused.

The container started successfully and verified:

```text
PROJECT_GIT_SHA
kubectl v1.32.5
non-root runtime
```

It then failed while traversing repository directories.

Diagnostic result:

```text
runtime files readable   = 8
runtime files unreadable = 6
```

Affected directory classes included:

```text
kubernetes
spark/common
spark/contracts
spark/manifests
```

Observed mode:

```text
0644
```

A directory requires execute permission for pathname traversal.

---

## 7. Permanent Fix

The permanent image generator now normalizes all runtime directories under the project root to:

```text
0755
```

Individual file modes remain unchanged.

A regression test was added.

TASK004 regression count after the fix:

```text
109 tests
```

---

## 8. Replacement Runtime Verification

Replacement root digest:

```text
sha256:10865e3923441b82409cab50710857fd5a11bda6b5ec1afc9cbf9a8982a91bc6
```

The replacement ran on:

```text
worker02
```

Verified:

```text
runtime UID/GID          = 10001:10001
runtime directories      = 0755
runtime files readable   = 14/14
Java present             = NO
Spark present            = NO
Airflow present          = NO
kubectl                  = v1.32.5
```

Direct resolver verification:

```text
patients   = PASS
encounters = PASS
```

Patients:

```text
rows   = 20
sha256 = f4e249d17302acd8ffd53b54e92808547fe58af329f26ede89c6c0f5c74203e8
```

Encounters:

```text
rows   = 2459
sha256 = 8b39571d258380ccb8ebae2f19466a6430399210c0dcdce540bf5f0f00f83440
```

No Processing, PostgreSQL or RBAC mutation occurred during Phase 9 smoke verification.

---

## 9. Failure-Evidence Policy Demonstrated

The original failed Job and Pod were deliberately retained.

Recovery sequence:

```text
runtime failure
  ↓
retain Job / Pod
  ↓
inspect real filesystem modes
  ↓
identify root cause
  ↓
patch permanent generator
  ↓
run regression tests
  ↓
Git checkpoint
  ↓
build replacement immutable image
  ↓
verify new digest
  ↓
run replacement smoke
  ↓
replacement PASS
  ↓
clean historical failed resources
```

This should remain the preferred recovery pattern.

---

## 10. Phase 9 Exit Criteria

All Phase 9 exit criteria are satisfied:

```text
dedicated control image               PASS
GHCR build                            PASS
immutable OCI digest                  PASS
Git revision provenance               PASS
linux/amd64                           PASS
non-root runtime                      PASS
kubectl pinned                        PASS
14-file runtime closure               PASS
directory traversal                   PASS
direct in-cluster lineage             PASS
patients resolver                     PASS
encounters resolver                   PASS
runner01 filesystem independence      PASS
scheduler kubectl-exec independence   PASS
runtime cleanup                       PASS
```

**Phase 9 is closed.**

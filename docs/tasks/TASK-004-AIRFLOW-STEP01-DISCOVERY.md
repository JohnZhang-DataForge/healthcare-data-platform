# TASK-004 Airflow STEP01 — Read-only Discovery / Contract Freeze

> **CURRENT STEP CHECKPOINT**  
> Date: 2026-10-12  
> STEP status: **PASS**  
> Mutation: **NO**  
> TASK004 overall: **IN PROGRESS**  
> Airflow orchestration overall: **NOT YET VERIFIED**

## 1. Purpose

Before writing the TASK004 production DAG, this STEP performed a read-only discovery of:

- current Airflow runtime and DAG visibility;
- KubernetesPodOperator availability;
- current ServiceAccounts and S3 Secret presence;
- effective Kubernetes RBAC derived from RoleBinding / ClusterRoleBinding;
- current TASK004 control runtime image source closure;
- runtime image build trigger coverage.

No Pod, Job, SparkApplication, ConfigMap, Secret or data product was created or changed by the discovery.

## 2. Source identity

Healthcare exact main inspected:

```text
06dfd1d4f2462e04245206564ea21b6ad4e4699d
```

Self-Runner discovery implementation:

```text
PR #33 merge = f3d0f79971ac61b0a84a011567fdb2d70b70c812
PR #34 merge = d57639bc518c7de3d655c957e8ac9a845b1df619
```

Final accepted discovery run:

```text
Run      = 38289799881
Artifact = 11763724885
Digest   = sha256:388a6c83f01c458099bf029fbb0e95653a5390f8f1457e3a1747c6e42e6ac2a3
```

## 3. Airflow runtime facts

```text
AIRFLOW_VERSION=3.2.2
KUBERNETES_PROVIDER_VERSION=10.17.1
KUBERNETES_POD_OPERATOR_IMPORT=PASS
AIRFLOW_DAG_IMPORT_ERRORS=0
AIRFLOW_SMOKE_DAG_VISIBLE=YES
AIRFLOW_SCHEDULER_SERVICE_ACCOUNT=dw-airflow-scheduler
AIRFLOW_SCHEDULER_NODE=worker02
AIRFLOW_DAGS_FOLDER=/opt/airflow/dags/repo/airflow/dags
```

Scheduler Pod containers:

```text
scheduler=apache/airflow:3.2.2
git-sync=registry.k8s.io/git-sync/git-sync:v4.4.2
scheduler-log-groomer=apache/airflow:3.2.2
```

Conclusion:

```text
AIRFLOW_ENGINE_BLOCKER=NO
KUBERNETES_PROVIDER_BLOCKER=NO
DAG_SYNC_BLOCKER=NO
```

The current repo DAG is still only the BashOperator smoke DAG:

```text
CURRENT_DAG_USES_KPO=NO
```

## 4. Existing runtime dependencies

ServiceAccounts observed:

```text
dw-airflow:
  default
  dw-airflow-api-server
  dw-airflow-create-user-job
  dw-airflow-dag-processor
  dw-airflow-migrate-database-job
  dw-airflow-scheduler
  dw-airflow-triggerer

dw-spark:
  default
  spark-job
  spark-operator-controller
  spark-operator-spark
  spark-operator-webhook

dw-synthea:
  default
```

Required existing Secrets:

```text
DW_SPARK_S3_SECRET=PRESENT
DW_SYNTHEA_S3_SECRET=PRESENT
```

No Secret values were read or logged.

## 5. Effective scheduler RBAC

The final RBAC inspector resolves RoleBinding / ClusterRoleBinding / Role / ClusterRole directly and understands fixed `resourceNames`.

Current `dw-airflow/dw-airflow-scheduler`:

```text
dw-airflow pods:
  create=yes
  get=yes
  list=yes
  watch=yes
  delete=yes
  pods/log get=yes

dw-spark pods:
  create=no
  get=no
  list=no
  watch=no
  delete=no
  pods/log get=no

dw-synthea pods:
  create=no
  get=no
  list=no
  watch=no
  delete=no
  pods/log get=no
```

Therefore a KubernetesPodOperator task cannot currently create and monitor TASK004 control Pods directly in `dw-spark` or `dw-synthea`.

## 6. Existing spark-job is not a TASK004 control ServiceAccount

Current `dw-spark/spark-job`:

```text
namespaces get=no
CRD get=no

dw-spark:
  secrets get=no
  serviceaccounts get=no

  configmaps create=yes
  configmaps get=yes
  configmaps patch=yes
  configmaps delete=yes

  sparkapplications create=no
  sparkapplications get=no
  sparkapplications delete=no

  pods get=yes
  pods list=yes
  pods/log get=yes
```

The TASK004 Person / Visit / Reconciliation control runners need more than the current `spark-job` permissions.

Decision:

```text
DO_NOT_OVERLOAD_SPARK_JOB_AS_CONTROL_SA
```

A dedicated narrow TASK004 control ServiceAccount should be created for `dw-spark`.

## 7. dw-synthea/default is not a TASK004 control ServiceAccount

Current `dw-synthea/default`:

```text
namespaces get=no
nodes get=no
secrets get=no
configmaps create/get/patch/delete=no
jobs create/get/delete=no
pods get/list=no
pods/log get=no
```

This cannot execute the existing canonical:

```text
scripts/task004/04c-run-synthea-generate-publish.sh
```

Decision:

```text
DO_NOT_GRANT_CONTROL_PERMISSIONS_TO_DEFAULT_SA
```

A dedicated narrow TASK004 control ServiceAccount should be created for `dw-synthea`.

## 8. Control runtime image blocker

The current accepted control runtime source does not include Batch Reconciliation:

```text
CONTROL_RUNTIME_RECONCILE_COMMAND=NO
CONTROL_RUNTIME_RECONCILIATION_ASSETS=NO
RUNTIME_BUILD_TRACKS_RECONCILIATION=NO
```

Missing from the runtime image closure:

```text
scripts/task004/05f-reconcile-person-visit.sh
spark/apps/task004/reconcile_person_visit.py
spark/manifests/task004/person-visit-reconciliation.yaml.tpl
```

Current entrypoint has:

```text
resolve
generate-publish
person
visit
```

but not:

```text
reconcile
```

The current immutable image:

```text
ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-runtime@sha256:10865e3923441b82409cab50710857fd5a11bda6b5ec1afc9cbf9a8982a91bc6
```

must therefore **not** be used as the final control image for the complete Airflow DAG.

## 9. Generator ownership

The TASK004 runtime image remains owned by the historical permanent generator:

```text
scripts/task004/06a-prepare-unified-runtime-image.sh
```

Therefore the next runtime-image change must update the generator and regenerate/verify:

```text
images/task004-runtime/Dockerfile
images/task004-runtime/entrypoint.sh
.github/workflows/build-task004-runtime-image.yml
tests/task004/test_unified_runtime_image_source.py
```

Directly patching only generated runtime-image files is not accepted.

## 10. Airflow prerequisite classification

Final discovery result:

```text
TASK004_AIRFLOW_DISCOVERY=PASS
DISCOVERY_MUTATION=NO
AIRFLOW_ORCHESTRATION_PREREQUISITES_READY=NO
```

This does **not** mean Airflow is broken.

It means:

```text
Airflow engine                    READY
Kubernetes provider / KPO import READY
DAG sync / import                READY
TASK004 control image closure    NOT READY
cross-namespace KPO RBAC         NOT READY
TASK004 control Pod RBAC         NOT READY
```

## 11. Ordered next steps

Do not write the full TASK004 DAG yet.

Proceed in this order:

```text
STEP02
Control Runtime Image vNext
  - add reconciliation command/assets
  - generator-owned reconstruction
  - source tests
  - immutable GHCR build
  - real non-root cluster smoke

STEP03
Dedicated TASK004 Control RBAC
  - dw-spark control SA + minimal Role/ClusterRole
  - dw-synthea control SA + minimal Role/ClusterRole
  - scheduler cross-namespace KPO pod lifecycle RBAC
  - read-only effective RBAC verification
  - minimal control-Pod smoke

STEP04
First bounded KubernetesPodOperator DAG
  - no full E2E yet
  - prove real Scheduler -> KPO -> control Pod lifecycle

Only after STEP04 PASS:
  - compose Generate -> Person -> Visit -> Reconcile
  - execute real DAG run
  - validate metadata/task/data evidence
```

## 12. Fail-fast history

Two early discovery failures were control-layer defects and did not execute cluster discovery:

```text
Run 38288902609
  failure = workflow script path
  cluster discovery = NOT RUN

Run 38288983232
  failure = Self-Runner checkout absent
  cluster discovery = NOT RUN
```

The corrected discovery then passed:

```text
Run 38289082211 = PASS
```

The final resourceNames-aware RBAC discovery also passed:

```text
Run 38289799881 = PASS
```

## 13. STEP01 classification

```text
TASK004_AIRFLOW_STEP01_DISCOVERY=PASS
AIRFLOW_ENGINE=READY
KPO_PROVIDER=READY
DAG_SYNC=READY
CONTROL_RUNTIME_VNEXT=REQUIRED
CONTROL_RBAC=REQUIRED
FULL_AIRFLOW_DAG=NOT_YET
TASK004_OVERALL=IN_PROGRESS
NEXT=TASK004_AIRFLOW_STEP02_CONTROL_RUNTIME_IMAGE_VNEXT
RESULT=PASS
```

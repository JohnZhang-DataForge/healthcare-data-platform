# TASK004 Airflow Processing Orchestration — Mainline Closeout

> **MAINLINE ACCEPTED / 2026-10-12**  
> 本文记录 TASK004 Airflow Processing orchestration 的正式主线验收。  
> 本轮范围从已验证 Landing manifest 开始，完成 Person + Visit → Reconcile 的真实 Airflow 调度闭环。  
> 本文不声明 Generate Synthea / Landing publication 已经纳入 Airflow；该部分是下一阶段。

## 1. 正式状态

~~~text
GitHub DAG source              PASS
git-sync                       PASS
Airflow DAG parse              PASS
KubernetesPodOperator PodSpec  PASS
Scheduler → dw-spark RBAC      PASS
Control runtime in-cluster API PASS
Person Airflow task            PASS
Visit Airflow task             PASS
Dynamic XCom handoff           PASS
Reconcile Airflow task         PASS
Successful resource cleanup    PASS
PostgreSQL mutation            NO

TASK004 Airflow Processing Orchestration
= PASS / MAINLINE ACCEPTED
~~~

TASK004 整体仍为：

~~~text
IN PROGRESS
~~~

下一阶段是把：

~~~text
Generate Synthea
→ Landing publication / validation
~~~

接到当前已经验收的 Processing DAG 上游。

---

## 2. 正式业务链

当前 mainline DAG：

~~~text
GitHub main
  ↓
git-sync
  ↓
Airflow 3.2.2
  ↓
task004_processing_pipeline
  ├─ Person  ─┐
  └─ Visit   ─┤
              ↓
           Reconcile
~~~

Person / Visit 使用：

~~~text
KubernetesPodOperator
→ dw-spark
→ ServiceAccount: task004-control-runtime
→ TASK004 control-runtime image
→ SparkApplication
→ Spark Operator
→ Driver / Executor
~~~

Person 与 Visit 并行。

两者成功后通过 KPO XCom 返回动态结果：

~~~text
processing_data_uri
canonical_rows
run_id
~~~

Reconcile 不使用历史硬编码 Processing URI，而是消费本次 Airflow run 的 Person / Visit XCom 输出。

---

## 3. Runtime / RBAC 主线闭环

### Control runtime reconciliation closure

Healthcare PR #26：

~~~text
tested PR HEAD = c9127f9fc4ce52781a4825309ddd6bb8686ea911
merge/main SHA = e99a68e8b24a3dee97ea38ce7dc426a63c6fb119
~~~

Post-merge immutable runtime image：

~~~text
ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-runtime
@sha256:bf7f4611a9dcbd8bd79b420f80c5f97f4ec92e0dbd5ba8132cea4be59fdf57bf
~~~

正式 runtime smoke 已确认：

~~~text
CONTROL_RUNTIME_RBAC=PASS
CONTROL_RUNTIME_NON_ROOT=PASS
RECONCILIATION_ASSETS=PASS
RECONCILE_RENDER_ONLY=PASS
SPARKAPPLICATION_APPLY=NO
PROCESSING_MUTATION=NO
POSTGRESQL_MUTATION=NO
SUCCESSFUL_POD_RESIDUAL=NO
RESULT=PASS
~~~

### Airflow scheduler launch RBAC

Healthcare PR #27 增加：

~~~text
kubernetes/manifests/task004/airflow-task004-control-runtime-rbac.yaml
~~~

职责边界：

~~~text
dw-airflow/dw-airflow-scheduler
  → 只创建 / 观察 / 删除 dw-spark control Pods
  → 可读 Pod logs
  → 可 pods/exec 支持 KPO XCom
  → 不读 dw-spark Secrets
  → 不直接创建 SparkApplication

dw-spark/task004-control-runtime
  → 管理 SparkApplication / ConfigMap
  → 读取运行所需 namespace-local Secret / spark-job SA

dw-spark/spark-job
  → Spark Driver / Executor runtime identity
~~~

真实 scheduler SelfSubjectAccessReview：

~~~text
CAN_I_CREATE_PODS=yes
CAN_I_GET_PODS=yes
CAN_I_LIST_PODS=yes
CAN_I_WATCH_PODS=yes
CAN_I_PATCH_PODS=yes
CAN_I_DELETE_PODS=yes
CAN_I_GET_PODS_LOG=yes
CAN_I_CREATE_PODS_EXEC=yes
CAN_I_GET_PODS_EXEC=yes
CAN_I_LIST_EVENTS=yes
CAN_I_WATCH_EVENTS=yes

CAN_I_GET_SECRETS=no
CAN_I_CREATE_SPARKAPPLICATIONS=no

AIRFLOW_SCHEDULER_DW_SPARK_POD_RBAC=PASS
AIRFLOW_SCHEDULER_PRIVILEGE_SEPARATION=PASS
~~~

---

## 4. Healthcare mainline commits

### Airflow Processing DAG

Healthcare PR #27：

~~~text
final PR HEAD = e49b67e81119c8e18426a26faf7fa5a1cf6b6ee0
merge/main SHA = f82a70e28038d87bb9e7e60670dfb0c39e928b0b
~~~

正式文件：

~~~text
airflow/dags/task004_processing_pipeline.py
kubernetes/manifests/task004/airflow-task004-control-runtime-rbac.yaml
tests/task004/test_airflow_task004_processing_source.py
.github/workflows/task004-airflow-step02-source.yml
~~~

### Default unpaused follow-up

首次 live run 成功 trigger 后，Airflow 新 DAG 默认处于 paused，导致：

~~~text
DAG_IS_PAUSED=true
DAG_RUN_STATE=queued
TASK_STATE_PERSON=None
TASK_STATE_VISIT=None
TASK_STATE_RECONCILE=None
~~~

这不是 KPO / Spark / RBAC 问题。

完成一次正式 runner unpause 后：

~~~text
DAG_IS_PAUSED=false
TASK004_AIRFLOW_DAG_UNPAUSE=PASS
~~~

随后 Healthcare PR #28 将默认行为固化到 Git source：

~~~text
is_paused_upon_creation=False
~~~

PR #28：

~~~text
final PR HEAD = fe2a044cf0ec3972732551c02d2a8529f6646eea
merge/main SHA = 5e043b8f00d89a01b72ae6264f35903ceff93de9
~~~

当前 Healthcare main authority：

~~~text
5e043b8f00d89a01b72ae6264f35903ceff93de9
~~~

---

## 5. Validation evidence

### Source gate

Healthcare run：

~~~text
38309219834  PASS
~~~

PR #28 follow-up source gate：

~~~text
38312722895  PASS
~~~

### Real Airflow parse

Self-Runner：

~~~text
Run 38309576088  PASS
~~~

Evidence：

~~~text
AIRFLOW_VERSION=3.2.2
KUBERNETES_PROVIDER_VERSION=10.17.1
IMPORT_ERROR_COUNT=0
DAG_ID=task004_processing_pipeline
TASK_IDS=person,reconcile,visit
TASK_CLASS_PERSON=KubernetesPodOperator
TASK_CLASS_VISIT=KubernetesPodOperator
TASK_CLASS_RECONCILE=KubernetesPodOperator
PERSON_TO_RECONCILE=PASS
VISIT_TO_RECONCILE=PASS
RECONCILE_UPSTREAM_GATE=PASS
AIRFLOW_DAG_IMPORT=PASS
AIRFLOW_DAG_STRUCTURE=PASS
RESULT=PASS
~~~

### KPO PodSpec dry-run

Self-Runner：

~~~text
Run 38309911048  PASS
~~~

Evidence：

~~~text
KPO_PODSPEC_PERSON=PASS
KPO_PODSPEC_VISIT=PASS
KPO_PODSPEC_RECONCILE=PASS
RUNTIME_IMAGE_DIGEST_GATE=PASS
CONTROL_RUNTIME_SERVICE_ACCOUNT_GATE=PASS
NON_ROOT_SECURITY_CONTEXT_GATE=PASS
PERSON_XCOM_SIDECAR_GATE=PASS
VISIT_XCOM_SIDECAR_GATE=PASS
RECONCILE_DYNAMIC_INPUT_GATE=PASS
KPO_DRY_RUN_RESOURCE_CREATE=NO
RESULT=PASS
~~~

### Scheduler RBAC

Self-Runner：

~~~text
Run 38311231070  PASS
~~~

### Control-runtime in-cluster kubectl

Self-Runner：

~~~text
Run 38311402840  PASS
~~~

Evidence：

~~~text
RUNTIME_UID=10001
RUNTIME_GID=10001
CONTROL_RUNTIME_NODE=worker02
CONTROL_RUNTIME_INCLUSTER_KUBECTL=PASS
SUCCESSFUL_CONTROL_RUNTIME_POD_RESIDUAL=NO
RESULT=PASS
~~~

---

## 6. Live Airflow orchestration acceptance

Self-Runner live run：

~~~text
Run = 38311805385
Airflow run_id = task004-step02c-38311805385
~~~

输入使用已验收 Landing batch：

~~~text
batch_id = task004-p20-first-landing-20261011
~~~

Live evidence：

~~~text
PROCESSING_MUTATION=YES
SPARKAPPLICATION_MUTATION=YES_TEMPORARY
POSTGRESQL_MUTATION=NO

AIRFLOW_GITSYNC_DAG_VISIBLE=YES
AIRFLOW_GITSYNC_EXACT_SOURCE_GATE=PASS
AIRFLOW_DAG_TRIGGER=PASS

TASK_STATE_PERSON=success
TASK_STATE_VISIT=success
TASK_STATE_RECONCILE=success
AIRFLOW_DAG_RUN=PASS

SUCCESSFUL_SPARKAPPLICATION_RESIDUAL=NO
SUCCESSFUL_CONTROL_POD_RESIDUAL=NO

TASK004_AIRFLOW_STEP02C_LIVE=PASS
RESULT=PASS
~~~

Live artifact：

~~~text
Artifact ID = 11775098927
Digest =
sha256:570901ce456778457fecc3a1c718ea88aa9ea9dafe8281028e917b3f678cf0ed
~~~

---

## 7. Post-merge exact-main verification

PR #28 merge 后：

~~~text
Healthcare main =
5e043b8f00d89a01b72ae6264f35903ceff93de9
~~~

Self-Runner post-merge gate：

~~~text
Run 38313275171  PASS
~~~

Evidence：

~~~text
LOCAL_DAG_SHA256=
6269920737ca616194f6282994dca711dac98afabf7a4b4f992c01d84789ac1c

GITSYNC_DAG_SHA256=
6269920737ca616194f6282994dca711dac98afabf7a4b4f992c01d84789ac1c

DAG_IS_PAUSED=false
AIRFLOW_GITSYNC_POSTMERGE_SOURCE_GATE=PASS
DAG_UNPAUSED_DEFAULT_SOURCE_GATE=PASS
AIRFLOW_DAG_RUNTIME_UNPAUSED=PASS
DATA_MUTATION=NO
RESULT=PASS
~~~

---

## 8. 非业务失败 / 经验

以下失败没有推翻业务主线，也没有进入业务 mutation。

### KPO dry-run harness

~~~text
Run 38309770180
~~~

原因：

~~~text
验证脚本错误地假设 container_security_context 是 Kubernetes Python 对象；
provider 10.17.1 返回 dict。
~~~

修正 runner assertion 后：

~~~text
Run 38309911048  PASS
~~~

Healthcare DAG 无需修改。

### ARC impersonation auth check

~~~text
Run 38311070377
~~~

RBAC manifest 已成功 apply，但 runner 的 kubectl auth can-i impersonation 检查遇到 ARC runner 的 localhost:8080 context 异常。

不继续把该辅助问题当主线 blocker。

改为由真实 Airflow scheduler 使用自己的 ServiceAccount token 执行 SelfSubjectAccessReview：

~~~text
Run 38311231070  PASS
~~~

### New DAG paused by default

Live trigger 成功，但新 DAG 默认 paused。

正式处理：

1. runner one-time unpause；
2. Git source 增加 is_paused_upon_creation=False；
3. post-merge exact git-sync 验证 PASS。

---

## 9. 冻结边界

从本 Closeout 起，以下成为 TASK004 当前 mainline accepted baseline：

~~~text
GitHub → git-sync DAG delivery
Airflow task004_processing_pipeline
Person KPO
Visit KPO
Person/Visit dynamic XCom handoff
Reconcile KPO
scheduler → dw-spark Pod-launch RBAC
task004-control-runtime in-cluster Kubernetes access
success cleanup policy
default unpaused DAG behavior
~~~

除非出现新需求或回归失败，不重新设计上述业务链。

---

## 10. 下一阶段

当前 DAG 从已验证 Landing manifest 开始。

下一阶段唯一业务目标：

~~~text
STEP03
Airflow upstream ingestion orchestration

Generate Synthea
→ Landing publish / validate
→ feed manifest URI + manifest SHA
→ existing Person + Visit
→ existing Reconcile
~~~

原则：

- 不重新开发 Person / Visit / Reconcile；
- 复用当前 task004-control-runtime；
- 复用 04c-run-synthea-generate-publish.sh；
- 新增权限必须保持 namespace-scoped；
- Generate/Publish 输出必须动态进入下游，不能硬编码历史 manifest；
- 先做 bounded discovery / RBAC / render，再做一次 live end-to-end；
- GitHub 继续作为 DAG 唯一事实来源，不新增 DAG PVC。

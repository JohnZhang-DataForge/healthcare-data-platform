# TASK-004 开发经验总结

> **CURRENT TECHNICAL LESSONS / 历史案例原文与最新状态区分**：本文最初记录 TASK004 Synthea、Landing、resolver、Phase9、Standalone Person 的真实经验；下面原始案例按发生时的状态保留。
>
> **截至 2026-10-12：Standalone Visit 与 Batch Reconciliation 已 PASS，只有 Airflow Orchestration 尚未验收。** 最新权威状态见 `docs/tasks/TASK-STATUS.md`、`docs/tasks/TASK-004-BATCH-RECONCILIATION-CLOSEOUT.md`。第21/22节旧 `NEXT` 仅表示当时的开发顺序，不是当前待办。

---

## 1. Batch ID 和 Run ID 必须分开

TASK004 再次确认：

```text
batch_id = 数据批次身份
run_id   = 某一次处理运行身份
```

同一个 batch 可以有多个 run：

- first processing；
- recovery；
- replay verification；
- read-only verification；
- Person runtime；
- Visit runtime。

不能把数据身份和执行身份混在一个字段中。

---

## 2. Generator 参数不能被当成最终数据事实

Synthea 的：

```text
population_size
```

是 generator input，不应该被下游直接当成 `patients.csv` 的永久 expected rows。

正确链路应是：

```text
generator input
  ↓
actual generated output
  ↓
validator
  ↓
manifest actual row_count
  ↓
downstream runtime dynamically consumes row_count
```

TASK004 已去掉旧 Person 流程里固定 `113` 行的历史假设。

---

## 3. Landing Publication 必须有明确状态机

TASK004 验证了四种核心行为。

### 新 batch

```text
payload first
  ↓
independent remote readback
  ↓
manifest LAST
```

### same batch + same payload

```text
REUSE
```

### same batch + different payload

```text
CONFLICT
```

必须拒绝覆盖。

### partial payload + no manifest

允许安全 recovery。

### manifest present + incomplete payload

必须失败，不能静默修复一个已经宣告发布完成但内容不完整的 batch。

---

## 4. Manifest 是真正的发布边界

以下都不能单独证明 batch 已发布：

```text
CSV exists
directory exists
some objects exist
Job completed
```

真正可消费状态需要：

```text
exact payload set
header validation
row counts
payload SHA256
remote readback
manifest SHA256
INTAKE_VERIFIED
```

Manifest 是正式发布契约，而不是普通元数据文件。

---

## 5. 下游 Lineage 不应依赖某台机器上的历史 Report

历史流程曾依赖 TASK001 本地 runtime report。

TASK004 改为：

```text
batch_id
manifest_uri
manifest_sha256
```

这样：

- runner01 不再是 authoritative data source；
- Kubernetes Pod 可以独立执行；
- Airflow 不依赖历史开发目录；
- 下游依赖真正的远端已发布 manifest。

---

## 6. Manual Bridge 和 Production Runtime 必须分开

runner01 无法解析 cluster DNS，因此开发期允许：

```text
runner01
  ↓
kubectl exec
  ↓
existing Airflow scheduler
  ↓
cluster DNS
```

但这只能是开发 workaround。

未来控制面正确路径应是：

```text
control Pod
  ↓
direct resolver
  ↓
SeaweedFS
```

不能让 Airflow task 再 `kubectl exec` 回自己的 scheduler。

TASK004 通过：

```text
TASK004_RUNTIME_CONTEXT=manual
TASK004_RUNTIME_CONTEXT=in-cluster
```

明确区分两种执行环境。

---

## 7. Control Plane 和 Data Plane 应分层

TASK004 没有把所有组件塞进一个大镜像。

当前职责：

### Synthea Generator Image

```text
source generation
```

### TASK004 Control Runtime Image

```text
lineage resolution
control scripts
templates
kubectl
Python
Bash
```

### Spark Image

```text
PySpark data processing
```

### Airflow Image

```text
orchestration engine
```

这种分层比一个同时包含 Synthea、Spark、Airflow、kubectl 的巨型镜像更清晰。

---

## 8. 镜像身份必须同时包含 Git Identity 和 OCI Digest

TASK004 使用：

```text
git-<full-sha>
```

用于追踪 source。

真正 Kubernetes runtime 使用：

```text
ghcr.io/...@sha256:<digest>
```

最终 evidence 应建立：

```text
Git commit
  ↕
OCI revision label
  ↕
GHCR digest
  ↕
Kubernetes runtime imageID
```

---

## 9. 容器文件权限不能只检查 File Mode

Phase 9 的真实问题不是目标文件本身不可读，而是父目录不能 traverse。

失败状态：

```text
directory mode = 0644
read           = YES
execute        = NO
```

对于目录：

```text
r = 可以读取目录内容
x = 可以 traverse pathname
```

没有 `x`，即使目标文件本身是 `0644`，非 root 用户也无法打开。

因此以后容器验收要检查：

```text
file readable
+
every parent directory traversable
```

---

## 10. Docker COPY --chmod 要警惕父目录副作用

TASK004 第一版 Dockerfile 对 read-only assets 使用：

```text
COPY --chmod=0644
```

某些由该 COPY 创建的父目录最终没有 execute bit。

永久修复不是只补某一个路径，而是在 runtime source COPY 完成后统一：

```text
runtime directories → 0755
```

同时增加 regression test。

---

## 11. Non-root 镜像必须在真实 Pod 中验证

静态 Dockerfile 测试不能证明：

```text
UID 10001
```

真的能访问全部 runtime source。

Phase 9 最终在真实 Kubernetes Pod 中验证：

```text
uid/gid          = 10001:10001
runtime files    = 14/14 readable
runtime dirs     = 0755
```

因此以后 non-root image 的验收必须包括真实 filesystem runtime test。

---

## 12. 失败资源应保留到替代方案通过

TASK004 Phase 9 的处理顺序：

```text
failed Job
  ↓
retain
  ↓
diagnose
  ↓
fix source
  ↓
build replacement
  ↓
run replacement
  ↓
replacement PASS
  ↓
delete old failed Job
```

失败资源是证据，不是垃圾。

---

## 13. 排障要先确定 Failure Domain

第一次 runtime smoke 失败时，已先确认：

```text
image pull      PASS
container start PASS
version         PASS
kubectl         PASS
resolver        NOT YET EXECUTED
```

因此问题域被缩小到：

```text
container filesystem
```

以后排障应明确：

```text
失败发生在哪一层？
上一层是否已证明 PASS？
下一层是否根本还没执行？
```

---

## 14. Permanent Generator 优先于 Generated File Patch

如果 canonical source 由 permanent generator 重建，那么 bug 修复必须进入 generator。

不能只修：

```text
generated Dockerfile
generated test
generated shell
```

否则下次 reconstruction 会把修复覆盖。

验收应包含：

```text
generator reconstruction
checksum before / after
determinism PASS
```

---

## 15. Markdown 文档不要通过大型 Bash Heredoc 生成

项目已经多次遇到 Markdown 与 Bash 混合带来的问题：

- code fence；
- 反引号；
- `${...}`；
- `$()`；
- heredoc delimiter；
- 浏览器复制截断；
- Shell 误解析。

因此大型项目文档采用：

```text
直接生成独立 .md 文件
  ↓
人工放入明确 repo path
  ↓
单独验证
  ↓
git diff --check
  ↓
commit
```

不再把大型 Markdown 正文作为用户 Shell installer 的 heredoc payload。

---

## 16. EOF 和 git diff --check 必须是 Checkpoint Gate

Phase 9 曾出现：

```text
new blank line at EOF
```

当时 108 个测试全部通过，但 Git checkpoint 仍应失败。

正确 source gate：

```text
unit tests
+
generator determinism
+
git diff --check
```

文件结尾建议：

```text
exactly one final newline
no trailing whitespace
no extra blank line
```

---

## 17. Runtime PASS 不能停在 Render-only

Person / Visit 的 render-only 可以验证：

```text
lineage
template rendering
dynamic row count
SparkApplication structure
```

但不能证明：

```text
Spark image can start
S3 can be read
transformation is correct
Processing write works
readback works
```

因此 TASK004 在接 Airflow 前必须独立证明：

```text
Person real runtime PASS
Visit real runtime PASS
```

---

## 18. Processing 写入必须做 Independent Readback

Person STEP01 没有以：

```text
SparkApplication COMPLETED
```

作为最终成功条件。

还要求：

```text
SOURCE_ROWS=20
CANONICAL_ROWS=20
CANONICAL_CONTRACT=PASS
PROCESSING_WRITE=PASS
PROCESSING_READBACK=PASS
PROCESSING_READBACK_ROWS=20
```

所以：

```text
workload completed
```

和：

```text
data product verified
```

是两个不同层次。

---

## 19. Successful Runtime 应清理临时 K8s 资源

Person 成功后确认：

```text
SparkApplication residual = NO
ConfigMap residual         = NO
Driver Pod residual        = NO
```

推荐规则：

```text
success → cleanup
failure → retain evidence
```

Visit 和未来 Airflow workload 应继续遵守。

---

## 20. Frozen Task 不应因复用而被修改

TASK004 复用了：

```text
TASK002 Person adapter/template
TASK003 Encounter adapter/template
```

但没有为了 TASK004 去改历史 frozen source。

正确模式是：

```text
reuse frozen implementation
+
TASK004 wrapper/interface
```

TASK004 wrapper 负责：

- 新 lineage；
- 新 batch/run identity；
- dynamic expected rows；
- TASK004 label；
- 新 Processing output。

---

## 21. Airflow 必须最后接入

> **当前解释**：这条是 TASK004 的业务编排顺序：先验收 Person/Visit/Recon，再验证真正 Airflow DAG Run。它**不是**要求每个新 STEP 都重新建设 Airflow CI 基建。下方为当时记录的历史顺序。

当时已经独立证明：

```text
generator
Landing
resolver
control runtime
Person real runtime
```

下一步先证明：

```text
Visit real runtime
```

之后再进入：

```text
batch reconciliation
Airflow DAG
minimal RBAC
end-to-end orchestration
```

这样 Airflow 阶段失败时，排障范围主要剩：

```text
orchestration
RBAC
task dependency
```

而不是同时怀疑 Spark transformation。

---

## 22. TASK004 Reference Flow（原始阶段快照）

已经验证：

```text
Synthea Generator
        ↓
Kubernetes Job
        ↓
Landing publication
        ↓
verified manifest
        ↓
generic resolver
        ↓
Person Spark runtime
        ↓
Canonical Patient
        ↓
Processing Patient
```

下一步：

```text
verified manifest
        ↓
Visit Spark runtime
        ↓
Canonical Encounter
        ↓
Processing Encounter
```

最后才由 Airflow 编排完整链路。

---

## 23. 2026-10-12 真实验收补充（不改写历史案例）

- **Standalone Visit**：Self-Runner V8 Run `38250467965`，Encounter Processing 2459 行，PASS；无 PostgreSQL 写入。
- **Person/Visit Batch Reconciliation**：Healthcare PR #16，V9 pre-merge Run `38251984921`，20 Patient / 2459 Encounter / 0 orphan；negative Run `38251924029` 正确 Policy FAIL 且 ARC SKIPPED；post-merge Run `38252497171` PASS。
- **下一步**：Airflow DAG 的真实编排、参数/依赖、RBAC 和运行结果验证。不能把 DAG parse、render-only、CI 基础链路 PASS 冒充 Airflow Scheduler + Metadata DB 的真实 DAG Run。
- **新的 GitHub 开发规则**：新 STEP 直接维护 Git canonical source；旧依赖 Generator 的冻结实现必须同步 Generator；跨仓库 PR/SHA 手工绑定与 Runner 操作见正式 Development Operations。

---

## 24. Workflow Parse FAIL 与 Runtime FAIL 必须分开

本轮第一次 Self-Runner 运行：

```text
Run 38286850393
jobs = 0
```

失败发生在 GitHub Workflow YAML 解析阶段。

这意味着：

```text
Policy      = NOT RUN
ARC Runner  = NOT RUN
Kubernetes  = NOT RUN
Spark       = NOT RUN
Data        = NOT MUTATED
```

所以不能把所有 Actions failure 都归类为 workload failure。

推荐先判断 failure domain：

```text
workflow parse
→ policy
→ source gate
→ runner bootstrap
→ Kubernetes
→ Spark
→ business evidence
```

---

## 25. Source Test 也可能自己写错，不能绕过 Gate

Run `38286943030` 中：

```text
policy        PASS
exact PR HEAD PASS
source tests  FAIL
Spark         SKIPPED
```

失败的两个 assertion 都是测试自身缺陷：

- negative string test 把被禁止的字符串写进 test source，导致匹配自己；
- test 期待一个固定错误字符串，但实现使用通用参数化错误信息。

正确处理不是删掉 test gate，也不是直接跑 Spark，而是：

```text
定位 test defect
→ 修同一 feature branch
→ PR HEAD 变化
→ Self-Runner request 重新绑定新 exact SHA
→ 从 policy/source gate 重新验证
```

---

## 26. 重要 STEP 推荐同时做 PR HEAD 和 merged main 验证

本轮正式 Reconciliation 使用：

```text
Healthcare PR exact HEAD
→ real ARC / Spark PASS
→ merge
→ merged main exact SHA
→ real ARC / Spark PASS
```

对应：

```text
PR #24 final HEAD = ee16f5265b0ebb8c30e7e65ec665215613956e77
pre-merge Run     = 38287060452 PASS

merged main       = 91d96f436e7697d70025cc1c9a045ecfb20f41b1
post-merge Run    = 38287401518 PASS
```

这比“PR 里测过，所以 merge 后默认相同”更强。

不是所有小文档改动都需要 post-merge runtime；但对关键业务 STEP，这种模式应优先采用。

---

## 27. Runtime PASS、Historical Evidence、Mainline Acceptance 是三个不同状态

TASK004 Reconciliation 明确证明：

```text
代码能真实运行 PASS
!=
它已经属于正式主线
```

状态应区分：

```text
HISTORICAL_RUNTIME_PASS
CANDIDATE
MAINLINE_REVIEWED
MAINLINE_ACCEPTED
```

测试期 V9 的真实 PASS 没有被删除，但只有在主线完成：

```text
review
→ modify
→ source tests
→ exact PR HEAD real runtime
→ merge
→ exact main real runtime
→ closeout
```

之后才升级为：

```text
MAINLINE_ACCEPTED
```

这条原则以后同样适用于 Airflow、OMOP 新实体和其他平台组件。


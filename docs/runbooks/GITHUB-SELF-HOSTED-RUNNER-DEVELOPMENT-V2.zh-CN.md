# GitHub + Self-hosted Runner + 固化 Shell 验证开发方案（V2 试行 Runbook）

> 状态：**独立候选方案 / Pilot**，2026-10-11。本文为新增 Runbook，不覆盖、合并或修改现有 TASK001–TASK004 的开发文档、冻结规则、Canonical Contract 或主线架构。正式迁移须单独评审。

## 1. 决策和目标

保留原有 **可重复固化 Shell 验证**（Git baseline / schema-contract / lineage / PASS-FAIL Gate / checkpoint）的优点，同时将新开发中的**正式 Python、YAML、JSON 和测试源码直接交由 GitHub 管理**。GitHub Actions 只做通用编排；Kubernetes 内的 Self-hosted Runner（现有标签 `dw-runner-set`）Checkout 精确 Commit，调用仓库内固定 `.sh`，产生易读取的标准化结果和 Artifact。ChatGPT 使用 GitHub Connector 提交代码、查看 Workflow/日志、在同一次工作会话里迭代修复；长时间运行或会话结束后不承诺自动继续轮询。

**最小改动原则**：旧 TASK 的 Generator 和已冻结内容全部保留；新 STEP 可以逐步将 Generator 的“生成源码”职责退出，但继续维护独立可复现的 Shell 验证入口。不得将旧历史验证记录追溯性改写。

## 2. 已验证的最小 Pilot

独立试验仓库：`JohnZhang-DataForge/Self-Runner`，分支 `feature/reproducible-shell-ci-demo`。

- Python：`src/demo_math.py`；测试：`tests/test_demo_math.py`。
- 固化 Shell：`scripts/task-demo/validate.sh`；通用入口：`scripts/ci/run-task.sh`。
- 通用 Workflow：`.github/workflows/generic-shell-validation.yml`；Runner 标签 `dw-runner-set`。
- 成功执行：Run `38128940344`，Commit `3b8659f773780db48cdcef3b0922c0e01b33b679`，语法/3 个单测/Git worktree Gates 均 PASS，成功上传 `result.txt` 和 `report.json`。
- 后续增量：同一分支提交了 `even_numbers` Python 功能和两个新单测（Commit `a4ebb0faa8882033f57055b64fc365a9e6375655`），复用相同 Workflow，已确认 Push 能触发；此文档**不把该次结果推定为成功**。
- 此 Pilot 验证的是 Git/Runner/Python/Shell/Artifact 链路，**不是**生产级 Spark/K8s 全流程成功认证。

## 3. 职责边界

| 层次 | 唯一主要职责 |
| --- | --- |
| GitHub Feature Branch | 正式源码、测试、文档、版本审计与 PR |
| Python / YAML / JSON | ETL/业务逻辑、Kubernetes/Spark 定义、契约和测试 |
| `scripts/taskNNN/*.sh` | 可重复执行的测试序列、预检与 Gates；不再为新功能批量生成业务源码 |
| `scripts/ci/run-task.sh` | 统一安全入口、任务/脚本白名单、参数与环境检查 |
| 通用 GitHub Workflow | Checkout 精确 SHA、调用 Shell、超时和结果上传；不内嵌 ETL |
| Self-hosted Runner | 执行 Shell/单测，或通过 kubectl 发起受控集成测试 |
| Spark Operator / Spark Pods | 实际分布式 ETL；Runner 不承担大型 PySpark Driver |
| GitHub Logs / Step Summary / Artifact | 记录可审计结果，供人和 ChatGPT Connector 读取 |

## 4. 标准执行链路

1. 读取现有 TASK 规格、Contract、冻结规则和父 Git checkpoint；确认本次允许变更的文件路径。
2. 创建 `feature/taskNNN-...`；直接更新 Python、YAML、JSON、单测和固化 Shell（必要时）；每次 Commit 有明确 message。
3. Push 触发**无副作用验证**；Workflow 通过 `actions/checkout` 获取该次 `GITHUB_SHA`，并验证 `git rev-parse HEAD == GITHUB_SHA`。
4. Workflow 运行 `bash scripts/ci/run-task.sh <allowlisted-task>`，由 Shell 自己执行原有各项 Gates；失败必须非零退出。
5. Shell 输出 BEGIN/END 标记、每项 Gate 结果、`FINAL_STATUS`；生成 `result.txt`（简洁）和 `report.json`（结构化）。
6. Workflow 总是上传结果 Artifact（失败也尽可能上传），并将关键摘要放到 Step Summary；避免每次读取全量日志。
7. ChatGPT 在会话允许期间读取结果并修复，再 Commit/Push；若 Workflow 未完成，后续需新消息或经单独启用的自动任务继续检查。
8. 所有 Gate 合格后发起 PR/检查；主线合并与真实部署是独立受控步骤。

**建议输出契约**：

```text
===== TASKNNN_STEPNN_RESULT_BEGIN =====
TASK=TASKNNN
STEP=STEPNN
BRANCH=feature/...
GIT_COMMIT=<40-char-sha>
CONTRACT_SHA256=<sha256-or-NOT_APPLICABLE>
BASELINE_GATE=PASS
SYNTAX_GATE=PASS
UNIT_GATE=PASS
CONTRACT_GATE=PASS
FROZEN_FILES_GATE=PASS
FINAL_STATUS=PASS
===== TASKNNN_STEPNN_RESULT_END =====
```

`report.json` 记录相同标识与 Gates、独立 run_id、输入数据版本、镜像 digest 和失败原因（如果适用）；不能将未运行的 Gate 标为 PASS。必须传播所有命令失败码，不能仅依据日志里出现 PASS 判断成功。可复用 Shell 要能在相同前提下独立执行，不能依赖 Actions 特定行为来隐藏业务逻辑。

## 5. Workflow 设计

- 推荐通用 `code-validation`（feature branch Push / PR，仅读）；`spark-integration`（单独手动批准或限定触发）；`deploy`（人工批准）。
- Workflow 输入必须白名单化，不接受用户提供的任意 Shell 路径/命令；Shell 参数做校验。
- 禁止因为普通代码 Push 自动运行可能修改持久数据、PVC、数据库或正式环境的脚本。
- 使用 `timeout-minutes`、只读 `GITHUB_TOKEN`（`contents: read`）、最小必要依赖、受信任并固定版本的 Actions。
- 防止旧 Workflow 对所有分支无条件触发，避免并行多余任务；按 branch/path 精确过滤。
- 结果报告不打印 kubeconfig Token、Secrets、数据库密码、敏感数据行或其他凭据。
- Runner checkout 的 SHA 与 Spark Driver **实际运行**的源码要一致：优先不可变镜像 digest/Commit 标签或经过校验的代码 Artifact；不要默默依赖节点上遗留的 `/data/spark` 文件。
- 集成测试用隔离的输入/输出路径、不可变 run_id 和唯一资源名称；清理仅限本次创建的资源，不能影响冻结任务/共享数据。

## 6. 现阶段 RBAC 决策（仅实验集群）

**用户当前选择**：出于开发效率和资源开销考虑，暂时使用**现有** `dw-runner-set` / `dw-runner:dw-runner-sa`，实验阶段允许授予 `cluster-admin`，不额外启动第二套 Runner。它是**风险接受的临时政策**，不是生产建议。

**重要状态说明**：将决策写入本文**不等于已经修改集群 RBAC**。需从有权限的 kubeconfig 在集群上执行并验证：

```bash
kubectl create clusterrolebinding dw-runner-cluster-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=dw-runner:dw-runner-sa

kubectl auth can-i '*' '*' --all-namespaces \
  --as=system:serviceaccount:dw-runner:dw-runner-sa
# expected: yes
```

必要时撤回：

```bash
kubectl delete clusterrolebinding dw-runner-cluster-admin
```

**风险与约束**：任何可在该 Runner 上执行代码的工作流都可能掌控整个集群（包括 Secrets/RBAC/高权限 Pod），并可能间接访问宿主机或业务数据。因此必须限制谁能 Push、哪些仓库/分支能运行它、第三方 PR 是否能使用它；敏感的部署动作应使用人工批准、受保护分支和独立 Workflow。不要让来自不可信来源的代码运行在这一管理员 Runner 上。长期目标仍是拆分低权限验证身份与受限部署身份；当前选择并不豁免安全检查。

## 7. 当前集成前提与待办

- `dw-runner-sa` 原来的 namespace Role 只覆盖 `dw-runner`，此前 RBAC Audit 显示跨 Namespace 无权限。**本文提交不自动升级权限。**
- 先把基础代码验证迁入 `healthcare-data-platform` 的**新 Workflow**，但不要修改历史 TASK001–TASK003 Generator/Contract/Checkpoint。
- 明确 Shell 的依赖：`python3`、测试包、`kubectl`、其他 CLI 及版本。Runner Pod 临时环境与 `/data/spark` 非同一个文件系统；必须显式准备工具和输入。
- 后续添加 Spark 集成测试时，再单独验证 ServiceAccount 权限、SparkApplication 提交/完成、镜像 SHA 对齐、SeaweedFS / PostgreSQL 连通性、失败退出码、Artifact 上传及数据隔离。
- 为每一次测试保留 `GITHUB_SHA`、TASK/STEP、run_id、Contract SHA256、各 Gates、Artifacts 与最终结论。
- 单独编写迁移评审/变更记录后，才允许讨论与现有主线 TASK 文档合并。

## 8. 本文的适用范围

本 Runbook 是对开发工作流的**新增候选方案**，并非对既有项目架构、任务冻结状态或已通过历史 Gate 的修改。任何后续 Agent/新 Session 应先阅读本文件，再读取当前 TASK 的权威文档核对路径和执行边界；如果有冲突，保持已冻结任务不变并提出评审，而不是擅自覆盖。

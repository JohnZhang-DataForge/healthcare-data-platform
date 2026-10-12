# Healthcare Data Platform — STEP GitOps 迁移说明 v1.0（中文版）

> **日期：2026-10-12｜性质：迁移设计与执行清单，NOT_DEPLOYED｜来源：Self-Runner 已验证实验**
>
> 先在 `JohnZhang-DataForge/Self-Runner` 保存权威迁移说明，再以**新文件、单独 PR**复制到 `JohnZhang-DataForge/healthcare-data-platform`。此文档发布不表示 Workflow 已安装、任何 Healthcare TASK 已重新验收或运行环境已修改。**禁止覆盖、删除、移动或重写 Healthcare 已有文档与冻结代码。**

## 1. 范围与原则

- **文档阶段（本次）**：仅新建 `docs/migration/HEALTHCARE-GITOPS-MIGRATION-v1.0-zh-CN.md`；两仓各自以分支→PR→Merge Commit 合并。不得修改原有 `docs/BASELINE.md`、`docs/runbooks/GITHUB-SELF-HOSTED-RUNNER-DEVELOPMENT-V2.zh-CN.md`、`docs/architecture/**`、`docs/handoffs/**`、`docs/task003/**`、`docs/tasks/**` 和现有 Workflow、Shell、Contract、数据或 Kubernetes。
- **后续实施阶段（另行开展）**：以增量新目录/新 Workflow 适配 Healthcare，先检查/只读验证，最后再考虑有副作用的执行。**本文不授权部署或写数据**。
- STEP 为迭代及验收单元；每 STEP 一份固定 JSON，每次改**同一文件**；身份以 Git 完整 SHA + GitHub Actions Run ID 认定，request_id 仅为可读标签。
- 每次从最新 `main` 建 `feature/taskNNN-stepNN`；失败在同一分支修复，只有**最新 Feature Head SHA** 的全部适用 Gate PASS 才能 PR Merge Commit。合并后在受保护 main 上复验，Checkpoint 也经 PR 提交。
- Python / YAML / JSON / Tests 为 Git 原生源码；Shell 为版本化的预检、执行、验证入口。**历史 TASK003/004 已冻结的自重建 Shell Generator 原样保留**；只对新 STEP 逐步引入新方法，不反向强制改写旧规则。
- Tag 只用于 Phase/TASK/平台里程碑，STEP 以 Checkpoint、Commit、PR 和 Workflow Run 追溯。
- 遇到文档冲突：当前 Healthcare TASK 专属的冻结 Contract/Checkpoint 优先；旧 `BASELINE.md` 保持不变；本文件仅是未来工作流的**新增候选流程**，不自动替换权威约束。

## 2. 可追溯的 Self-Runner 实验结果

| 测试 | 证据 | 界限 |
|---|---|---|
| STEP01 Spark Operator/K8s Smoke | [STEP01 Checkpoint](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/checkpoints/task004/step01-spark-smoke.md) | 只代表实验环境 PASS |
| STEP02 固定 STEP JSON、Airflow 3 隔离 DagBag/纯 Python | [STEP02 Checkpoint](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/checkpoints/task004/step02-airflow-fixed-json.md) | 不是 Scheduler+Metadata DB 实际 DAG Run |
| STEP03 Push Validate 允许列表、拒绝 execute、冻结文件 Gate、Merge SKIP/main 复验 | [STEP03 Checkpoint](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/checkpoints/task004/step03-safety.md)；[最终 main PASS](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38193663449) | V3 仅允许 task004/step03/validate，**非通用授权引擎** |
| 相同旧 SHA 的两路 JSON 并发写 | [并发记录](https://github.com/JohnZhang-DataForge/Self-Runner/blob/feature/task004-concurrency-probe/tests/concurrency/RESULTS.md) | 一方 409，证明防静默覆盖；不等于两条 Workflow 并发资源隔离 |
| Healthcare protected main：GitHub App 直接写入被拒绝 | GitHub 409 “Changes must be made through a pull request” | 证明当前连接不具直接写入权限 |
| Healthcare PR 合并与清理 | [PR #7](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/7)、[PR #8](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/8) | 已验证 Merge Commit 路径；尚未启用强制 PR Status Check |

**重要限制**：Self-Runner V1/V2/V3 有不同触发路径和冻结边界；不能整体复制或宣布全部“生产级”。允许列表、旧冻结哈希、任务名、Airflow/Spark 示例、路径、环境和权限都需重新建立。V3 的多父 Merge Commit 采用 SKIP；完成合并后的真实业务验证必须独立执行，不能把 SKIP 当作验证 PASS。

## 3. 当前 Healthcare 事实与兼容性

现有主要资料（保持**原文件不变**）：
- `docs/BASELINE.md`：历史 `/data/spark/phase3c` 不可覆盖，原 V2 开发与 PASS 冻结准则继续有效。
- `docs/runbooks/GITHUB-SELF-HOSTED-RUNNER-DEVELOPMENT-V2.zh-CN.md`：既有独立 Pilot Runbook，继续保留。
- `docs/architecture/**`、`docs/tasks/**`、`docs/task003/**`、`docs/handoffs/**`、`docs/runbooks/**`：架构、Contract、Lineage、TASK003/004 阶段证据及经验汇总保持原路径。
- `.github/workflows/build-synthea-image.yml`、`.github/workflows/build-task004-runtime-image.yml`：既存构建流程不得替换或无依据更改触发器。
- `dw-runner-set` 是实验用 ARC ephemeral Runner，`maxRunners=3` 只是**容量上限**，不等于 STEP 层面互斥或资源隔离；Runner SA 权限必须在实施前独立核实。不得将非可信 PR 代码直接授予高权限 K8s 执行能力。

## 4. 后续目标布局（示意，**本次不创建**）

```text
healthcare-data-platform/
├── .github/workflows/generic-step-validation-v1.yml   # 新文件；先仅安全验证
├── config/ci/tasks/taskNNN/stepNN.json                  # 每 STEP 固定 JSON
├── scripts/ci/run-task.sh                               # 新统一入口，白名单
├── scripts/ci/tasks/taskNNN/stepNN.sh                    # 新 STEP 固化验证入口
├── src/、spark/、airflow/、tests/                         # 沿用已存在的业务结构，按实际需要增量扩展
└── docs/migration/HEALTHCARE-GITOPS-MIGRATION-v1.0-zh-CN.md
```

此图是规划**不是部署现状**。实施前必须用仓库树和当前 `main` 确认无命名冲突；不复用 Self-Runner `config/policy/tasks/task004/step03.json` 作为 Healthcare 的业务任务。

## 5. 分阶段迁移顺序和 Gate

### M0 — 只迁移文档（本次）

1. 在 Self-Runner 新增迁移文件，独立分支→PR→Merge Commit。
2. 从 Self-Runner 的合并后 `main` 读取**准确文本**，在 Healthcare 的**不存在的新路径**新建同名文件，独立分支→PR→Merge Commit。
3. 验证 Healthcare `main` 文件内容与来源一致、原有业务/文档/Workflow 文件无任何变化。不得以直接 Push 绕过 protected main。
4. 文档阶段无 Shell 执行、无镜像构建、无 K8s 资源部署；状态为 `DOCUMENT_ONLY`。

### M1 — Healthcare 只读预检（后续独立 PR）

- 冻结当前真实主线 HEAD 和旧 TASK 文件清单/哈希；建立基线 manifest；读取当前 `docs/tasks` 和对应任务 Checkpoint，制定**准许变更列表**与拒绝列表。
- 验证 GitHub Actions/App Token 权限、受保护 main、PR 合并、Actions Runner label/checkout/依赖版本；审查现有 Actions 的 path filters，避免旧/新 Workflow 双触发。
- 审核可信执行边界：高权限 Runner 下的 `pull_request` 执行不可信代码仍有风险；应先考虑最小权限预检或可信合并后的执行路径。不能只靠 JSON allowlist 就宣称代码隔离。
- 所有检查只读、无数据写入，生成基线报告；Gate PASS 后才能进入 M2。

### M2 — 新 Workflow + Schema/Allowlist/Freeze Gate（后续独立 PR）

- 新建而非覆盖 Workflow；先实现 `validate`，禁止 JSON 自定义 Shell 路径、命令、Namespace、镜像和危险 execute 参数。
- 精确 `GITHUB_SHA` checkout、单次提交请求检测（Merge Commit 单独逻辑）、可复现 Shell 入口、参数 Schema、每 STEP 白名单与冻结清单、超时和错误传播。
- 单元测试包括多请求、未授权 TASK/STEP、Shell 注入、缺失配置、修改冻结文件及新的请求误配；确认失败时**业务 Shell 不执行**。
- 单 STEP 同时工作用 `concurrency.group`/幂等唯一资源名管控；同文件 Git 409 必须停止并人工/显式比较，不可盲目重试覆盖。
- 先在无副作用样例上验证 Feature PASS、非法请求 FAIL、PR 合并及 main 后验 Gate；**不要要求一个尚未在所有 PR 上稳定运行的 Check 名称**，以免锁死合并。

### M3 — 按需受控 Spark/Airflow 集成（后续独立批准）

- 只能使用隔离 Namespace、唯一资源名、已批准的镜像/提交和受控测试数据；验证 SparkDriver/Executor 终态、Contract/Lineage；Airflow DagBag 解析与真正 DAG Run 要分别验收。
- 写入 PostgreSQL、SeaweedFS、PVC 或共享 DAG/数据库前需具体范围和授权；绝不因普通 JSON Push 自动执行破坏性变更。
- 失败时采集 Pod logs/describe，限定清理自己创建的资源；同时考虑中断后的孤儿 Pod 回收。

### M4 — Checkpoint、恢复/Replay、运行治理（后续）

- 每个 STEP 记录 Feature SHA、Merge SHA、main 校验 SHA、PR/Run ID、各 Gate、源码/Contract/镜像/输入哈希、PASS/NOT_RUN/FAIL 与安全/回滚范围。
- Checkpoint 自身走 PR；不再用直接 Push `main` 方式提交。若其合并产生新的 HEAD，不得声称之前测试自动覆盖了新的 HEAD。
- Replay 需验证外部数据快照/Secrets/容器 digest/存储和依赖，而不只是 Shell 文件不变。
- 条件合适后评估 Require Status Checks；当前不要求其立刻开启。强制 PR 及禁止管理员绕过已实测有效。

## 6. 实施中止条件与已知未验收事项

**遇到以下情况立即停止自动合并或执行**：冻结文件差异、不在允许列表、失败/未运行的必要 Gate、Head SHA 改变、PR 冲突、运行中断、权限/凭据不足、潜在数据破坏，以及强制保护规则拒绝。

保留为**未完成**：真正多个 Workflow 同时争用同一 Kubernetes 持久资源；突然 kill Runner 后的孤儿清理；独立可信策略仓库/隔离式执行；全新集群 Replay；全面自动化 PR Required Checks。这些不是本次文档迁移的阻塞项，但**不可标为已 PASS**。

## 7. 交接给新 ChatGPT Session 的执行要求

1. 先读 `docs/BASELINE.md`、当前 TASK 的 Contract/Checkpoint/冻结清单，再读本迁移文档、Self-Runner v1.0/v1.1 规范及 STEP01/02/03 Checkpoint。
2. 在现有 main 基线上工作，明确 TASK/STEP、允许修改路径、原约束和目标 Gate，默认只读；不得假设本文已部署 Workflow。
3. 先分支开发，精确 SHA 测试，失败就原分支迭代；一切合并经 PR，Merge Commit，并在 main 复验。
4. 遇到 409 Git 冲突、Runner 长时间 Queued、冻结哈希变化，先核对状态与证据，不能推测 PASS 或直接覆盖。
5. 不改旧 Healthcare 文档和冻结 Generator；任何替代/迁移旧逻辑都必须单独提议与得到批准。
6. 迁移完成后，未来如果需要更新本文，创建新版本 `v1.1` 或独立增补，**不静默覆盖 v1.0**。

## 8. 原始参考

- Self-Runner：`docs/STEP-BASED-GITOPS-DEVELOPMENT-STANDARD-v1.0-zh-CN.md`
- Self-Runner：`docs/STEP-BASED-GITOPS-DEVELOPMENT-STANDARD-v1.1-ADDENDUM.md`
- Self-Runner：`docs/runbooks/SELF-RUNNER-COMMON-LESSONS.md`
- Self-Runner：`docs/checkpoints/task004/step01-spark-smoke.md`、`step02-airflow-fixed-json.md`、`step03-safety.md`
- Healthcare：`docs/runbooks/GITHUB-SELF-HOSTED-RUNNER-DEVELOPMENT-V2.zh-CN.md`（不覆盖）
- Healthcare：`docs/BASELINE.md` 及现有 TASK003/004 冻结文档（不覆盖）
